#=========================================================
# admin_auth.py
# 관리자 페이지. DB에 관리자 테이블 암호와 일치하는지 확인하는 역할
# supabase 모듈을 사용하기 위한 설치 명령어: pip install supabase python-dotenv
#=========================================================
import os
import hashlib
import shutil
import time
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client, Client
from pages.client_list import show_client_management

# =====================================================================================
# 환경 설정 및 초기화
# Supabase 객체 초기화
load_dotenv() 
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# 챗봇 캐싱 객체 초기화
CHROMA_PERSIST_DIR = "./chroma_cache"
FORMAT_LIMIT = 1024
# =====================================================================================

# =====================================================================================
# 용량 계산 함수

def get_folder_size(folder_path):
    total_size = 0
    if os.path.exists(folder_path):
        for dirpath, _, filenames in os.walk(folder_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
    return total_size

def format_size(size_bytes):
    if size_bytes < FORMAT_LIMIT:
        return f"{size_bytes} B"
    elif size_bytes < FORMAT_LIMIT * FORMAT_LIMIT:
        return f"{size_bytes / FORMAT_LIMIT:.1f} KB"
    elif size_bytes < FORMAT_LIMIT * FORMAT_LIMIT * FORMAT_LIMIT:
        return f"{size_bytes / (FORMAT_LIMIT * FORMAT_LIMIT):.2f} MB"
    else:
        return f"{size_bytes / (FORMAT_LIMIT * FORMAT_LIMIT * FORMAT_LIMIT):.2f} GB"
# =====================================================================================

# 화면 구성 및 인증 함수 정의
def show_admin_page():
    st.subheader("관리자 페이지")
    st.markdown('<div id="top"></div>', unsafe_allow_html=True)    
    st.page_link("pages/home.py", label="홈으로 돌아가기", icon="🏠")
    
    if "is_admin_logged_in" not in st.session_state:
        st.session_state["is_admin_logged_in"] = False

    if not st.session_state["is_admin_logged_in"]:
        st.write("관리자 암호를 입력하세요.")
        secret_key = st.text_input("Admin Key", type="password", label_visibility="collapsed")
        
        if st.button("로그인",use_container_width=True):
            if secret_key:
                input_hash = hashlib.sha256(secret_key.encode()).hexdigest()
                response = supabase.table("admin_auth").select("key_hash").eq("role", "admin").execute()
                
                if response.data and response.data[0]["key_hash"] == input_hash:
                    st.session_state["is_admin_logged_in"] = True
                    st.rerun()
                else:
                    st.error("암호가 일치하지 않습니다.")
    # 로그인 성공 상태 (관리자 대시보드)
    else:
        # 상단 헤더: 성공 메시지와 로그아웃 버튼 레이아웃 분리
        st.success("관리자 인증 성공")
    
        if st.button("로그아웃", use_container_width=True):
            st.session_state["is_admin_logged_in"] = False
            st.rerun()
          
        st.markdown("---")
        
        # 챗봇 캐시 관리 UI
        st.markdown("### 🧠 챗봇 DB 캐시 관리")
        cache_size = get_folder_size(CHROMA_PERSIST_DIR)
        st.metric(label="현재 누적된 캐시 용량", value=format_size(cache_size))
        
        if st.button("🗑️ 학습 캐시 전체 비우기", use_container_width = True):
            if os.path.exists(CHROMA_PERSIST_DIR):
                shutil.rmtree(CHROMA_PERSIST_DIR)
                st.success("✅ 캐시가 성공적으로 삭제되었습니다!")
            else:
                st.warning("⚠️ 삭제할 캐시 폴더가 존재하지 않습니다.")
            time.sleep(1.5)
            st.rerun()
            
        st.markdown("---")
        
        # 기존 고객 관리 UI 호출
        show_client_management()

# 정의된 함수를 실제로 호출하여 화면에 렌더링
show_admin_page()