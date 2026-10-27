import streamlit as st
import pandas as pd
import plotly.express as px
from settings import BUSAN_METRO_BOARDING_DATA_PARQUET_PATH
from util.utils import load_common_data

# ==========================================
# 상수데이터 define
AXIS_X_VALUE = '연도'
METRO_STATION = '지하철역'
SUM_AFTERNOON_STOPOFF = '오후하차_합계'
# ==========================================

def render_busan_history():
    """부산 상권 흥망성쇠 UI 렌더링"""
    df_busan = load_common_data(BUSAN_METRO_BOARDING_DATA_PARQUET_PATH)

    if df_busan is None:
        st.error("부산 데이터를 불러올 수 없습니다.")
        return

    st.header("부산 상권 흥망성쇠")

    if '년월일' in df_busan.columns:
        df_busan[AXIS_X_VALUE] = df_busan['년월일'].astype(str).str[:4]
        busan_alight = df_busan[df_busan['구분'] == '하차'].copy()
        
        b_afternoon_cols = ['13시-14시', '14시-15시', '15시-16시', '16시-17시']
        valid_b_after = [c for c in b_afternoon_cols if c in busan_alight.columns]
        busan_alight[SUM_AFTERNOON_STOPOFF] = busan_alight[valid_b_after].sum(axis=1)

        # 부산 상권 비교: 서면, 전포, 부산대
        with st.expander("☕ 신구 상권 교체 및 중심 상권: 전포, 부산대", expanded=True):
            st.markdown("**카페거리로 급부상한 전포역과 상권 노후화로 하향세를 보이는 부산대역의 추이를 비교합니다.**")
            
            bench_b1 = busan_alight[busan_alight[METRO_STATION].isin(['부산대', '전포', '서면'])]
            if not bench_b1.empty:
                trend_b1 = bench_b1.groupby([METRO_STATION, AXIS_X_VALUE])[SUM_AFTERNOON_STOPOFF].mean().round(0).reset_index()
                
                # 차트용 데이터에서 '서면' 제외
                trend_chart = trend_b1[trend_b1[METRO_STATION] != '서면'].copy()
                
                fig_b1 = px.line(trend_chart, x=AXIS_X_VALUE, y=SUM_AFTERNOON_STOPOFF, color=METRO_STATION, markers=True,
                                 title="전포역, 부산대역 오후 시간(13~17시) 일평균 하차 인원 교차 추이")
                fig_b1.update_traces(line=dict(width=3), marker=dict(size=8))
                st.plotly_chart(fig_b1, use_container_width=True)
                
                # 테이블에 올릴 데이터
                pivot_b1 = trend_b1.pivot(index=METRO_STATION, columns=AXIS_X_VALUE, values=SUM_AFTERNOON_STOPOFF).reset_index()

                # 가나다 순으로 올라오는 현상 막기 위해 테이블 순서 강제지정
                target_order = ['부산대', '전포', '서면']
                pivot_b1[METRO_STATION] = pd.Categorical(pivot_b1[METRO_STATION], categories=target_order, ordered=True)
                pivot_b1 = pivot_b1.sort_values(METRO_STATION).reset_index(drop=True)
                
                # 동적 증감률 계산 (첫 연도와 마지막 연도 추출)
                years = sorted([str(c) for c in pivot_b1.columns if str(c).isdigit()])
                if len(years) >= 2:
                    start_y = years[0]
                    end_y = years[-1]
                    growth_col = f'증감률({start_y[2:]}->{end_y[2:]})'
                    pivot_b1[growth_col] = ((pivot_b1[end_y] - pivot_b1[start_y]) / pivot_b1[start_y] * 100)
                    pivot_b1[growth_col] = pivot_b1[growth_col].apply(lambda x: f"+{x:.1f}%" if x > 0 else f"{x:.1f}%")
                
                st.dataframe(pivot_b1, use_container_width=True, hide_index=True)

    st.markdown("---")