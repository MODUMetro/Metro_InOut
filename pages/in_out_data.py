import streamlit as st
import pandas as pd
import plotly.express as px
import os
from pathlib import Path
import sys
from settings import CSV_PATH, PARQUET_PATH

st.set_page_config(page_title="지하철 승하차 조회 대시보드", layout="wide")

# 1. CSV 파일 읽어오기 (캐싱) - 경로(String)와 업로드된 객체 모두 지원
@st.cache_data
def load_data(file):
    if file.suffix == '.parquet':
        return pd.read_parquet(file)    
    elif file.suffix == '.csv':
        try:
            return pd.read_csv(file, encoding='cp949')
        except UnicodeDecodeError:
            return pd.read_csv(file, encoding='utf-8')
    else:
        raise ValueError("지원하지 않는 파일 형식입니다.")

st.title("🚇 지하철 시간대별 유동인구 탐색 대시보드")
st.markdown("환승역의 경우 통합된 인원수를 보여주며, 차트에 마우스를 올리면 호선별 상세 인원을 확인할 수 있습니다.")

# ==========================================
# 지정된 경로에서 자동 로드하기
# ==========================================
# 프로젝트 루트(pages/의 부모 폴더)에 있는 settings.py를 확실히 찾도록 경로 추가
sys.path.append(str(Path(__file__).resolve().parent.parent))

st.sidebar.header("📁 데이터 상태")
df = None

# 지정된 경로에 파일이 존재하면 자동으로 불러옵니다.
if os.path.exists(PARQUET_PATH):
    df = load_data(PARQUET_PATH)
    st.sidebar.success(f"✅ 기본 데이터 자동 로드 완료")
else:
    st.sidebar.warning(f"⚠️ 폴더에 기본 파일이 없습니다. 경로를 확인해주세요: {PARQUET_PATH}")

# ==========================================

