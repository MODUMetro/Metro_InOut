import streamlit as st
from views.view_seoul_history import render_seoul_history
from views.view_busan_history import render_busan_history
from util.utils import hide_sidebar, move_scroll_up

REGION_SEOUL = "서울"
REGION_BUSAN = "부산"

# ==========================================
# 페이지 설정
# ==========================================
st.set_page_config(page_title="상권 흥망성쇠", layout="wide")
hide_sidebar()

st.markdown('<div id="top"></div>', unsafe_allow_html=True)
st.title("📈 어떤 사건이 상권을 흥망성쇠로 만들었을까?")
st.page_link("pages/home.py", label="홈으로 돌아가기", icon="🏠")
st.markdown("<br>", unsafe_allow_html=True)

# 지역 선택버튼
region = st.pills("흥망성쇠 사례 지역", [REGION_SEOUL, REGION_BUSAN], default= REGION_SEOUL)

st.markdown("<br>", unsafe_allow_html=True)

# 선택된 지역에 따라 뷰 모듈 호출
if region == REGION_SEOUL:
    render_seoul_history()
elif region == REGION_BUSAN:
    render_busan_history()
else:
    st.info("👆 위 메뉴에서 분석할 지역(서울/부산)을 선택해 주세요.")

# 스크롤 맨 위로 올리기
move_scroll_up()