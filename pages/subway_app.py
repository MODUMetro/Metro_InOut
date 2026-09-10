#subway_app.py

"""
지하철 시간대별 승하차 인원 - 1/3/6시간 뒤 예측 대시보드
(멀티페이지 앱에서 pages/in_out_data.py 가 render()를 불러다 쓰는 구조)

폴더 구조 전제:
  project_folder/
    main.py
    settings.py               <- 공유 설정값 (경로, HOUR_ORDER, LINE_NAME_MAP 등)
    resource/                 <- CSV 원본과 학습된 pkl이 있음
    pages/
      home.py
      in_out_data.py          <- 여기서 이 파일의 render()를 호출
      subway_model.py         <- 데이터 로딩/학습 로직
      subway_app.py           <- 이 파일

단독 테스트 실행: streamlit run pages/subway_app.py
(pkl 모델 파일이 resource 폴더에 없으면 최초 실행 시 자동으로 학습 후 저장됩니다)
"""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
import pytz

# subway_model.py(같은 pages 폴더)와 settings.py(프로젝트 루트) 둘 다 찾도록 경로 추가
_THIS_DIR = Path(__file__).resolve().parent
sys.path.append(str(_THIS_DIR))          # pages/ 폴더 (subway_model.py를 위해)
sys.path.append(str(_THIS_DIR.parent))   # 프로젝트 루트 (settings.py를 위해)

# 경로 상수(PARQUET_PATH, MODEL_PATH), HOUR_ORDER, HORIZONS는 settings.py 기준.
# 여기서 재정의하지 않고 import해서만 씀 (중복 방지)
from settings import CSV_PATH, PARQUET_PATH, MODEL_PATH, HOUR_ORDER, HORIZONS
from subway_model import (load_and_reshape, build_multihorizon_features,
                           load_or_train_models)
from data_guards import ensure_file_exists

# NOTE: st.set_page_config()는 main.py에서 앱 전체 기준으로 이미 한 번 호출했으므로
# 여기서는 절대 다시 호출하지 않음 (두 번 호출하면 StreamlitAPIException 발생)


@st.cache_data
def load_data() -> pd.DataFrame:
    ensure_file_exists(PARQUET_PATH)
    try:
        wide = load_and_reshape(PARQUET_PATH)
        return build_multihorizon_features(wide)
    except Exception as e:
        st.error(f"CSV 파일을 읽는 중 문제가 생겼습니다: {e}")
        st.stop()


@st.cache_resource
def load_models():
    if not MODEL_PATH.exists():
        ensure_file_exists(PARQUET_PATH)
        with st.spinner("처음 실행이라 모델을 학습하는 중이에요. 데이터가 커서 몇 분 정도 걸릴 수 있어요..."):
            return load_or_train_models(PARQUET_PATH, MODEL_PATH)

    # 이미 학습된 pkl이 있으면 바로 로드 (스피너 없이)
    return load_or_train_models(PARQUET_PATH, MODEL_PATH)


