import streamlit as st
import pandas as pd
import plotly.express as px
from settings import BUSAN_METRO_BOARDING_DATA_PARQUET_PATH, BUSAN_DATA_PATH
from util.utils import load_common_data

# ==========================================
# 상수데이터 define
AXIS_X_VALUE = '연도'
METRO_STATION = '지하철역'
SUM_AFTERNOON_STOPOFF = '오후하차_합계'
GROUTH_MINISTY_BUSAN = '증감률(25->26)' 
BOARDING_SUM_DAILY = '일일_승하차_합계'
COMMERCIAL_DISTRICT = '상권(동)'
AVERAGE_USE_MONEY = '평균이용금액'
# ==========================================

def render_busan_history():
    """부산 상권 흥망성쇠 UI 렌더링"""
    df_busan = load_common_data(BUSAN_METRO_BOARDING_DATA_PARQUET_PATH)
    df_busan_comm = load_common_data(BUSAN_DATA_PATH)

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
        with st.expander("☕ 신구 상권 교체 및 중심 상권: 전포, 부산대", expanded=False):
            st.markdown("**카페거리로 급부상한 전포역과 상권 노후화로 하향세를 보이는 부산대역의 추이를 비교합니다.**")
            
            bench_b1 = busan_alight[busan_alight[METRO_STATION].isin(['부산대', '전포', '서면'])]
            if not bench_b1.empty:
                trend_b1 = bench_b1.groupby([METRO_STATION, AXIS_X_VALUE])[SUM_AFTERNOON_STOPOFF].mean().round(0).reset_index()
                
                # 차트용 데이터에서 '서면' 제외
                trend_chart = trend_b1[trend_b1[METRO_STATION] != '서면'].copy()
                
                fig_b1 = px.line(trend_chart, x=AXIS_X_VALUE, y=SUM_AFTERNOON_STOPOFF, color=METRO_STATION, markers=True,
                                 title="전포역, 부산대역 오후 시간(13~17시) 일평균 하차 인원 교차 추이")
                fig_b1.update_traces(line=dict(width=3), marker=dict(size=8))
                # Y축 숫자 쉼표(천 단위) 포맷 적용
                fig_b1.update_layout(yaxis=dict(tickformat=","))
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
                
                # 표 숫자 쉼표 포맷 적용
                format_dict_b1 = {y: "{:,.0f}" for y in years}
                st.dataframe(pivot_b1.style.format(format_dict_b1), use_container_width=True, hide_index=True)

        with st.expander("🏢 공공기관 이전 효과: 해양수산부 부산 이전", expanded=False):
            st.markdown("**2025년 12월 해양수산부의 부산 이전으로 인해 인접한 부산진역, 좌천역, 초량역의 유동인구와 배후 상권(수정1·2동, 좌천동, 범일5동)의 매출 증감 현황을 분석합니다.**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🚇 인접 지하철역 일평균 승하차 인원 변화**")
                time_cols = [c for c in df_busan.columns if '시-' in c]
                df_busan[BOARDING_SUM_DAILY] = df_busan[time_cols].sum(axis=1)
                
                target_stations = ['부산진', '좌천', '초량']
                bench_b2_sub = df_busan[df_busan[METRO_STATION].isin(target_stations)].copy()
                
                if not bench_b2_sub.empty:
                    bench_b2_sub = bench_b2_sub[bench_b2_sub[AXIS_X_VALUE].isin(['2025', '2026'])]
                    trend_b2_sub = bench_b2_sub.groupby([METRO_STATION, AXIS_X_VALUE])[BOARDING_SUM_DAILY].mean().round(0).reset_index()
                    
                    if not trend_b2_sub.empty:
                        fig_b2_sub = px.bar(trend_b2_sub, x=AXIS_X_VALUE, y=BOARDING_SUM_DAILY, color=METRO_STATION, barmode='group',
                                         title="부산진·좌천·초량역 일평균 승하차 인원")
                        # Y축 숫자 쉼표 포맷 적용
                        fig_b2_sub.update_layout(yaxis=dict(tickformat=","))
                        st.plotly_chart(fig_b2_sub, use_container_width=True)
                        
                        pivot_b2_sub = trend_b2_sub.pivot(index=METRO_STATION, columns=AXIS_X_VALUE, values=BOARDING_SUM_DAILY).reset_index()
                        if '2025' in pivot_b2_sub.columns and '2026' in pivot_b2_sub.columns:
                            pivot_b2_sub[GROUTH_MINISTY_BUSAN] = ((pivot_b2_sub['2026'] - pivot_b2_sub['2025']) / pivot_b2_sub['2025'] * 100)
                            pivot_b2_sub[GROUTH_MINISTY_BUSAN] = pivot_b2_sub[GROUTH_MINISTY_BUSAN].apply(lambda x: f"+{x:.1f}%" if pd.notna(x) and x > 0 else (f"{x:.1f}%" if pd.notna(x) else "-"))
                        
                        # 표 숫자 쉼표 포맷 적용
                        years_sub = [str(c) for c in pivot_b2_sub.columns if str(c).isdigit()]
                        format_dict_sub = {y: "{:,.0f}" for y in years_sub}
                        st.dataframe(pivot_b2_sub.style.format(format_dict_sub), use_container_width=True, hide_index=True)

            with col2:
                st.markdown("**💳 배후 상권 평균이용금액 변화**")
                if df_busan_comm is not None and '기준년월' in df_busan_comm.columns:
                    df_busan_comm[AXIS_X_VALUE] = df_busan_comm['기준년월'].astype(str).str[:4]
                    
                    target_dongs = ['수정1동', '수정2동', '좌천동', '범일5동']
                    pattern = '|'.join(target_dongs)
                    bench_b2_comm = df_busan_comm[df_busan_comm['행정동명'].str.contains(pattern, na=False)].copy()
                    
                    if not bench_b2_comm.empty:
                        bench_b2_comm = bench_b2_comm[bench_b2_comm[AXIS_X_VALUE].isin(['2025', '2026'])]
                        bench_b2_comm[COMMERCIAL_DISTRICT] = bench_b2_comm['행정동명'].apply(lambda x: next((d for d in target_dongs if d in x), x))
                        bench_b2_comm[AVERAGE_USE_MONEY] = pd.to_numeric(bench_b2_comm[AVERAGE_USE_MONEY], errors='coerce').fillna(0)
                        
                        trend_b2_comm = bench_b2_comm.groupby([COMMERCIAL_DISTRICT, AXIS_X_VALUE])[AVERAGE_USE_MONEY].mean().round(0).reset_index()
                        
                        if not trend_b2_comm.empty:
                            fig_b2_comm = px.bar(trend_b2_comm, x=AXIS_X_VALUE, y=AVERAGE_USE_MONEY, color=COMMERCIAL_DISTRICT, barmode='group',
                                             title="인근 상권 월별 일평균 소비매출액")
                            # Y축 숫자 쉼표 및 '원' 단위 포맷 적용 (소수점 없음)
                            fig_b2_comm.update_layout(yaxis=dict(tickformat=",", ticksuffix="원"))
                            st.plotly_chart(fig_b2_comm, use_container_width=True)
                            
                            pivot_b2_comm = trend_b2_comm.pivot(index=COMMERCIAL_DISTRICT, columns=AXIS_X_VALUE, values=AVERAGE_USE_MONEY).reset_index()
                            if '2025' in pivot_b2_comm.columns and '2026' in pivot_b2_comm.columns:
                                pivot_b2_comm[GROUTH_MINISTY_BUSAN] = ((pivot_b2_comm['2026'] - pivot_b2_comm['2025']) / pivot_b2_comm['2025'] * 100)
                                pivot_b2_comm[GROUTH_MINISTY_BUSAN] = pivot_b2_comm[GROUTH_MINISTY_BUSAN].apply(lambda x: f"+{x:.1f}%" if pd.notna(x) and x > 0 else (f"{x:.1f}%" if pd.notna(x) else "-"))
                            
                            # 표 숫자 쉼표 및 '원' 단위 포맷 적용 (소수점 없음)
                            years_comm = [str(c) for c in pivot_b2_comm.columns if str(c).isdigit()]
                            format_dict_comm = {y: "{:,.0f}원" for y in years_comm}
                            st.dataframe(pivot_b2_comm.style.format(format_dict_comm), use_container_width=True, hide_index=True)
                    else:
                        st.warning("해당 상권의 매출 데이터를 찾을 수 없습니다.")
                else:
                    st.warning("상권 매출 데이터 파일(busan_commercial.csv)을 로드하지 못했습니다.")

    st.markdown("---")