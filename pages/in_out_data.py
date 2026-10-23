import streamlit as st
import pydeck as pdk
import os

# 분리된 지역별 뷰 모듈 불러오기
from views.view_seoul_subway import render_seoul
from views.view_busan_subway import render_busan

from util.utils import block_right_click_render_pydeck, hide_sidebar, move_scroll_up

# ==========================================
# 자주 사용하는 텍스트 상수 지정
COL_LAT = '위도'
COL_LON = '경도'
COL_LINE = '호선명'
COL_BOARD_DETAIL = '승차_상세'
COL_ALIGHT_DETAIL = '하차_상세'
LIGHT_DAY_TIME_START = 6
LIGHT_DAY_TIME_END = 18
PAGE_TITLE = '내 매장 골든타임 찾기'
MENU_TAP_SEOUL = '서울 도시철도'
MENU_TAP_BUSAN = '부산 도시철도'
# ==========================================

# ==========================================
# 페이지 기본 설정
# 타이틀 설정
st.set_page_config(page_title=PAGE_TITLE, layout="wide", initial_sidebar_state="collapsed")
# 지도부분 우클릭 방지
block_right_click_render_pydeck()
# 사이드바 숨기기 기능
hide_sidebar()
# ==========================================

st.markdown('<div id="top"></div>', unsafe_allow_html=True)
st.title("🚇 내 타겟 고객이 몰리는 골든타임 역 찾기")
st.page_link("pages/home.py", label="홈으로 돌아가기", icon="🏠")

# 상위 페이지 버튼 UI 제공 (서울 / 부산 선택)
region = st.pills("📍 분석할 지역을 선택하세요", [MENU_TAP_SEOUL, MENU_TAP_BUSAN], default=MENU_TAP_SEOUL)

st.markdown("<br>", unsafe_allow_html=True)

# 선택된 모듈 적용 (고유 UI 및 차트 렌더링 후 지도용 데이터 반환)
if region == MENU_TAP_SEOUL:
    map_df, center_lat, center_lon, map_container = render_seoul()
elif region == MENU_TAP_BUSAN:
    map_df, center_lat, center_lon, map_container = render_busan()

# Pydeck 지도 통일 (하나의 코드로 재사용)
if map_df is not None and not map_df.empty and map_container is not None:
    with map_container:
        st.markdown("---")
        st.subheader(f"🗺️ {region} 유동인구 3D 지도")
        
        # ⚠️ 조건: 서울과 부산 모듈에서 반환하는 map_df는 
        # '경도', '위도', '승하차합계', '역명', '상세설명' 컬럼명을 통일해서 반환해야 합니다.
        layer = pdk.Layer(
            "ColumnLayer",
            data=map_df,
            get_position=["경도", "위도"],
            get_elevation="승하차합계",           
            elevation_scale=0.03,  
            radius=150 if region == "서울 지하철" else 100, # 부산은 역간 거리가 좁아 반경 조절
            get_fill_color=[255, 140, 0, 200], 
            pickable=True,
            auto_highlight=True
        )

        # 카메라 뷰 설정 (transition_duration으로 스무스하게 지역 이동)
        view_state = pdk.ViewState(
            longitude=center_lon,
            latitude=center_lat,
            zoom=11,
            pitch=50, 
            bearing=0,
            transition_duration=2000, # 2초 애니메이션
        )

        carto_api_key = os.getenv("CARTO_API_KEY", "")
        CARTO_DARK = f"https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json?api_key={carto_api_key}"

        r = pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            map_style=CARTO_DARK,
            tooltip={
                "html": "<b>{역명}</b><br/>운영노선: {노선정보}<br/>선택시간 승차: {승차정보}명<br/>선택시간 하차: {하차정보}명",
                "style": {"color": "white"}
            }
        )

        st.pydeck_chart(r, use_container_width=True)

# 스크롤 맨 위로 올리기
move_scroll_up()