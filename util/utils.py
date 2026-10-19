import streamlit as st
import streamlit.components.v1 as components

def block_right_click_render_pydeck():
    """st.pydeck_chart 렌더링 후 우클릭(컨텍스트 메뉴)을 원천 차단합니다."""
    components.html(
        """
        <script>
        const parentDoc = window.parent.document;
        
        // 1. 캡처링(Capturing, 세 번째 인자 true)을 사용하여 새로 생성된 요소들의 우클릭 이벤트를 최상단에서 먼저 가로채서 차단
        parentDoc.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            e.stopPropagation();
        }, true);
        
        // 2. 문서 전체의 우클릭 속성을 직접 덮어씌워 이중 차단 (페이지를 다시 열 때마다 강제 갱신)
        parentDoc.oncontextmenu = function(e) {
            e.preventDefault();
            return false;
        };
        </script>
        """,
        height=0,
        width=0
    )

def hide_sidebar():
    """메인 홈 화면 등에서 사이드바와 햄버거 메뉴를 완전히 숨기는 기능"""
    st.markdown(
        """
        <style>
            /* 좌측 사이드바 영역 자체를 완전히 숨김 */
            [data-testid="stSidebar"] { display: none !important; }
            /* 모바일 화면 상단의 사이드바 열기(햄버거) 버튼 숨김 */
            [data-testid="collapsedControl"] { display: none !important; }
        </style>
        """,
        unsafe_allow_html=True
    )

def move_scroll_up():
    """ 스크롤 맨 위로 올리기 버튼 """
    st.markdown(
        """
        <style>
        .scroll-to-top {
            position: fixed;
            bottom: 30px;
            right: 30px;
            background-color: #ff4b4b;
            color: white;
            border: none;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            font-size: 24px;
            cursor: pointer;
            z-index: 9999;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            display: flex;
            align-items: center;
            justify-content: center;
            text-decoration: none;
        }
        .scroll-to-top:hover {
            background-color: #ff3333;
            color: white;
        }
        </style>
        <a href="#top" class="scroll-to-top" title="맨 위로">↑</a>
        """,
        unsafe_allow_html=True
    )