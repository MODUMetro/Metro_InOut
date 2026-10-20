import streamlit as st
import pandas as pd
import plotly.express as px
import os
from pathlib import Path

# 설정 파일이 있다면 임포트 (여기서는 상수로 대체 가능)
from settings import SHOW_CIRCLE_AND_BAR, SHOW_PYDECK, BUSAN_METRO_BOARDING_DATA_PATH, BUSAN_METRO_BOARDING_DATA_PARQUET_PATH, BUSAN_METRO_POSITION
from util.utils import load_common_data

# ==========================================
# 기본 상수 및 설정
# ==========================================
COL_STATION = '지하철역'
COL_BOARD = '승차'
COL_ALIGHT = '하차'

@st.cache_data
def load_busan_data(file_path):
    """부산 승하차 데이터를 로드하고 '년월' 컬럼을 생성합니다."""
    # 1. 공통 로더로 데이터 먼저 읽기
    df = load_common_data(file_path)
    if df is None:
        return None
    
    # '2023-01-01' 형태에서 '2023-01' 추출
    if '년월일' in df.columns:
        df['년월'] = df['년월일'].str.slice(0, 7)
    return df

@st.cache_data
def load_busan_coords(file_path):
    """부산 역별 위경도 좌표를 로드합니다."""
    if not os.path.exists(file_path):
        return None
    return pd.read_csv(file_path, encoding='utf-8')

