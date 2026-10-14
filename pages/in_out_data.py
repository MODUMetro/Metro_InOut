import streamlit as st
import pandas as pd
import plotly.express as px
import pydeck as pdk
import os
from pathlib import Path
import sys

from settings import PARQUET_PATH, METRO_PATH_SEOUL, TRANSER_INFORMATION, SHOW_CIRCLE_AND_BAR, SHOW_PYDECK, SUBWAY_COLORS

st.set_page_config(page_title="지하철 승하차 조회 대시보드", layout="wide")

# 자주 사용하는 텍스트 상수 지정
COL_STATION_ORIGIN = '역명'
COL_STATION = '지하철역'
COL_LAT = '위도'
COL_LON = '경도'
COL_LINE = '호선명'
COL_BOARD_DETAIL = '승차_상세'
COL_ALIGHT_DETAIL = '하차_상세'

# 파일 로드 함수 통합 (CSV/Parquet 및 인코딩 자동 처리)
@st.cache_data
def load_file_data(file_source):
    if file_source is None:
        return None
        
    # 경로(String) 입력일 경우
    if isinstance(file_source, (str, Path)):
        if not os.path.exists(file_source):
            return None
        suffix = Path(file_source).suffix
        source = file_source
    # Streamlit UploadedFile 객체
    else:
        suffix = Path(file_source.name).suffix
        source = file_source

    if suffix == '.parquet':
        return pd.read_parquet(source)    
    elif suffix == '.csv':
        try:
            return pd.read_csv(source, encoding='utf-8')
        except UnicodeDecodeError:
            return pd.read_csv(source, encoding='cp949')
    else:
        raise ValueError("지원하지 않는 파일 형식입니다.")

st.title("🚇 지하철 시간대별 유동인구 탐색 대시보드")
st.markdown(TRANSER_INFORMATION)

# ==========================================
# 프로젝트 루트 경로 추가 및 기본 데이터 로드
sys.path.append(str(Path(__file__).resolve().parent.parent))

st.sidebar.header("📁 데이터 상태")
df = load_file_data(PARQUET_PATH)

if df is not None:
    st.sidebar.success(f"✅ 기본 데이터 자동 로드 완료")
else:
    st.sidebar.warning(f"⚠️ 폴더에 기본 파일이 없습니다. 경로를 확인해주세요: {PARQUET_PATH}")

# ==========================================

