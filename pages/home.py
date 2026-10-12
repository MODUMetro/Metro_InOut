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

# --- 네 번째 행 (Row 4) ---
st.subheader("⚖️ LightGBM vs XGBoost 비교")
st.write("같은 조건으로 학습한 두 모델의 MAE·RMSE·R²·학습시간을 비교합니다.")
st.page_link("pages/model_comparison_app.py", label="모델 비교 페이지로 이동", icon="⚖️")
 
st.markdown("---")

# --- 다섯 번째 행 (Row 5) ---
st.subheader("🏙️ 지역별 TOP3 업종")
st.write("행정동별 매출 상위 3개 업종을 매출 규모·특화도 기준으로 확인합니다.")
st.page_link("pages/commercial_top3.py", label="지역별 TOP3 업종으로 이동", icon="🏙️")
st.markdown("---")

st.markdown("---")
st.caption(
    "본 저작물은 '서울신용보증재단'에서 '2023년' 작성하여 공공누리 제1유형으로 개방한 "
    "'서울시 상권분석서비스(추정매출-행정동)', '서울시 상권분석서비스(점포-행정동)', "
    "'서울시 상권분석서비스(상주인구-행정동)', '서울시 상권분석서비스(영역-행정동)'(작성자: 서울신용보증재단)과, "
    "'서울특별시'에서 '2015년' 작성하여 공공누리 제1유형으로 개방한 "
    "'서울시 지하철 호선별 역별 시간대별 승하차 인원 정보'(작성자: 서울특별시), "
    "'서울특별시'에서 '2022년' 작성하여 공공누리 제1유형으로 개방한 "
    "'서울시 역사마스터 정보'(작성자: 서울특별시)를 이용하였으며, "
    "해당 저작물은 [서울 열린데이터광장](https://data.seoul.go.kr)에서 무료로 다운받으실 수 있습니다. "
    "이 대시보드의 분석 결과는 위 데이터를 가공한 결과이며 서울특별시·서울신용보증재단의 공식 수치가 아닙니다."
)