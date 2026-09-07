import streamlit as st

st.title("🏙️ 통합 상권 & 유동인구 분석 대시보드")
st.markdown("원하시는 분석 메뉴를 클릭하거나 좌측 사이드바 메뉴를 이용해주세요.")

st.markdown("---")

# --- 첫 번째 행 (Row 1) ---
st.subheader("📊 지하철 유동인구 분석")
st.write("시간대별 승하차 인원 Top 10 도넛 차트 및 호선별 누적 막대 차트를 확인합니다.")
st.page_link("pages/in_out_data.py", label="유동인구 분석 페이지로 이동", icon="🚇")

st.markdown("---")

# -- 두 번째 행 (Row 2) ---
st.subheader("🏪 노원/구로 지하화 검토")
st.write("경의중앙선 지하화를 통해 노원/구로 지하화 내용 검토")
st.page_link("pages/under_ground.py", label="노원/구로 지하화 검토", icon="🚉")

st.markdown("---")

# --- 세 번째 행 (Row 3) ---
st.subheader("🚇 지하철 승하차 예측 대시보드")
st.write("1/3/6시간 뒤 승하차 인원 예측, 순유입·순유출 TOP 10을 확인합니다.")
st.page_link("pages/subway_app.py", label="예측 대시보드로 이동", icon="🚇")

st.markdown("---")