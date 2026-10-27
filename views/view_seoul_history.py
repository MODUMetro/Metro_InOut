import streamlit as st
import pandas as pd
import plotly.express as px
from settings import PARQUET_PATH
from util.utils import load_common_data

# ==========================================
# 상수데이터 define
AXIS_X_VALUE = '연도'
AXIS_Y_VALUE = '낮하차_합계'
METRO_STATION = '지하철역'
SUM_AFTERNOON_STOPOFF = '오후하차_합계'
SUM_EVENING_STOPOFF = '저녁하차_합계'
YEONNAM_GROUTH = '성장률(15->19)'
# ==========================================

def render_seoul_history():
    """서울 상권 흥망성쇠 UI 렌더링"""
    df_seoul = load_common_data(PARQUET_PATH)

    if df_seoul is None:
        st.error("서울 데이터를 불러올 수 없습니다.")
        return

    if AXIS_X_VALUE not in df_seoul.columns:
        df_seoul[AXIS_X_VALUE] = df_seoul['사용월'].astype(str).str[:4]

    # 시간대별 하차 인원 파생 변수 생성
    s_midday_cols = ['11시-12시 하차인원', '12시-13시 하차인원', '13시-14시 하차인원', '14시-15시 하차인원']
    s_afternoon_cols = ['13시-14시 하차인원', '14시-15시 하차인원', '15시-16시 하차인원', '16시-17시 하차인원']
    s_evening_cols = ['17시-18시 하차인원', '18시-19시 하차인원', '19시-20시 하차인원', '20시-21시 하차인원']

    df_seoul[AXIS_Y_VALUE] = df_seoul[[c for c in s_midday_cols if c in df_seoul.columns]].sum(axis=1)
    df_seoul[SUM_AFTERNOON_STOPOFF] = df_seoul[[c for c in s_afternoon_cols if c in df_seoul.columns]].sum(axis=1)
    df_seoul[SUM_EVENING_STOPOFF] = df_seoul[[c for c in s_evening_cols if c in df_seoul.columns]].sum(axis=1)

    st.header("서울 상권 흥망성쇠")

    # 성공 사례: 경의선 숲길 지하화
    with st.expander("성공 사례: 경의선 숲길 지하화 (2015~2019)", expanded=False):
        st.markdown("**2016년 5월 이후 경의중앙선 연남동 구간 지하화로 유동인구가 급증했습니다. (거대 상권인 홍대입구역은 시각적 왜곡 방지를 위해 차트에서 제외했습니다)**")
        
        stations_1 = ['가좌', '공덕', '서강대', '홍대입구']
        years_1 = ['2015', '2016', '2017', '2018', '2019']
        
        bench_df1 = df_seoul[(df_seoul[METRO_STATION].isin(stations_1)) & (df_seoul[AXIS_X_VALUE].isin(years_1))]
        
        if not bench_df1.empty:
            bench_trend_all = bench_df1.groupby([METRO_STATION, AXIS_X_VALUE])[AXIS_Y_VALUE].mean().round(0).reset_index()
            bench_trend_chart = bench_trend_all[bench_trend_all[METRO_STATION] != '홍대입구'].copy()
            
            fig_1 = px.line(
                bench_trend_chart, x=AXIS_X_VALUE, y=AXIS_Y_VALUE, color=METRO_STATION, markers=True,
                title="경의선 숲길 인근 역 낮 시간(11~15시) 유동인구 성장 추이"
            )
            fig_1.update_traces(line=dict(width=3), marker=dict(size=8))
            fig_1.update_layout(yaxis=dict(range=[10000, 45000]))
            st.plotly_chart(fig_1, use_container_width=True)
            
            bench_pivot = bench_trend_all.pivot(index=METRO_STATION, columns=AXIS_X_VALUE, values=AXIS_Y_VALUE).reset_index()
            if '2015' in bench_pivot.columns and '2019' in bench_pivot.columns:
                bench_pivot[YEONNAM_GROUTH] = ((bench_pivot['2019'] - bench_pivot['2015']) / bench_pivot['2015'] * 100)
                bench_pivot[YEONNAM_GROUTH] = bench_pivot[YEONNAM_GROUTH].apply(lambda x: f"+{x:.1f}%" if x > 0 else f"{x:.1f}%")
            st.dataframe(bench_pivot, use_container_width=True, hide_index=True)

    # 대박 사례: 성수동 팝업 성지화
    with st.expander("대박 사례: 성수동 팝업스토어 성지화", expanded=False):
        st.markdown("**과거 공장지대였던 성수동 일대가 복합문화공간과 팝업스토어의 메카로 탈바꿈하며 오후 유동인구가 폭발적으로 증가한 사례입니다.**")
        
        bench_s2 = df_seoul[df_seoul[METRO_STATION].isin(['성수', '뚝섬', '서울숲'])]
        if not bench_s2.empty:
            trend_s2 = bench_s2.groupby([METRO_STATION, AXIS_X_VALUE])[SUM_AFTERNOON_STOPOFF].mean().round(0).reset_index()
            fig_s2 = px.line(trend_s2, x=AXIS_X_VALUE, y=SUM_AFTERNOON_STOPOFF, color=METRO_STATION, markers=True,
                             title="성수동 일대 역 오후 시간(13~17시) 월평균 하차 인원 추이")
            fig_s2.update_traces(line=dict(width=3), marker=dict(size=8))
            st.plotly_chart(fig_s2, use_container_width=True)
            
            pivot_s2 = trend_s2.pivot(index=METRO_STATION, columns=AXIS_X_VALUE, values=SUM_AFTERNOON_STOPOFF).reset_index()
            st.dataframe(pivot_s2, use_container_width=True, hide_index=True)

    # 몰락과 이동: 이대·신촌에서 홍대·합정으로
    with st.expander("상권의 몰락과 이동: 이대·신촌·홍대입구·합정", expanded=False):
        st.markdown("**임대료 상승과 상권 노후화로 신촌의 저녁 유동인구가 급감하고, 그 수요가 홍대와 합정으로 완전히 흡수된 젠트리피케이션 사례입니다.**")
        
        bench_s3 = df_seoul[df_seoul[METRO_STATION].isin(['이대', '신촌', '홍대입구', '합정'])]
        if not bench_s3.empty:
            trend_s3 = bench_s3.groupby([METRO_STATION, AXIS_X_VALUE])[SUM_EVENING_STOPOFF].mean().round(0).reset_index()
            fig_s3 = px.line(trend_s3, x=AXIS_X_VALUE, y=SUM_EVENING_STOPOFF, color=METRO_STATION, markers=True,
                             title="신촌/이대 쇠퇴 및 홍대/합정 저녁 시간(17~21시) 상권 이동 추이")
            fig_s3.update_traces(line=dict(width=3), marker=dict(size=8))
            st.plotly_chart(fig_s3, use_container_width=True)
            pivot_s3 = trend_s3.pivot(index=METRO_STATION, columns=AXIS_X_VALUE, values=SUM_EVENING_STOPOFF).reset_index()
            st.dataframe(pivot_s3, use_container_width=True, hide_index=True)

    st.markdown("---")