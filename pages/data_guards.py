#data_guards.py
"""
여러 페이지(subway_app.py, model_comparison_app.py 등)가 공통으로 쓰는
Streamlit UI 가드(guard) 함수 모음.

CSV 원본 존재 여부 체크처럼, "이게 없으면 친절한 메시지를 띄우고 멈춘다"는
로직이 페이지마다 필요한데, 이걸 각 페이지 파일에 따로따로 정의하면
말 그대로 같은 함수가 중복되니까 여기 한 곳에서만 정의하고 다른 페이지는
전부 여기서 import해서 씀.

폴더 구조 전제:
  project_folder/
    main.py
    settings.py
    resource/
    pages/
      data_guards.py          <- 이 파일 (pages 폴더 안)
      subway_app.py           <- 여기서 이 파일을 import해서 씀
      model_comparison_app.py <- 여기서도 이 파일을 import해서 씀
"""

import sys
from pathlib import Path

import streamlit as st

# 프로젝트 루트(pages/의 부모 폴더)에 있는 settings.py를 확실히 찾도록 경로 추가
sys.path.append(str(Path(__file__).resolve().parent.parent))


def ensure_file_exists(file_path):
    """
    파일 원본이 없으면 raw FileNotFoundError 트레이스백 대신
    친절한 경고 메시지를 띄우고 스크립트 실행을 멈춤.
    """
        
    if not file_path.exists():
        st.error(
            "지정된 경로에서 파일을 찾을 수 없어 읽지 못했습니다.\n\n"
            f"찾으려고 한 경로: `{file_path}`\n\n"
            "resource 폴더 위치나 프로젝트 폴더 구조가 원래 전제와 맞는지 확인해 주세요."
        )
        st.stop()