# df가 정상적으로 로드되었을 때만 아래 대시보드 로직 실행
if df is not None:
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 검색 조건 설정")
    
    # 노선 공식 색상 세팅
    subway_colors = {
        '1호선': '#0052A4', '2호선': '#00A84D', '3호선': '#EF7C1C', 
        '4호선': '#00A5DE', '5호선': '#996CAC', '6호선': '#CD7C2F', 
        '7호선': '#747F00', '8호선': '#E6186C', '9호선': '#BDB092',
        '수인분당선': '#FABE00', '신분당선': '#D4003B', 
        '경의중앙선': '#77C4A3', '공항철도 1호선': '#0090D2',
        '경강선': '#003DA5', '경부선': '#0052A4', '경원선': '#0052A4', 
        '경인선': '#0052A4', '경의선': '#77C4A3', '경춘선': '#0C8E72', 
        '과천선': '#00A5DE', '분당선': '#FABE00', '서해선': '#81A914', 
        '수인선': '#FABE00', '신림선': '#6789CA', '안산선': '#00A5DE', 
        '우이신설선': '#B0CE18', '일산선': '#EF7C1C', '장항선': '#0052A4', '중앙선': '#77C4A3'
    }
    
    if '사용월' in df.columns:
        # 사용월 최신순 정렬 적용
        month_list = sorted(df['사용월'].astype(str).unique().tolist(), reverse=True)
        selected_month = st.sidebar.selectbox("사용월 선택", month_list)
    else:
        st.error("데이터에 '사용월' 컬럼이 없습니다.")
        st.stop()
        
    board_cols = [col for col in df.columns if '승차' in col]
    alight_cols = [col for col in df.columns if '하차' in col]
    
    selected_board = st.sidebar.selectbox("시간대 탑승 선택", board_cols)
    selected_alight = st.sidebar.selectbox("시간대 하차 선택", alight_cols)
    
    if st.sidebar.button("조회 실행 🚀"):
        st.markdown(f"### 📌 [{selected_month}] 조회 결과")
        
        filtered_df = df[df['사용월'].astype(str) == selected_month]
        result_df = filtered_df[['호선명', '지하철역', selected_board, selected_alight]].copy()
        
        result_df[selected_board] = pd.to_numeric(result_df[selected_board].astype(str).str.replace(',', ''), errors='coerce').fillna(0).astype(int)
        result_df[selected_alight] = pd.to_numeric(result_df[selected_alight].astype(str).str.replace(',', ''), errors='coerce').fillna(0).astype(int)
        result_df = result_df.drop_duplicates()
        
        result_df['승차_상세'] = result_df.apply(lambda x: f"{x['호선명']}: {x[selected_board]:,}명", axis=1)
        result_df['하차_상세'] = result_df.apply(lambda x: f"{x['호선명']}: {x[selected_alight]:,}명", axis=1)
        
        grouped_df = result_df.groupby('지하철역').agg({
            selected_board: 'sum',
            selected_alight: 'sum',
            '승차_상세': lambda x: '<br>'.join(x),
            '하차_상세': lambda x: '<br>'.join(x)
        }).reset_index()
        
        st.dataframe(result_df[['호선명', '지하철역', selected_board, selected_alight]], use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("🏆 환승역 통합 Top 10 비중 (원형 차트)")
        st.caption("ℹ️ 차트 조각에 마우스를 올리시면 호선별 상세 인원수가 표시됩니다.")
        
        col1, col2 = st.columns(2)
        
        top10_board = grouped_df.sort_values(by=selected_board, ascending=False).head(10)
        fig_board = px.pie(
            top10_board, 
            values=selected_board, 
            names='지하철역', 
            title=f"📈 {selected_board} Top 10", 
            hole=0.4,
            custom_data=['승차_상세']
        )
        fig_board.update_traces(
            textposition='inside', 
            textinfo='percent+label',
            hovertemplate="<b>%{label}역</b><br>총 인원: %{value:,}명<br><br><b>[호선별 상세]</b><br>%{customdata[0]}<extra></extra>"
        )
        
        top10_alight = grouped_df.sort_values(by=selected_alight, ascending=False).head(10)
        fig_alight = px.pie(
            top10_alight, 
            values=selected_alight, 
            names='지하철역', 
            title=f"📉 {selected_alight} Top 10", 
            hole=0.4,
            custom_data=['하차_상세']
        )
        fig_alight.update_traces(
            textposition='inside', 
            textinfo='percent+label',
            hovertemplate="<b>%{label}역</b><br>총 인원: %{value:,}명<br><br><b>[호선별 상세]</b><br>%{customdata[0]}<extra></extra>"
        )
        
        with col1:
            st.plotly_chart(fig_board, use_container_width=True)
        with col2:
            st.plotly_chart(fig_alight, use_container_width=True)
            
        st.markdown("---")
        st.subheader("📊 Top 10 역 호선별 구성 비율 (누적 막대 차트)")
        
        col3, col4 = st.columns(2)
        
        top10_board_stations = top10_board['지하철역'].tolist()
        bar_board_df = result_df[result_df['지하철역'].isin(top10_board_stations)]
        fig_bar_board = px.bar(
            bar_board_df, 
            x='지하철역', 
            y=selected_board, 
            color='호선명',
            color_discrete_map=subway_colors, # 지정 색상 적용 
            title=f"📈 {selected_board} 호선별 구성",
            text_auto='.2s'
        )
        fig_bar_board.update_layout(xaxis={'categoryorder':'total descending'})
        
        top10_alight_stations = top10_alight['지하철역'].tolist()
        bar_alight_df = result_df[result_df['지하철역'].isin(top10_alight_stations)]
        fig_bar_alight = px.bar(
            bar_alight_df, 
            x='지하철역', 
            y=selected_alight, 
            color='호선명', 
            color_discrete_map=subway_colors, # 지정 색상 적용
            title=f"📉 {selected_alight} 호선별 구성",
            text_auto='.2s'
        )
        fig_bar_alight.update_layout(xaxis={'categoryorder':'total descending'})
        
        with col3:
            st.plotly_chart(fig_bar_board, use_container_width=True)
        with col4:
            st.plotly_chart(fig_bar_alight, use_container_width=True)

# 기본 파일 외에 다른 파일을 보고 싶을 때를 대비한 수동 업로더
uploaded_file = st.sidebar.file_uploader("다른 파일을 보시려면 업로드하세요", type=['csv'])
if uploaded_file is not None:
    df = load_data(uploaded_file)
    st.sidebar.success("✅ 새로운 파일 로드 완료")