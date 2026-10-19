import streamlit as st
import pandas as pd
import plotly.express as px
import pydeck as pdk
import os
from pathlib import Path
import sys
import re

from settings import PARQUET_PATH, METRO_PATH_SEOUL, TRANSER_INFORMATION, SHOW_CIRCLE_AND_BAR, SHOW_PYDECK, SUBWAY_COLORS, LINE_NAME_MAP, LINE_NAME_REGEX_MAP
from util.utils import block_right_click_render_pydeck, hide_sidebar, move_scroll_up

st.set_page_config(page_title="지하철 승하차 조회 대시보드", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 전체 페이지 마우스 우클릭 차단 및 사이드바 숨김
block_right_click_render_pydeck()
hide_sidebar()
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
        df = pd.read_parquet(source)    
    elif suffix == '.csv':
        try:
            df = pd.read_csv(source, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(source, encoding='cp949')
    else:
        raise ValueError("지원하지 않는 파일 형식입니다.")
        
    # 노선명 매핑 (settings.py의 LINE_NAME_MAP 사용. 예: 일산선 -> 3호선)
    if COL_LINE in df.columns: # 
        df[COL_LINE] = df[COL_LINE].replace(LINE_NAME_MAP)

        # 정규식 매핑 (9호선 2단계, 3단계 -> 9호선으로 통일)
        for pattern, replacement in LINE_NAME_REGEX_MAP:
            df[COL_LINE] = df[COL_LINE].str.replace(pattern, replacement, regex=True)
        
    return df

# 1. 앵커 태그를 상단에 배치하고 홈 버튼 추가
st.markdown('<div id="top"></div>', unsafe_allow_html=True)
st.title("🚇 지하철 시간대별 유동인구 탐색")
st.page_link("pages/home.py", label="홈으로 돌아가기", icon="🏠")
st.markdown(TRANSER_INFORMATION)

sys.path.append(str(Path(__file__).resolve().parent.parent))

# ==========================================
# 데이터 로드
# ==========================================
with st.expander("📁 데이터 로드 및 상태 확인 (클릭해서 열기)", expanded=False):
    # 파일 업로더
    uploaded_file = st.file_uploader("기본 파일 외에 다른 파일을 보시려면 업로드하세요", type=['csv', 'parquet'])
    
    if uploaded_file is not None:
        df = load_file_data(uploaded_file)
        st.success("✅ 새로운 파일 로드 완료")
    else:
        df = load_file_data(PARQUET_PATH)
        if df is not None:
            st.success(f"✅ 기본 데이터 자동 로드 완료")
        else:
            st.warning(f"⚠️ 폴더에 기본 파일이 없습니다. 경로를 확인해주세요: {PARQUET_PATH}")

# ==========================================
# 검색 조건 컨트롤 패널 (사이드바에서 메인 본문으로 이동)
# ==========================================
if df is not None:
    st.markdown("### 🔍 분석 조건 설정")
    
    # UI 구성을 위해 화면을 여러 칸(Column)으로 나눕니다.
    # [첫 번째 줄] - 시각화 모드, 사용월
    col1, col2 = st.columns(2)
    with col1:
        view_mode = st.selectbox("📊 시각화 모드 선택", [SHOW_CIRCLE_AND_BAR, SHOW_PYDECK])
    
    with col2:
        if '사용월' in df.columns:
            month_list = sorted(df['사용월'].astype(str).unique().tolist(), reverse=True)
            selected_month = st.selectbox("📅 사용월 선택", month_list)
        else:
            st.error("데이터에 '사용월' 컬럼이 없습니다.")
            st.stop()
            
    # [두 번째 줄] - 노선, 승차, 하차 시간대
    col3, col4, col5 = st.columns(3)
    with col3:
        if COL_LINE in df.columns:
            line_list = ["전체"] + sorted(df[COL_LINE].dropna().unique().tolist())
            selected_line = st.selectbox("🛤️ 노선 선택", line_list)
        else:
            selected_line = "전체"
            
    board_cols = [col for col in df.columns if '승차' in col]
    alight_cols = [col for col in df.columns if '하차' in col]
    
    with col4:
        selected_board = st.selectbox("시간대 탑승 선택", board_cols)
    with col5:
        selected_alight = st.selectbox("시간대 하차 선택", alight_cols)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 메인 화면을 가로지르는 큼직한 버튼
    execute_btn = st.button("조회 실행 🚀", use_container_width=True, type="primary")
    st.markdown("---")

    # ==========================================
    # 조회 실행 로직 및 결과 렌더링
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
            selected_board: 'sum',
            selected_alight: 'sum',
            COL_BOARD_DETAIL: lambda x: '<br>'.join(x),
            COL_ALIGHT_DETAIL: lambda x: '<br>'.join(x)
        }).reset_index()
        
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
            
            # 표를 그래프 아래로 이동
            st.markdown("---")
            st.subheader(f"📌 [{selected_month}] 조회 결과")
            st.dataframe(result_df[[COL_LINE, COL_STATION, selected_board, selected_alight]], use_container_width=True, hide_index=True)
    
        elif view_mode == SHOW_PYDECK:
            st.subheader("유동인구 3D 지도")        

            # 통합된 load_file_data 함수 호출
            coord_df = load_file_data(METRO_PATH_SEOUL)

            if coord_df is not None:
                carto_api_key = os.getenv("CARTO_API_KEY")

                # CARTO 벡터 타일 스타일 URL 정의 (API 키 포함)
                CARTO_LIGHT = f"https://basemaps.cartocdn.com/gl/positron-gl-style/style.json?api_key={carto_api_key}"
                CARTO_DARK = f"https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json?api_key={carto_api_key}"

                # 시간대에 따른 지도 테마 동적 변경 로직
                # "08시-09시 승차인원" 등의 텍스트에서 앞의 숫자(8)만 추출
                hour_match = re.search(r'(\d+)시', selected_board)
                if hour_match:
                    hour = int(hour_match.group(1))
                    # 06시 ~ 18시 사이는 밝은 낮 테마, 그 외는 어두운 밤 테마
                    if LIGHT_DAY_TIME_START <= hour < LIGHT_DAY_TIME_END:
                        dynamic_map_style = CARTO_LIGHT
                    else:
                        dynamic_map_style = CARTO_DARK 
                else: # 예외 발생 시 기본 어두운 테마
                    dynamic_map_style = CARTO_DARK

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
                        map_style=dynamic_map_style, # 시간때별 배경 설정 테마
                        tooltip={
                            "html": f"<b>{{{COL_STATION}}}</b><br/>선택시간 탑승: {{board_count_str}}명<br/>선택시간 하차: {{alight_count_str}}명",
                            "style": {"color": "white"}
                        }
                    )

                    st.pydeck_chart(r, use_container_width=True)

                    # 표를 3D 지도 아래로 이동
                    st.markdown("---")
                    st.subheader("📋 데이터 표")
                    st.dataframe(result_df[[COL_LINE, COL_STATION, selected_board, selected_alight]], use_container_width=True, hide_index=True)
                else:
                    st.error("⚠️ 병합된 데이터에 매핑할 수 있는 좌표가 없습니다.")
                    st.caption(f"- 승하차 역명 예시: {grouped_df[COL_STATION].head(3).tolist()}")
                    
                    st.markdown("---")
                    st.subheader("📋 데이터 표")
                    st.dataframe(result_df[[COL_LINE, COL_STATION, selected_board, selected_alight]], use_container_width=True, hide_index=True)
                    if COL_STATION in coord_df.columns:
                        st.caption(f"- 좌표 역명 예시: {coord_df[COL_STATION].head(3).tolist()}")
                        
            else:
                st.warning(f"⚠️ 폴더 내에 {METRO_PATH_SEOUL} 파일을 찾을 수 없습니다. 파일명과 위치를 다시 확인해주세요.")

# ==========================================
# 스크롤 맨 위로 올리기 버튼
# ==========================================
move_scroll_up()