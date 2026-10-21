import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from settings import PARQUET_PATH
from util.utils import load_common_data

# ==========================================
# 상수데이터 define
# ==========================================

# 페이지 설정
st.set_page_config(page_title="상권 흥망성쇠", layout="wide")

# 헤더 
st.markdown('<div id="top"></div>', unsafe_allow_html=True)
st.title("어떤 사건이 상권을 흥망성쇠로 만들었을까?")
st.page_link("pages/home.py", label="홈으로 돌아가기", icon="🏠")

df = load_common_data(PARQUET_PATH)

if '연도' not in df.columns:
    df['연도'] = df['사용월'].astype(str).str[:4]

if '낮하차_합계' not in df.columns:
    midday_cols = ['11시-12시 하차인원', '12시-13시 하차인원', '13시-14시 하차인원', '14시-15시 하차인원']
    df['낮하차_합계'] = df[midday_cols].sum(axis=1)

# ==========================================
# 메인 화면: 과거 벤치마크 데이터 동적 추출
# ==========================================
with st.expander("📊 성공 사례: 경의선 숲길 지하화", expanded=True): # 경의선 숲길 지하화 시점 = 2016년 5월
    st.markdown("**2016년 5월 이후 경의중앙선 연남동 구간 지하화로 유동인구 급증(시각적 왜곡을 방지하기 위해 유동인구가 지나치게 거대한 홍대입구역은 차트에서 제외했습니다)**")
    
    # 대상 경의중앙선역 (홍대입구 포함)
    all_gyeongui_stations = ['가좌', '공덕', '서강대', '홍대입구']
    target_years = ['2015', '2016', '2017', '2018', '2019']
    
    # df 안에서 해당 역과 연도만 골라냄 (전체 데이터)
    bench_df = df[(df['지하철역'].isin(all_gyeongui_stations)) & (df['연도'].isin(target_years))]
    
    if not bench_df.empty:
        # 연도별, 역별 '낮 시간 하차 합계' 1개월 평균 산출 (전체 데이터)
        bench_trend_all = bench_df.groupby(['지하철역', '연도'])['낮하차_합계'].mean().round(0).reset_index()
        
        # 차트용 데이터 분리: '홍대입구' 제외
        bench_trend_chart = bench_trend_all[bench_trend_all['지하철역'] != '홍대입구'].copy()
        
        # Plotly 꺾은선 그래프 렌더링 (차트용 데이터 사용)
        fig_bench = px.line(
            bench_trend_chart, x='연도', y='하차 합계', color='지하철역', markers=True,
            title="경의선 숲길 인근 역 낮 시간(11~15시) 여가 인구 성장 추이 (홍대입구 제외)"
        )
        fig_bench.update_traces(line=dict(width=3), marker=dict(size=8))
        # Y축 범위를 가좌/공덕 수준에 맞춰 여유있게 자동 조절
        fig_bench.update_layout(yaxis=dict(range=[10000, 45000]))
        st.plotly_chart(fig_bench, use_container_width=True)
        
        # 보기 좋은 표 형태로 피벗 변환 (전체 데이터 사용)
        bench_pivot = bench_trend_all.pivot(index='지하철역', columns='연도', values='낮하차_합계').reset_index()
        
        # 2015년 대비 2019년 성장률(%) 동적 계산
        if '2015' in bench_pivot.columns and '2019' in bench_pivot.columns:
            bench_pivot['성장률(15->19)'] = ((bench_pivot['2019'] - bench_pivot['2015']) / bench_pivot['2015'] * 100)
            bench_pivot['성장률(15->19)'] = bench_pivot['성장률(15->19)'].apply(lambda x: f"+{x:.1f}%" if x > 0 else f"{x:.1f}%")
        
        # Streamlit에 데이터프레임 표출 (홍대입구가 포함된 표)
        st.dataframe(bench_pivot, use_container_width=True, hide_index=True)
    else:
        st.warning("파일 추출에 실패했습니다.")
        
st.markdown("---")