def render_busan():
    """부산 도시철도 UI 렌더링 및 분석 로직"""
    
    # ==========================================
    # 데이터 로드
    # ==========================================
    with st.expander("📁 부산 데이터 로드 상태 (클릭해서 열기)", expanded=False):
        df = load_busan_data(BUSAN_METRO_BOARDING_DATA_PARQUET_PATH)
        coord_df = load_busan_coords(BUSAN_METRO_POSITION)
        
        if df is not None and coord_df is not None:
            st.success("✅ 부산 승하차 및 좌표 데이터 로드 완료")
        else:
            st.error("⚠️ 데이터 파일이 없습니다. 경로를 확인해주세요.")
            return None, None, None, None

    # ==========================================
    # 검색 조건 컨트롤 패널
    # ==========================================
    st.markdown("### 🔍 부산 분석 조건 설정")
    
    col1, col2 = st.columns(2)
    with col1:
        view_mode = st.pills("📊 시각화 모드 선택", [SHOW_CIRCLE_AND_BAR, SHOW_PYDECK], key="busan_view_mode")
    
    with col2:
        month_list = sorted(df['년월'].unique().tolist(), reverse=True)
        selected_month = st.selectbox("사용월 선택", month_list, key="busan_month")
            
    col3, col4 = st.columns(2)
    # 부산은 시간대 컬럼이 '01시-02시'부터 '24시-01시'까지 존재합니다.
    time_cols = [col for col in df.columns if '시-' in col]
    
    with col3:
        selected_time = st.selectbox("조회할 시간대 선택", time_cols, key="busan_time")
    
    with col4:
        # 요일 필터 추가 (부산 데이터 특징 활용)
        day_type = st.radio("요일 구분", ["전체", "평일", "주말/휴일"], horizontal=True, key="busan_day_type")
    
    st.markdown("<br>", unsafe_allow_html=True)
    execute_btn = st.button("조회 실행", use_container_width=True, type="primary", key="busan_btn")

    # ==========================================
    # 조회 실행 로직 및 차트 렌더링
    # ==========================================
    if execute_btn:        
        # 조건 필터링
        filtered_df = df[df['년월'] == selected_month]
        
        if day_type == "평일":
            filtered_df = filtered_df[~filtered_df['요일'].isin(['토', '일'])]
        elif day_type == "주말/휴일":
            filtered_df = filtered_df[filtered_df['요일'].isin(['토', '일'])]
            
        # '구분' (승차/하차) 컬럼을 가로로 언피벗 (Pivot)
        # 역별로 묶어서 선택한 시간대의 인원수를 합산합니다.
        pivot_df = filtered_df.pivot_table(
            index=COL_STATION, 
            columns='구분', 
            values=selected_time, 
            aggfunc='sum'
        ).reset_index().fillna(0)
        
        # 혹시 승차나 하차 데이터가 없는 경우를 대비한 방어 코드
        if COL_BOARD not in pivot_df.columns: pivot_df[COL_BOARD] = 0
        if COL_ALIGHT not in pivot_df.columns: pivot_df[COL_ALIGHT] = 0
        
        # 🟢 원형 차트 / 막대 차트 모드
        if view_mode == SHOW_CIRCLE_AND_BAR:
            st.markdown("---")
            st.subheader(f"🏆 {selected_time} 부산 도시철도 Top 10 비중 (원형 차트)")
            
            col1, col2 = st.columns(2)
            
            top10_board = pivot_df.sort_values(by=COL_BOARD, ascending=False).head(10)
            fig_board = px.pie(
                top10_board, values=COL_BOARD, names=COL_STATION, 
                title=f"📈 {selected_time} 승차 Top 10", hole=0.4
            )
            fig_board.update_traces(textposition='inside', textinfo='percent+label')
            
            top10_alight = pivot_df.sort_values(by=COL_ALIGHT, ascending=False).head(10)
            fig_alight = px.pie(
                top10_alight, values=COL_ALIGHT, names=COL_STATION, 
                title=f"📉 {selected_time} 하차 Top 10", hole=0.4
            )
            fig_alight.update_traces(textposition='inside', textinfo='percent+label')
            
            with col1: st.plotly_chart(fig_board, use_container_width=True)
            with col2: st.plotly_chart(fig_alight, use_container_width=True)
                
            st.markdown("---")
            st.subheader(f"📊 {selected_time} 부산 도시철도 Top 10 막대 차트")
            col3, col4 = st.columns(2)
            
            fig_bar_board = px.bar(
                top10_board, x=COL_STATION, y=COL_BOARD,
                title=f"📈 {selected_time} 승차 인원", text_auto='.2s'
            )
            fig_bar_alight = px.bar(
                top10_alight, x=COL_STATION, y=COL_ALIGHT,
                title=f"📉 {selected_time} 하차 인원", text_auto='.2s'
            )
            
            with col3: st.plotly_chart(fig_bar_board, use_container_width=True)
            with col4: st.plotly_chart(fig_bar_alight, use_container_width=True)
            
            st.markdown("---")
            st.subheader(f"📌 [{selected_month}] {selected_time} 상세 조회 결과")
            st.dataframe(pivot_df, use_container_width=True, hide_index=True)
            
            return None, None, None, None

        # 🟢 Pydeck 3D 지도 모드
        elif view_mode == SHOW_PYDECK:
            # 부산 좌표 데이터 구조: ['운영노선', '역명', '위도', '경도']
            coord_df = coord_df.rename(columns={'역명': COL_STATION})
            coord_df = coord_df.drop_duplicates(subset=[COL_STATION])
            
            # 승하차 데이터와 위경도 데이터 병합
            map_df = pd.merge(pivot_df, coord_df, on=COL_STATION, how='inner')
            
            if not map_df.empty and '위도' in map_df.columns and '경도' in map_df.columns:
                # 부모 모듈(in_out_data.py)의 통일된 지도 규격에 맞추기 위한 공통 컬럼 세팅
                map_df['역명'] = map_df[COL_STATION]
                # 지도 높이는 승차 기준 (또는 합계 등 목적에 맞게 변경)
                map_df['승하차합계'] = map_df[COL_BOARD]  
                
                # 상세 툴팁 텍스트
                map_df['노선정보'] = map_df.get('운영노선', '알수없음')
                map_df['승차정보'] = map_df[COL_BOARD].apply(lambda x: f"{int(x):,}")
                map_df['하차정보'] = map_df[COL_ALIGHT].apply(lambda x: f"{int(x):,}")

                # 부산의 지도 중심점 계산
                center_lat = map_df['위도'].mean()
                center_lon = map_df['경도'].mean()

                map_container = st.container()

                st.markdown("---")
                st.subheader(f"📋 {selected_time} 데이터 표")
                # 보여줄 컬럼만 선택하여 표기
                display_cols = [COL_STATION, COL_BOARD, COL_ALIGHT]
                if '운영노선' in map_df.columns:
                    display_cols.insert(0, '운영노선')
                    
                st.dataframe(map_df[display_cols], use_container_width=True, hide_index=True)

                # 🚀 in_out_data.py 로 데이터 및 중심 좌표 반환
                return map_df, center_lat, center_lon, map_container
            else:
                st.error("⚠️ 병합된 데이터에 매핑할 수 있는 좌표가 없습니다. 역명 표기를 확인해주세요.")
                return None, None, None, None

    # 조회를 누르지 않은 경우 빈 값 반환
    return None, None, None, None