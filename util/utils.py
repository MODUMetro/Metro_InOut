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