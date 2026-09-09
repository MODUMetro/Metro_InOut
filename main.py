import streamlit as st
import sys
import os

# ---------------------------------------------------------
# 실행기(Wrapper) 영역: exe 또는 일반 python으로 실행될 때 작동
# pyinstaller --onedir --add-data "main.py;." --add-data "pages;pages" --hidden-import settings --collect-all sklearn --collect-all streamlit --collect-all xgboost main.py
# ---------------------------------------------------------
if __name__ == "__main__":
    from streamlit import runtime
    from streamlit.web.cli import main as stcli_main
    
    # Streamlit 런타임 위에서 실행 중인지 확인
    if not runtime.exists():
        # Streamlit 런타임이 아니라면 (최초 exe 더블클릭 시)
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller 환경: 압축 해제된 임시 폴더 안의 main.py 위치
            script_path = os.path.join(sys._MEIPASS, "main.py")
        else:
            # 로컬에서 python main.py 로 직접 실행 시
            script_path = os.path.abspath(__file__)
        
        # 내부적으로 'streamlit run main.py'를 실행하도록 프로세스 덮어쓰기
        sys.argv = ["streamlit", "run", script_path, "--global.developmentMode=false"]
        sys.exit(stcli_main())


# ---------------------------------------------------------
# 본 웹 앱(Streamlit UI) 영역: streamlit run 명령을 받은 후 작동
# ---------------------------------------------------------
st.set_page_config(page_title="통합 대시보드", layout="wide")

# 1. 각 페이지를 코드로 정의 (pages 폴더 안의 파일들을 바라보게 합니다)
page_main = st.Page("pages/home.py", title="🏠 메인 화면", default=True)
page_inout = st.Page("pages/in_out_data.py", title="📊 유동인구 데이터 분석")
page_nowon = st.Page("pages/under_ground.py", title="🏪 노원/구로 지하화 검토")
page_subway = st.Page("pages/subway_app.py", title="🚇 지하철 승하차 예측 대시보드")
page_comparison = st.Page("pages/model_comparison_app.py", title="⚖️ LightGBM vs XGBoost 비교")

# 2. 사이드바 네비게이션 메뉴 구성
pg = st.navigation([page_main, page_inout, page_nowon, page_subway, page_comparison])

# 3. 구성한 페이지 묶음을 실행
pg.run()