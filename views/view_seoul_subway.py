import streamlit as st
import pandas as pd
import plotly.express as px
import os
from pathlib import Path
import re

from settings import PARQUET_PATH, METRO_PATH_SEOUL, TRANSER_INFORMATION, SHOW_CIRCLE_AND_BAR, SHOW_PYDECK, SUBWAY_COLORS, LINE_NAME_MAP, LINE_NAME_REGEX_MAP

# ==========================================
# 자주 사용하는 텍스트 상수 지정
COL_STATION_ORIGIN = '역명'
COL_STATION = '지하철역'
COL_LAT = '위도'
COL_LON = '경도'
COL_LINE = '호선명'
COL_BOARD_DETAIL = '승차_상세'
COL_ALIGHT_DETAIL = '하차_상세'
LIGHT_DAY_TIME_START = 6
LIGHT_DAY_TIME_END = 18
# ==========================================

@st.cache_data
def load_file_data(file_source):
    """파일 로드 함수 (CSV/Parquet 및 인코딩 자동 처리)"""
    if file_source is None:
        return None
        
    if isinstance(file_source, (str, Path)):
        if not os.path.exists(file_source):
            return None
        suffix = Path(file_source).suffix
        source = file_source
    else:
        suffix = Path(file_source.name).suffix
        source = file_source

    if suffix == '.parquet':
        df = pd.read_parquet(source)    
    elif suffix == '.csv':
        try:
            df = pd.read_csv(source, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(source, encoding='cp949')
    else:
        raise ValueError("지원하지 않는 파일 형식입니다.")
        
    if COL_LINE in df.columns:
        df[COL_LINE] = df[COL_LINE].replace(LINE_NAME_MAP)
        for pattern, replacement in LINE_NAME_REGEX_MAP:
            df[COL_LINE] = df[COL_LINE].str.replace(pattern, replacement, regex=True)
        
    return df

def render_seoul():
    """서울 지하철 UI 렌더링 및 분석 로직"""
    st.markdown(TRANSER_INFORMATION)

    # ==========================================
    # 데이터 로드
    # ==========================================
    with st.expander("📁 데이터 로드 및 상태 확인 (클릭해서 열기)", expanded=False):
        # ⚠️ 위젯 key를 지정해 주어 부산 UI와 충돌을 방지합니다.
        uploaded_file = st.file_uploader("기본 파일 외에 다른 파일을 보시려면 업로드하세요", type=['csv', 'parquet'], key='seoul_uploader')
        
        if uploaded_file is not None:
            df = load_file_data(uploaded_file)
            st.success("✅ 새로운 파일 로드 완료")
        else:
            df = load_file_data(PARQUET_PATH)
            if df is not None:
                st.success("✅ 기본 데이터 자동 로드 완료")
            else:
                st.warning(f"⚠️ 폴더에 기본 파일이 없습니다. 경로를 확인해주세요: {PARQUET_PATH}")

    if df is None:
        return None, None, None, None

    # ==========================================
    # 검색 조건 컨트롤 패널
    # ==========================================
    st.markdown("### 🔍 분석 조건 설정")
    
    col1, col2 = st.columns(2)
    with col1:
        view_mode = st.pills("📊 시각화 모드 선택", [SHOW_CIRCLE_AND_BAR, SHOW_PYDECK], key="seoul_view_mode")
    
    with col2:
        if '사용월' in df.columns:
            month_list = sorted(df['사용월'].astype(str).unique().tolist(), reverse=True)
            selected_month = st.selectbox("사용월 선택", month_list, key="seoul_month")
        else:
            st.error("데이터에 '사용월' 컬럼이 없습니다.")
            st.stop()
            
    col3, col4, col5 = st.columns(3)
    with col3:
        if COL_LINE in df.columns:
            line_list = ["전체"] + sorted(df[COL_LINE].dropna().unique().tolist())
            selected_line = st.selectbox("노선 선택", line_list, key="seoul_line")
        else:
            selected_line = "전체"
            
    board_cols = [col for col in df.columns if '승차' in col]
    alight_cols = [col for col in df.columns if '하차' in col]
    
    with col4:
        selected_board = st.selectbox("시간대 탑승 선택", board_cols, key="seoul_board")
    with col5:
        selected_alight = st.selectbox("시간대 하차 선택", alight_cols, key="seoul_alight")
    
    st.markdown("<br>", unsafe_allow_html=True)
    execute_btn = st.button("조회 실행", use_container_width=True, type="primary", key="seoul_btn")

    # ==========================================
    # 조회 실행 로직 및 차트 렌더링
    # ==========================================
    if execute_btn:        
        filtered_df = df[df['사용월'].astype(str) == selected_month]
        if selected_line != "전체":
            filtered_df = filtered_df[filtered_df[COL_LINE] == selected_line]
            
        result_df = filtered_df[[COL_LINE, COL_STATION, selected_board, selected_alight]].copy()
        
        result_df[selected_board] = pd.to_numeric(result_df[selected_board].astype(str).str.replace(',', ''), errors='coerce').fillna(0).astype(int)
        result_df[selected_alight] = pd.to_numeric(result_df[selected_alight].astype(str).str.replace(',', ''), errors='coerce').fillna(0).astype(int)
        result_df = result_df.drop_duplicates()
        
        result_df[COL_BOARD_DETAIL] = result_df.apply(lambda x: f"{x[COL_LINE]}: {x[selected_board]:,}명", axis=1)
        result_df[COL_ALIGHT_DETAIL] = result_df.apply(lambda x: f"{x[COL_LINE]}: {x[selected_alight]:,}명", axis=1)
        
        grouped_df = result_df.groupby(COL_STATION).agg({
            COL_LINE: lambda x: ', '.join(x.unique()),
            selected_board: 'sum',
            selected_alight: 'sum',
            COL_BOARD_DETAIL: lambda x: '<br>'.join(x),
            COL_ALIGHT_DETAIL: lambda x: '<br>'.join(x)
        }).reset_index()
        
        # 🟢 원형 차트 / 막대 차트 모드
        if view_mode == SHOW_CIRCLE_AND_BAR:
            st.markdown("---")
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
            
            st.markdown("---")
            st.subheader(f"📌 [{selected_month}] 조회 결과")
            st.dataframe(result_df[[COL_LINE, COL_STATION, selected_board, selected_alight]], use_container_width=True, hide_index=True)
            
            return None, None, None, None

        # 🟢 Pydeck 3D 지도 모드
        elif view_mode == SHOW_PYDECK:
            coord_df = load_file_data(METRO_PATH_SEOUL)

            if coord_df is not None:
                if COL_STATION_ORIGIN in coord_df.columns and COL_STATION not in coord_df.columns:
                    coord_df = coord_df.rename(columns={COL_STATION_ORIGIN: COL_STATION})
                
                coord_df = coord_df.drop_duplicates(subset=[COL_STATION])
                map_df = pd.merge(grouped_df, coord_df, on=COL_STATION, how='inner')
                
                if not map_df.empty and COL_LAT in map_df.columns and COL_LON in map_df.columns:
                    
                    map_df['board_count'] = map_df[selected_board]
                    map_df['alight_count'] = map_df[selected_alight]
                    
                    map_df['board_count_str'] = map_df['board_count'].apply(lambda x: f"{int(x):,}")
                    map_df['alight_count_str'] = map_df['alight_count'].apply(lambda x: f"{int(x):,}")
                    
                    # 🔥 통합 지도를 위한 공통 컬럼 생성
                    map_df['역명'] = map_df[COL_STATION]
                    map_df['승하차합계'] = map_df['board_count'] # 원본 코드의 get_elevation이 승차 기준이었습니다.
                    map_df['노선정보'] = map_df[COL_LINE]
                    map_df['승차정보'] = map_df['board_count_str']
                    map_df['하차정보'] = map_df['alight_count_str']

                    center_lat = map_df[COL_LAT].mean()
                    center_lon = map_df[COL_LON].mean()

                    map_container = st.container()

                    st.markdown("---")
                    st.subheader("📋 데이터 표")
                    st.dataframe(result_df[[COL_LINE, COL_STATION, selected_board, selected_alight]], use_container_width=True, hide_index=True)

                    # 부모 모듈(in_out_data.py)에 지도 데이터와 중심 좌표를 넘겨줌
                    return map_df, center_lat, center_lon, map_container
                else:
                    st.error("⚠️ 병합된 데이터에 매핑할 수 있는 좌표가 없습니다.")
                    return None, None, None, None
            else:
                st.warning(f"⚠️ 폴더 내에 {METRO_PATH_SEOUL} 파일을 찾을 수 없습니다.")
                return None, None, None, None

    # 조회를 누르지 않은 경우
    return None, None, None, None