import streamlit as st
from settings import COPYRIGHT_FULL, BUSAN_SOURCE_CAPTION
from util.utils import hide_sidebar

# 사이드바 숨김 함수 호출
hide_sidebar()

# 메인 타이틀
st.title("돈이 모이는 숨은 꿀상권 발굴 플랫폼")
st.markdown("**사장님의 성공적인 창업과 투자를 위해, 데이터에 숨겨진 '진짜 가치'를 찾아드립니다.**")
st.markdown("---")

st.subheader("내 타겟 고객이 몰리는 골든타임 역 찾기")
st.write("직장인 점심, 심야 등 내가 원하는 시간대에 지갑을 여는 사람들이 가장 많이 내리는 역을 추천합니다.")
st.page_link("pages/in_out_data.py", label="유동인구 분석 컨설팅 시작하기", icon="🚇")

st.markdown("---")

st.subheader("제2의 연트럴파크, 저평가 우량 상권 선점하기")
st.write("권리금이 오르기 전에 선점하세요. 철도 지하화 버프를 받았을 때 상권 가치가 폭발할 흙 속의 진주 같은 입지를 AI가 예측합니다.")
st.page_link("pages/under_ground.py", label="상권 폭발 잠재력 시뮬레이터", icon="📈")

st.markdown("---")

st.subheader("실시간 피크타임 & 유동인구 예측")
st.write("오늘 저녁 우리 매장 앞 유동인구가 얼마나 붐빌까? AI가 1/3/6시간 뒤의 인구 흐름을 예측하여 매장 운영 타이밍을 알려드립니다.")
st.page_link("pages/subway_app.py", label="실시간 유동인구 예측 보기", icon="⏰")

st.markdown("---")

st.subheader("우리 동네 블루오션, 독점 가능 업종 찾기")
st.write("경쟁이 치열한 레드오션을 피해, 해당 지역에서 유독 수요가 몰리는 '특화도 1위' 업종을 발굴해 드립니다.")
st.page_link("pages/commercial_top3.py", label="지역별 숨은 유망 업종 찾기", icon="💎")

secret_key = st.sidebar.text_input(" ", type="password", label_visibility="collapsed")

st.markdown("---")


with st.expander(f"{COPYRIGHT_FULL}"):
    st.caption(BUSAN_SOURCE_CAPTION) 
    
    # 안내문(label)이 아예 안 보이도록 collapsed 처리한 비밀번호 입력창
    secret_key = st.text_input("Admin Key", type="password", label_visibility="collapsed")

    # ML 모델 성능 비교 대시보드 보는 방법, 
    if secret_key == "qwer": 
        st.page_link("pages/model_comparison_app.py", label="ML 모델 성능 비교 대시보드", icon="⚖️")