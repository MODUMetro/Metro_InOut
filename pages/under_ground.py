import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import platform
from sklearn.ensemble import RandomForestRegressor
from pathlib import Path
import plotly.express as px

# 페이지 설정
st.set_page_config(page_title="지하화 가치 예측 시뮬레이터", layout="wide")

# 한글 폰트 설정
if platform.system() == 'Windows':
    plt.rcParams['font.family'] = 'Malgun Gothic'
elif platform.system() == 'Darwin':
    plt.rcParams['font.family'] = 'AppleGothic'
else:
    plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.unicode_minus'] = False

# ==========================================
# 0. 헤더 및 경의중앙선 학습 배경 명시 (Row 1)
# ==========================================
st.title("🚇 철도 지하화 및 상권 가치 폭발 시뮬레이터")
st.info("💡 **AI 학습 벤치마크:** 과거 **'경의선 및 경의중앙선' 지상 구간이 지하화되고 숲길로 조성된 후, 낮 시간 여가 유입과 심야 상권이 폭발적으로 증가했던 실제 성공 사례**를 머신러닝이 학습하여 미래를 예측한다.")
st.markdown("---")

# 1. 데이터 로드 및 모델 학습 (심야 시간 20시로 확대)
@st.cache_data
def load_and_train_model():
    file_path = Path(__file__).resolve().parent.parent / 'resource' / 'Subway_Line_Station_Boarding_Alighting_Information.csv'
    try:
        df = pd.read_csv(file_path, encoding='cp949')
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, encoding='utf-8')

    df['연도'] = df['사용월'].astype(str).str[:4]
    
    # 💡 20시 이후 심야시간대 확장을 위해 컬럼 변경
    midday_cols = ['11시-12시 하차인원', '12시-13시 하차인원', '13시-14시 하차인원', '14시-15시 하차인원']
    night_cols = ['20시-21시 승차인원', '21시-22시 승차인원', '22시-23시 승차인원', '23시-24시 승차인원'] 
    
    total_alight = [c for c in df.columns if '하차인원' in c]
    total_board = [c for c in df.columns if '승차인원' in c]

    for col in midday_cols + night_cols + total_alight + total_board:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

    df['낮하차_합계'] = df[midday_cols].sum(axis=1)
    df['심야승차_합계'] = df[night_cols].sum(axis=1)
    df['전체_하차합계'] = df[total_alight].sum(axis=1)
    df['전체_승차합계'] = df[total_board].sum(axis=1)

    df['기초_낮하차비중'] = df['낮하차_합계'] / df['전체_하차합계'].replace(0, np.nan)
    df['기초_심야승차비중'] = df['심야승차_합계'] / df['전체_승차합계'].replace(0, np.nan)

    available_years = sorted(df['연도'].unique())
    base_year = '2014' if '2014' in available_years else available_years[0]
    future_year = '2018' if '2018' in available_years else available_years[-1]

    df_base = df[df['연도'] == base_year].groupby('지하철역')[['전체_하차합계', '기초_낮하차비중', '기초_심야승차비중']].mean().reset_index()
    df_future = df[df['연도'] == future_year].groupby('지하철역')['낮하차_합계'].mean().reset_index()

    train_df = pd.merge(df_base, df_future, on='지하철역')
    train_df.rename(columns={'전체_하차합계': '기초_전체하차합계', '낮하차_합계': '미래_낮하차합계'}, inplace=True)
    
    train_df = train_df[train_df['기초_전체하차합계'] > 15000].copy()

    train_df['Y_낮하차_성장률'] = ((train_df['미래_낮하차합계'] - train_df['기초_전체하차합계'] * train_df['기초_낮하차비중']) 
                                 / (train_df['기초_전체하차합계'] * train_df['기초_낮하차비중'])) * 100

    gyeongui_stations = ['홍대입구', '공덕', '가좌', '서강대']
    train_df['인프라_지하화_여부'] = np.where(train_df['지하철역'].isin(gyeongui_stations), 1, 0).astype(int)
    train_df.replace([np.inf, -np.inf], np.nan, inplace=True)
    train_df.dropna(inplace=True)

    # 💡 UI 렌더링 시 직관적인 이름을 위해 컬럼명 임시 변경
    features = ['기초_낮하차비중', '기초_심야승차비중', '인프라_지하화_여부']
    X_train = train_df[features]
    y_train = train_df['Y_낮하차_성장률']

    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    return df, model, features

df, model, features = load_and_train_model()

