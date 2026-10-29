#=========================================================
# admin_auth.py
# 관리자 페이지. DB에 관리자 테이블 암호와 일치하는지 확인하는 역할
# supabase 모듈을 사용하기 위한 설치 명령어: pip install supabase python-dotenv
#=========================================================
import os
import hashlib
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client, Client
from pages.client_list import show_client_management

# Supabase 객체 초기화
load_dotenv() 
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# 화면 구성 및 인증 함수 정의
def show_admin_page():
    st.subheader("관리자 페이지")
    
    if "is_admin_logged_in" not in st.session_state:
        st.session_state["is_admin_logged_in"] = False

    if not st.session_state["is_admin_logged_in"]:
        st.write("관리자 암호를 입력하세요.")
        secret_key = st.text_input("Admin Key", type="password", label_visibility="collapsed")
        
        if st.button("로그인"):
            if secret_key:
                input_hash = hashlib.sha256(secret_key.encode()).hexdigest()
                response = supabase.table("admin_auth").select("key_hash").eq("role", "admin").execute()
                
                if response.data and response.data[0]["key_hash"] == input_hash:
                    st.session_state["is_admin_logged_in"] = True
                    st.rerun()
                else:
                    st.error("암호가 일치하지 않습니다.")
    else:
        st.success("관리자 인증 성공")
        if st.button("로그아웃"):
            st.session_state["is_admin_logged_in"] = False
            st.rerun()
            
        st.markdown("---")
        show_client_management()

# 핵심: 정의된 함수를 실제로 호출하여 화면에 렌더링
show_admin_page()