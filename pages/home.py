import streamlit as st
from settings import COPYRIGHT_FULL, BUSAN_SOURCE_CAPTION
from util.utils import hide_sidebar

# 사이드바 숨김 함수 호출
hide_sidebar()

# 외부 CSS 파일 불러오기
with open("style/mainstyle.css", "r", encoding="utf-8") as f:
    css = f.read()
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# 메인 타이틀
st.title("돈이 모이는 숨은 꿀상권 발굴 플랫폼")
st.markdown("**사장님의 성공적인 창업과 투자를 위해, 데이터에 숨겨진 '진짜 가치'를 찾아드립니다.**")
st.markdown("---")

# 기능별 폴더형 UI
with st.expander("내 타겟 고객이 몰리는 골든타임 역 찾기"):
    st.write("직장인 점심, 심야 등 내가 원하는 시간대에 지갑을 여는 사람들이 가장 많이 내리는 역을 추천합니다.")
    st.page_link("pages/in_out_data.py", label="유동인구 분석 컨설팅 시작하기", icon="🚇")

with st.expander("우리 동네 블루오션, 독점 가능 업종 찾기"):
    st.write("경쟁이 치열한 레드오션을 피해, 해당 지역에서 유독 수요가 몰리는 '특화도 1위' 업종을 발굴해 드립니다.")
    st.page_link("pages/commercial_top3.py", label="지역별 숨은 유망 업종 찾기", icon="💎")

with st.expander("상권 흥망성쇠"):
    st.write("어떤 이슈가 흥망성쇠를 결정했을까?")
    st.page_link("pages/under_ground.py", label="상권 흥망성쇠 보기", icon="📈")

with st.expander("피크타임 & 유동인구 예측"):
    st.write(
        "월별 시간대별 승하차 데이터를 바탕으로 지하철 이용 인원을 예측합니다. "
        "예측값은 해당 월의 시간대별 누적 인원이며, "
        "일별·실시간 예측은 아닙니다."
    )
    st.page_link(
        "pages/subway_app.py",
        label="지하철 시간대별 승하차 인원 예측 보기",
        icon="⏰"
    )


# 자료 출처
with st.expander("자료 출처"):
    st.write(COPYRIGHT_FULL)
    st.write(BUSAN_SOURCE_CAPTION)

st.markdown("<br><br>", unsafe_allow_html=True)

# Admin Key
secret_key = st.text_input("Admin Key", type="password", label_visibility="collapsed")

if secret_key == "qwer":
    st.page_link("pages/model_comparison_app.py", label="ML 모델 성능 비교 대시보드", icon="⚖️")
