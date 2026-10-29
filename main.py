import streamlit as st

# ---------------------------------------------------------
# 본 웹 앱(Streamlit UI) 영역: streamlit run 명령을 받은 후 작동
# ---------------------------------------------------------
st.set_page_config(page_title="도시 맥박", layout="wide")

# 각 페이지를 코드로 정의 (pages 폴더 안의 파일들을 바라보게 합니다)
page_main = st.Page("pages/home.py", title="🏠 메인 화면", default=True)
page_inout = st.Page("pages/in_out_data.py", title="📊 유동인구 데이터 분석")
page_rise_fall = st.Page("pages/commercial_rise_fall.py", title="🏪 상권흥망성쇠")
#page_subway = st.Page("pages/subway_app.py", title="🚇 지하철 승하차 예측 대시보드")
#page_comparison = st.Page("pages/model_comparison_app.py", title="⚖️ LightGBM vs XGBoost 비교")
page_top3 = st.Page("pages/commercial_top3.py", title="🏙️ 지역별 TOP3 업종")
page_chatbot = st.Page("pages/chatbot.py", title="챗봇으로 물어보세요")
page_admin = st.Page("pages/admin_auth.py", title="관리자 페이지")

# 2. 사이드바 네비게이션 메뉴 구성
pg = st.navigation([page_admin, page_main, page_inout, page_rise_fall, page_top3, page_chatbot], position="hidden")

# 3. 구성한 페이지 묶음을 실행
pg.run()