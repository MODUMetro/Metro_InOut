import streamlit as st

# 페이지 전체 기본 설정은 여기서 한 번만 해줍니다.
st.set_page_config(page_title="통합 대시보드", layout="wide")

# 1. 각 페이지를 코드로 정의 (pages 폴더 안의 파일들을 바라보게 합니다)
page_main = st.Page("pages/home.py", title="🏠 메인 화면", default=True)
page_inout = st.Page("pages/in_out_data.py", title="📊 유동인구 데이터 분석")
page_nowon = st.Page("pages/under_ground.py", title="🏪 노원/구로 지하화 검토")
page_subway = st.Page("pages/subway_app.py", title="🚇 지하철 승하차 예측 대시보드")

# 2. 사이드바 네비게이션 메뉴 구성
pg = st.navigation([page_main, page_inout, page_nowon, page_subway])

# 3. 구성한 페이지 묶음을 실행
pg.run()

#깃허브 올리기 위한 변경 

#### 깃허브