# 🌳 [수정된 부분] 차트에는 홍대입구 제외, 표에는 전체 포함
with st.expander("📊 AI가 학습한 과거 성공 사례 (경의선 숲길 트렌드 동적 추출)", expanded=True):
    st.markdown("업로드된 지하철 원본 데이터에서 **2015년~2018년 경의선 숲길 수혜 역**의 실제 성장 트렌드를 실시간으로 추출한 결과다. (※ 시각적 왜곡을 방지하기 위해 유동인구가 지나치게 거대한 홍대입구역은 차트에서만 제외한다.)")
    
    # 1. 벤치마크 대상 전체 역 (홍대입구 포함)
    all_gyeongui_stations = ['가좌', '공덕', '서강대', '홍대입구']
    target_years = ['2015', '2016', '2017', '2018']
    
    # df 안에서 해당 역과 연도만 골라냄 (전체 데이터)
    bench_df = df[(df['지하철역'].isin(all_gyeongui_stations)) & (df['연도'].isin(target_years))]
    
    if not bench_df.empty:
        # 2. 연도별, 역별 '낮 시간 하차 합계' 1개월 평균 산출 (전체 데이터)
        bench_trend_all = bench_df.groupby(['지하철역', '연도'])['낮하차_합계'].mean().round(0).reset_index()
        
        # 3. 차트용 데이터 분리: '홍대입구' 제외
        bench_trend_chart = bench_trend_all[bench_trend_all['지하철역'] != '홍대입구'].copy()
        
        # 4. Plotly 꺾은선 그래프 렌더링 (차트용 데이터 사용)
        fig_bench = px.line(
            bench_trend_chart, x='연도', y='낮하차_합계', color='지하철역', markers=True,
            title="경의선 숲길 인근 역 낮 시간(11~15시) 여가 인구 성장 추이 (홍대입구 제외)"
        )
        fig_bench.update_traces(line=dict(width=3), marker=dict(size=8))
        # Y축 범위를 가좌/공덕 수준에 맞춰 여유있게 자동 조절
        fig_bench.update_layout(yaxis=dict(range=[10000, 45000]))
        st.plotly_chart(fig_bench, use_container_width=True)
        
        # 보기 좋은 표 형태로 피벗 변환 (전체 데이터 사용)
        bench_pivot = bench_trend_all.pivot(index='지하철역', columns='연도', values='낮하차_합계').reset_index()
        
        # 2015년 대비 2018년 성장률(%) 동적 계산
        if '2015' in bench_pivot.columns and '2018' in bench_pivot.columns:
            bench_pivot['성장률(15->18)'] = ((bench_pivot['2018'] - bench_pivot['2015']) / bench_pivot['2015'] * 100)
            bench_pivot['성장률(15->18)'] = bench_pivot['성장률(15->18)'].apply(lambda x: f"+{x:.1f}%" if x > 0 else f"{x:.1f}%")
        
        # Streamlit에 데이터프레임 표출 (홍대입구가 포함된 표)
        st.dataframe(bench_pivot, use_container_width=True, hide_index=True)
    else:
        st.warning("업로드된 데이터에 2015~2018년 경의선 데이터가 부족하여 벤치마크를 추출할 수 없다.")
        
st.markdown("---")

# ==========================================
# 사이드바 컨트롤러
# ==========================================
st.sidebar.header("🎛️ 시뮬레이터 설정")
target_station = st.sidebar.selectbox("분석 대상 역 선택", ["노원", "구로", "금천구청"])

recent_months = sorted(df['사용월'].unique(), reverse=True)[:3]
recent_df = df[df['사용월'].isin(recent_months)].groupby('지하철역')[['기초_낮하차비중', '기초_심야승차비중']].mean().reset_index()
station_data = recent_df[recent_df['지하철역'] == target_station].copy()

if station_data.empty:
    st.error(f"'{target_station}' 역의 데이터를 찾을 수 없다.")
    st.stop()

station_data['인프라_지하화_여부'] = 1
pred_growth = model.predict(station_data[features])[0]
base_midday = station_data['기초_낮하차비중'].values[0] * 100
base_night = station_data['기초_심야승차비중'].values[0] * 100

# ==========================================
# 메인 화면 (컬럼 없이 Row 단위로 위에서 아래로 배치)
# ==========================================
st.subheader(f"📌 [{target_station}역] 지하화 예측 리포트")

# Row 2: 낮 시간 지표 크게 배치
st.markdown("### ☀️ 낮 시간(11~15시) 여가 상권 폭발률")
st.metric(label="지하화 완공 후 예상 낮 시간 유입 성장률", value=f"+{pred_growth:.1f}%", delta_color="normal")
st.write(f"현재 기초 낮 하차 비중: **{base_midday:.1f}%** (이 비중이 높을수록 지하화 후 파급력이 커진다.)")

st.markdown("<br>", unsafe_allow_html=True) # 시각적 여백

# Row 3: 심야 시간 지표 크게 배치 (요청사항 2 반영)
st.markdown("### 🌙 심야 시간(20시 이후) 체류 잠재력")
st.metric(label="현재 심야(20시~24시) 승차 비중", value=f"{base_night:.1f}%")
st.write(f"노원역 학원가 하원 인파 및 야간 상권 체류 인구를 나타낸다. 이 수치가 높으면 팝업/공원 조성 시 사람들이 늦게까지 동네에 체류하게 된다.")

st.markdown("---")

# Row 4: 인사이트 텍스트 배치
st.subheader("💡 비즈니스 인사이트 요약")
st.markdown(f"""
* **과거 경의중앙선의 교훈:** 단순히 철도를 땅에 묻는 것이 아니라, 과거 경의선 숲길처럼 **기존에 잠재력을 갖춘 동네(낮/심야 기초체력)가 환경 개선 버프를 받았을 때** 유동인구가 폭발하는 법칙을 따른다.
* **낮과 밤의 시너지:** {target_station}역은 현재 **{base_night:.1f}%**라는 훌륭한 20시 이후 심야 체류 데이터를 보유하고 있다. 지하화가 완료될 경우, 낮에 유입된(+{pred_growth:.1f}%) 인구가 심야 상권까지 이어지는 메가 상권으로 거듭날 수학적 근거가 충분하다.
""")

st.markdown("---")

# Row 5: AI 뇌 구조 차트 배치
st.subheader("🧠 AI 판단 기준 (Feature Importance)")
st.markdown("AI가 경의선 사례를 바탕으로 인프라 충격을 예측할 때 가장 중요하게 본 데이터 가중치다.")

fig, ax = plt.subplots(figsize=(10, 4))
# 차트 라벨을 직관적으로 변경
display_features = ['낮 시간 하차 비중', '심야(20시 이후) 승차 비중', '지하화 공사 여부']
importance = pd.Series(model.feature_importances_, index=display_features).sort_values(ascending=True)

importance.plot(kind='barh', color='darkorange', ax=ax)
ax.set_title("AI가 분석한 상권 폭발의 핵심 원동력")
ax.set_xlabel("상대적 영향력")
st.pyplot(fig)