def render():
    """in_out_data.py 등 다른 페이지 파일에서 이 함수를 불러다 호출하면 대시보드가 그려짐"""
    df = load_data()
    models, results, feature_cols = load_models()

    st.title("🚇 지하철 시간대별 승하차 인원 예측")
    st.caption("기준 시간대까지의 직전 1~3시간대 실제값을 바탕으로, 1시간/3시간/6시간 뒤 승하차 인원을 예측합니다.")

    col1, col2 = st.columns(2)
    with col1:
        line = st.selectbox("호선", sorted(df["호선명"].unique()))
    with col2:
        stations = sorted(df.loc[df["호선명"] == line, "지하철역"].unique())
        station = st.selectbox("역", stations)

    months = sorted(df.loc[(df["호선명"] == line) & (df["지하철역"] == station), "사용월"].unique())
    latest_month = months[-1]

    now = datetime.now(pytz.timezone('Asia/Seoul'))
    current_bracket = f"{now.hour:02d}-{now.hour + 1:02d}"
    default_hour_idx = HOUR_ORDER.index(current_bracket) if current_bracket in HOUR_ORDER else 8

    use_now = st.checkbox(
        f"지금 시각({now.strftime('%m월 %d일 %H시')}) 기준으로 자동 입력",
        value=False,
        help="데이터에 있는 가장 최근 달의 같은 시간대 패턴으로 대신 계산합니다. "
             "오늘 날짜의 실제 데이터가 아니라는 점 참고해 주세요.",
    )

    if use_now:
        month = latest_month
        hour = current_bracket if current_bracket in HOUR_ORDER else HOUR_ORDER[default_hour_idx]
        st.info(
            f"데이터상 가장 최근 달인 **{latest_month // 100}년 {latest_month % 100:02d}월**의 "
            f"**{hour}시** 패턴을 기준으로 계산합니다 (오늘 날짜의 실시간 데이터는 아님)."
        )
    else:
        month = st.selectbox(
            "기준 월", months, index=len(months) - 1,
            format_func=lambda m: f"{m // 100}년 {m % 100:02d}월",
        )
        hour = st.selectbox("기준 시간대 (이 시점까지는 이미 안다고 가정)", HOUR_ORDER, index=default_hour_idx)

    if st.button("예측하기", type="primary"):
        row = df[
            (df["호선명"] == line) & (df["지하철역"] == station)
            & (df["사용월"] == month) & (df["시간대"] == hour)
        ]

        if row.empty or row[feature_cols].isna().any(axis=1).iloc[0]:
            st.warning(
                "이 조합은 직전 시간대 데이터가 부족해서 예측할 수 없어요. "
                "(하루 시작인 04-05시 근처는 lag 값이 부족할 수 있습니다)"
            )
        else:
            X = row[feature_cols]
            st.subheader(f"{line} {station}역 — {month // 100}년 {month % 100:02d}월 {hour}시 기준")

            records = []
            for h in HORIZONS:
                for target in ["승차인원", "하차인원"]:
                    pred = models[(h, target)].predict(X)[0]
                    actual_col = f"target_h{h}_{target[0]}차"
                    actual = row[actual_col].iloc[0] if actual_col in row.columns else None
                    records.append({
                        "예측시점": f"{h}시간 뒤",
                        "구분": target,
                        "예측값": round(pred),
                        "실제값(참고용)": None if pd.isna(actual) else round(actual),
                    })

            result_df = pd.DataFrame(records)
            st.dataframe(result_df, width="stretch", hide_index=True)

            # 예측시점 순서(1,3,6시간 뒤)를 고정
            chart_df = result_df.copy()
            chart_df["예측시점"] = pd.Categorical(
                chart_df["예측시점"], categories=[f"{h}시간 뒤" for h in HORIZONS], ordered=True
            )
            chart_df = chart_df.sort_values("예측시점")

            # 승차/하차가 위아래로 쌓이지(stacked) 않고, 1시간/3시간/6시간 각각에서
            # 승차-하차가 나란히(grouped) 놓이도록 stack=False.
            # 피벗하지 않고 원본(long format) 그대로 x/y/color를 지정해서,
            # 마우스오버 시 "value"/"color" 같은 애매한 이름 대신
            # 실제 컬럼명인 "예측값"/"구분"이 그대로 툴팁에 표시됨
            st.bar_chart(
                chart_df, x="예측시점", y="예측값", color="구분",
                stack=False, width="stretch",
            )

            st.caption(
                "실제값(참고용)은 데이터에 이미 존재하는 과거 기록과 비교하기 위한 값이라, "
                "미래 시점을 조회하면 표시되지 않습니다."
            )

    st.markdown("---")
    st.subheader("전체 역 예측 하차인원 TOP 10")
    st.caption(f"기준: {month // 100}년 {month % 100:02d}월 {hour}시 (위에서 고른 기준 월/시간대와 동일)")

    rank_horizon = st.selectbox(
        "몇 시간 뒤 기준으로 순위를 볼까요?", HORIZONS, index=HORIZONS.index(3),
        format_func=lambda h: f"{h}시간 뒤", key="rank_horizon",
    )

    rank_pool = df[(df["사용월"] == month) & (df["시간대"] == hour)].dropna(subset=feature_cols)

    if rank_pool.empty:
        st.warning("이 월/시간대 조합에는 예측 가능한 역이 없어요.")
    else:
        X_all = rank_pool[feature_cols]
        pred_승차 = models[(rank_horizon, "승차인원")].predict(X_all)
        pred_하차 = models[(rank_horizon, "하차인원")].predict(X_all)

        table = rank_pool[["호선명", "지하철역"]].copy()
        table["예측 승차인원"] = pred_승차.round().astype(int)
        table["예측 하차인원"] = pred_하차.round().astype(int)
        table["순유입(하차-승차)"] = table["예측 하차인원"] - table["예측 승차인원"]

        top10_get_off = table.sort_values("예측 하차인원", ascending=False).head(10).reset_index(drop=True)
        top10_get_off.index = top10_get_off.index + 1
        st.dataframe(top10_get_off, width="stretch")
        st.bar_chart(top10_get_off.set_index("지하철역")["예측 하차인원"])

        st.markdown("#### 🔺 사람이 가장 몰리는 역 (순유입 TOP 10)")
        st.caption("순유입 = 예측 하차인원 - 예측 승차인원. 값이 클수록 그 시간대에 사람이 몰려드는 역이에요.")
        top10_in = table.sort_values("순유입(하차-승차)", ascending=False).head(10).reset_index(drop=True)
        top10_in.index = top10_in.index + 1
        st.dataframe(top10_in, width="stretch")
        st.bar_chart(top10_in.set_index("지하철역")["순유입(하차-승차)"])

        st.markdown("#### 🔻 사람이 가장 빠져나가는 역 (순유출 TOP 10)")
        st.caption("순유입이 가장 작은(음수 폭이 큰) 역이에요. 값이 작을수록 그 시간대에 사람이 빠져나가는 역입니다.")
        top10_out = table.sort_values("순유입(하차-승차)", ascending=True).head(10).reset_index(drop=True)
        top10_out.index = top10_out.index + 1
        st.dataframe(top10_out, width="stretch")
        st.bar_chart(top10_out.set_index("지하철역")["순유입(하차-승차)"])


if __name__ == "__main__":
    # `streamlit run pages/subway_app.py`로 단독 실행할 때만 여기서 바로 그려짐.
    # in_out_data.py가 import해서 render()를 호출할 때는 이 블록이 실행되지 않음.
    render()