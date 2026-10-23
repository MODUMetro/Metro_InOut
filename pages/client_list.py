# client_list.py
# 상담 찾으러온 고객들 관리하는 사이트

import streamlit as st
import pandas as pd
from sqlalchemy import text
from setting_DB import engine, init_db

def show_client_management():
    # 테이블 최초 1회 생성 확인
    init_db()
    
    st.subheader("📝 신규 고객 상담 등록")

    with st.form("consultation_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("손님 이름*")
            phone = st.text_input("전화번호*")
        with col2:
            location = st.text_input("희망 위치 (예: 신대방2동)")
            category = st.text_input("희망 업종 (예: 복권방)")
            
        purpose = st.text_area("방문 목적 및 상담 내용")
        
        submitted = st.form_submit_button("DB에 저장하기")
        
        if submitted:
            if name and phone:
                with engine.connect() as conn:
                    conn.execute(text("""
                        INSERT INTO consultations (name, phone, location, category, purpose)
                        VALUES (:name, :phone, :location, :category, :purpose)
                    """), {"name": name, "phone": phone, "location": location, "category": category, "purpose": purpose})
                    conn.commit()
                st.success(f"{name} 손님의 상담 내역이 성공적으로 저장되었습니다.")
            else:
                st.warning("이름과 전화번호는 필수 입력 사항입니다.")
    
    st.divider()
    st.subheader("📋 고객 상담 내역 관리 (조회/수정/삭제)")
    
    # DB에서 전체 데이터 불러오기
    with engine.connect() as conn:
        df = pd.read_sql("SELECT * FROM consultations ORDER BY created_at DESC", conn)
    
    # 검색창 위젯 추가
    search_keyword = st.text_input("🔍 이름, 전화번호, 지역, 업종 등 키워드로 검색하세요")
    
    # 검색어가 있을 경우 데이터프레임 필터링
    if search_keyword:
        # 모든 컬럼(숫자형 제외)을 문자열로 변환하여 검색어가 포함되어 있는지 확인
        mask = df.astype(str).apply(lambda x: x.str.contains(search_keyword, case=False, na=False)).any(axis=1)
        filtered_df = df[mask].reset_index(drop=True)
    else:
        filtered_df = df.reset_index(drop=True)
    
    # 필터링된 데이터를 에디터에 렌더링
    edited_df = st.data_editor(
        filtered_df,
        use_container_width=True,
        num_rows="dynamic", 
        disabled=["id", "created_at"], 
        key="consultation_editor"
    )
    
    # 변경사항 저장 로직 (필터링된 데이터프레임 기준으로 인덱스 추출)
    if st.button("수정 및 삭제 반영하기"):
        changes = st.session_state["consultation_editor"]
        
        with engine.begin() as conn: 
            for row_idx, updates in changes.get("edited_rows", {}).items():
                row_id = filtered_df.iloc[row_idx]["id"]
                for col_name, new_val in updates.items():
                    conn.execute(
                        text(f"UPDATE consultations SET {col_name} = :val WHERE id = :id"),
                        {"val": new_val, "id": int(row_id)}
                    )
            
            for row_idx in changes.get("deleted_rows", []):
                row_id = filtered_df.iloc[row_idx]["id"]
                conn.execute(
                    text("DELETE FROM consultations WHERE id = :id"),
                    {"id": int(row_id)}
                )
                
        st.success("데이터베이스에 변경사항이 성공적으로 적용되었습니다.")
        st.rerun()