# df가 정상적으로 로드되었을 때만 대시보드 로직 실행
if df is not None:
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 검색 조건 설정")
    
    view_mode = st.sidebar.selectbox(
        "📊 시각화 모드 선택", 
        [SHOW_CIRCLE_AND_BAR, SHOW_PYDECK]
    )
    st.sidebar.markdown("---")
    
    if '사용월' in df.columns:
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
        
        # 상수 변수 적용
        filtered_df = df[df['사용월'].astype(str) == selected_month]
        result_df = filtered_df[[COL_LINE, COL_STATION, selected_board, selected_alight]].copy()
        
        result_df[selected_board] = pd.to_numeric(result_df[selected_board].astype(str).str.replace(',', ''), errors='coerce').fillna(0).astype(int)
        result_df[selected_alight] = pd.to_numeric(result_df[selected_alight].astype(str).str.replace(',', ''), errors='coerce').fillna(0).astype(int)
        result_df = result_df.drop_duplicates()
        
        result_df[COL_BOARD_DETAIL] = result_df.apply(lambda x: f"{x[COL_LINE]}: {x[selected_board]:,}명", axis=1)
        result_df[COL_ALIGHT_DETAIL] = result_df.apply(lambda x: f"{x[COL_LINE]}: {x[selected_alight]:,}명", axis=1)
        
        grouped_df = result_df.groupby(COL_STATION).agg({
            selected_board: 'sum',
            selected_alight: 'sum',
            COL_BOARD_DETAIL: lambda x: '<br>'.join(x),
            COL_ALIGHT_DETAIL: lambda x: '<br>'.join(x)
        }).reset_index()
        
        st.dataframe(result_df[[COL_LINE, COL_STATION, selected_board, selected_alight]], use_container_width=True, hide_index=True)
        st.markdown("---")
        
        if view_mode == SHOW_CIRCLE_AND_BAR:
            st.subheader("🏆 환승역 통합 Top 10 비중 (원형 차트)")
            st.caption("ℹ️ 차트 조각에 마우스를 올리시면 호선별 상세 인원수가 표시됩니다.")
            
            col1, col2 = st.columns(2)
            
            top10_board = grouped_df.sort_values(by=selected_board, ascending=False).head(10)
            fig_board = px.pie(
                top10_board, 
                values=selected_board, 
                names=COL_STATION, 
                title=f"📈 {selected_board} Top 10", 
                hole=0.4,
                custom_data=[COL_BOARD_DETAIL]
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
                names=COL_STATION, 
                title=f"📉 {selected_alight} Top 10", 
                hole=0.4,
                custom_data=[COL_ALIGHT_DETAIL]
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
            
            top10_board_stations = top10_board[COL_STATION].tolist()
            bar_board_df = result_df[result_df[COL_STATION].isin(top10_board_stations)]
            fig_bar_board = px.bar(
                bar_board_df, 
                x=COL_STATION, 
                y=selected_board, 
                color=COL_LINE,
                color_discrete_map=SUBWAY_COLORS, 
                title=f"📈 {selected_board} 호선별 구성",
                text_auto='.2s'
            )
            fig_bar_board.update_layout(xaxis={'categoryorder':'total descending'})
            
            top10_alight_stations = top10_alight[COL_STATION].tolist()
            bar_alight_df = result_df[result_df[COL_STATION].isin(top10_alight_stations)]
            fig_bar_alight = px.bar(
                bar_alight_df, 
                x=COL_STATION, 
                y=selected_alight, 
                color=COL_LINE, 
                color_discrete_map=SUBWAY_COLORS, 
                title=f"📉 {selected_alight} 호선별 구성",
                text_auto='.2s'
            )
            fig_bar_alight.update_layout(xaxis={'categoryorder':'total descending'})
            
            with col3:
                st.plotly_chart(fig_bar_board, use_container_width=True)
            with col4:
                st.plotly_chart(fig_bar_alight, use_container_width=True)
    
        elif view_mode == SHOW_PYDECK:
            st.subheader("유동인구 3D 지도")        

            # 통합된 load_file_data 함수 호출
            coord_df = load_file_data(METRO_PATH_SEOUL)

            if coord_df is not None:
                if COL_STATION_ORIGIN in coord_df.columns and COL_STATION not in coord_df.columns:
                    coord_df = coord_df.rename(columns={COL_STATION_ORIGIN: COL_STATION})
                
                # 중복 제거 로직 유지
                coord_df = coord_df.drop_duplicates(subset=[COL_STATION])
                
                map_df = pd.merge(grouped_df, coord_df, on=COL_STATION, how='inner')
                
                if not map_df.empty and COL_LAT in map_df.columns and COL_LON in map_df.columns:
                    
                    map_df['board_count'] = map_df[selected_board]
                    map_df['alight_count'] = map_df[selected_alight]
                    
                    map_df['board_count_str'] = map_df['board_count'].apply(lambda x: f"{int(x):,}")
                    map_df['alight_count_str'] = map_df['alight_count'].apply(lambda x: f"{int(x):,}")
                    
                    layer = pdk.Layer(
                        "ColumnLayer",
                        data=map_df,
                        get_position=[COL_LON, COL_LAT],
                        get_elevation="board_count",           
                        elevation_scale=0.03,  
                        radius=150,            
                        get_fill_color=[255, 140, 0, 200], 
                        pickable=True,
                        auto_highlight=True
                    )

                    center_lat = map_df[COL_LAT].mean()
                    center_lon = map_df[COL_LON].mean()

                    view_state = pdk.ViewState(
                        longitude=center_lon,
                        latitude=center_lat,
                        zoom=11,
                        pitch=50, 
                        bearing=0
                    )

                    r = pdk.Deck(
                        layers=[layer],
                        initial_view_state=view_state,
                        tooltip={
                            "html": f"<b>{{{COL_STATION}}}</b><br/>선택시간 탑승: {{board_count_str}}명<br/>선택시간 하차: {{alight_count_str}}명",
                            "style": {"color": "white"}
                        }
                    )

                    st.pydeck_chart(r, use_container_width=True)
                else:
                    st.error("⚠️ 병합된 데이터에 매핑할 수 있는 좌표가 없습니다.")
                    st.caption(f"- 승하차 역명 예시: {grouped_df[COL_STATION].head(3).tolist()}")
                    if COL_STATION in coord_df.columns:
                        st.caption(f"- 좌표 역명 예시: {coord_df[COL_STATION].head(3).tolist()}")
            else:
                st.warning(f"⚠️ 폴더 내에 {METRO_PATH_SEOUL} 파일을 찾을 수 없습니다. 파일명과 위치를 다시 확인해주세요.")


# 기본 파일 외에 다른 파일을 보고 싶을 때를 대비한 수동 업로더
uploaded_file = st.sidebar.file_uploader("다른 파일을 보시려면 업로드하세요", type=['csv', 'parquet'])
if uploaded_file is not None:
    df = load_file_data(uploaded_file)
    st.sidebar.success("✅ 새로운 파일 로드 완료")