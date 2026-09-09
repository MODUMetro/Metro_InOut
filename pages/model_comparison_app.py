#model_comparison_app.py
"""
LightGBM vs XGBoost 성능 비교 대시보드
(멀티페이지 앱에서 다른 페이지가 render()를 불러다 쓰는 구조 - subway_app.py와 동일 패턴)

두 모델을 동일한 데이터/피처/train-test 분할/최대한 동등한 하이퍼파라미터로 학습시킨 뒤,
호라이즌(1/3/6시간 뒤) x 타겟(승차/하차)별로 MAE, RMSE, R², 학습시간을 나란히 비교해서 보여줌.

폴더 구조 전제:
  project_folder/
    main.py
    settings.py               <- 공유 설정값 (경로, HORIZONS 등)
    resource/                 <- CSV 원본과 학습된 pkl들이 여기 있음
    pages/
      subway_model.py         <- LightGBM 학습 로직
      subway_model_xgb.py     <- XGBoost 학습 로직
      data_guards.py          <- CSV 존재 체크 등 공용 UI 가드
      model_comparison_app.py <- 이 파일

단독 테스트 실행: streamlit run pages/model_comparison_app.py
(두 모델 pkl이 모두 없으면 최초 실행 시 둘 다 학습하느라 몇 분 정도 걸릴 수 있음)
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

_THIS_DIR = Path(__file__).resolve().parent
sys.path.append(str(_THIS_DIR))
sys.path.append(str(_THIS_DIR.parent))

from settings import CSV_PATH, MODEL_PATH, MODEL_PATH_XGB, HORIZONS
from subway_model import load_or_train_models
from subway_model_xgb import load_or_train_models_xgb
from data_guards import ensure_csv_exists

# NOTE: st.set_page_config()는 main.py에서 이미 호출했으므로 여기서는 다시 호출하지 않음


@st.cache_resource
def load_comparison_results():
    """
    두 모델(LightGBM/XGBoost) 모두 pkl이 있으면 그대로 로드하고,
    없는 쪽만 새로 학습함. 둘 다 없으면 순서대로 둘 다 학습하느라
    시간이 걸릴 수 있어서 각각 스피너로 진행 상황을 알려줌.
    """
    ensure_csv_exists()

    if not MODEL_PATH.exists():
        with st.spinner("LightGBM 모델이 없어서 새로 학습하는 중이에요 (몇 분 걸릴 수 있어요)..."):
            _, lgbm_results, _ = load_or_train_models(CSV_PATH, MODEL_PATH)
    else:
        _, lgbm_results, _ = load_or_train_models(CSV_PATH, MODEL_PATH)

    if not MODEL_PATH_XGB.exists():
        with st.spinner("XGBoost 모델이 없어서 새로 학습하는 중이에요 (몇 분 걸릴 수 있어요)..."):
            _, xgb_results, _ = load_or_train_models_xgb(CSV_PATH, MODEL_PATH_XGB)
    else:
        _, xgb_results, _ = load_or_train_models_xgb(CSV_PATH, MODEL_PATH_XGB)

    return lgbm_results, xgb_results


def _results_to_df(results: dict, model_name: str) -> pd.DataFrame:
    """{(호라이즌, 타겟): {mae, rmse, r2, time}} 딕셔너리를 표(DataFrame)로 변환"""
    rows = []
    for (h, target), metrics in results.items():
        rows.append({
            "모델": model_name,
            "예측시점": f"{h}시간 뒤",
            "구분": target,
            "조합": f"{h}시간 뒤 / {target}",
            "MAE": round(metrics["mae"], 1),
            "RMSE": round(metrics["rmse"], 1),
            "R2": round(metrics["r2"], 4),
            "학습시간(초)": round(metrics.get("time", 0), 1),
        })
    return pd.DataFrame(rows)


def render():
    """다른 페이지 파일에서 이 함수를 불러다 호출하면 비교 대시보드가 그려짐"""
    st.title("⚖️ LightGBM vs XGBoost 성능 비교")
    st.caption(
        "같은 피처, 같은 train/test 분할(사용월 202602 기준), 최대한 동등한 하이퍼파라미터"
        "(리프 개수 63개, 조기종료 30라운드, 범주형 네이티브 처리)로 두 모델을 학습시켜 비교합니다."
    )

    lgbm_results, xgb_results = load_comparison_results()

    df = pd.concat([
        _results_to_df(lgbm_results, "LightGBM"),
        _results_to_df(xgb_results, "XGBoost"),
    ], ignore_index=True)

    # 호라이즌 순서를 HORIZONS 기준으로 고정 (1,3,6 순서 보장)
    combo_order = [f"{h}시간 뒤 / {t}" for h in HORIZONS for t in ["승차인원", "하차인원"]]
    df["조합"] = pd.Categorical(df["조합"], categories=combo_order, ordered=True)
    df = df.sort_values(["조합", "모델"])

    st.subheader("전체 비교표")
    st.dataframe(
        df[["모델", "예측시점", "구분", "MAE", "RMSE", "R2", "학습시간(초)"]],
        width="stretch", hide_index=True,
    )

    st.markdown("---")
    st.subheader("지표별 모델 비교 (LightGBM vs XGBoost 나란히)")
    st.caption("각 조합(호라이즌/승하차)마다 LightGBM·XGBoost 막대가 옆으로 나란히 놓여서 바로 비교할 수 있어요.")

    # 학습시간이 가장 중요한 지표라 맨 위에 가장 크게 단독 배치
    st.markdown("**학습시간 비교 (초, 낮을수록 빠름)**")
    time_pivot = df.pivot(index="조합", columns="모델", values="학습시간(초)").reindex(combo_order)
    # stack=False: LightGBM/XGBoost 막대가 쌓이지 않고 옆으로 나란히
    st.bar_chart(time_pivot, stack=False, width="stretch", height=440)

    # 나머지 지표(MAE, RMSE, R2)는 그 아래에 3칸으로 나란히, 좀 더 작게
    metric_specs = [
        ("MAE", "MAE 비교 (낮을수록 정확)"),
        ("RMSE", "RMSE 비교 (낮을수록 정확)"),
        ("R2", "R² 비교 (높을수록 정확)"),
    ]

    cols = st.columns(3)
    for slot, (metric_col, title) in zip(cols, metric_specs):
        with slot:
            st.markdown(f"**{title}**")
            pivot = df.pivot(index="조합", columns="모델", values=metric_col).reindex(combo_order)
            st.bar_chart(pivot, stack=False, width="stretch", height=280)

    st.markdown("---")
    st.subheader("모델별 평균 요약 (6개 조합 평균)")
    summary = df.groupby("모델")[["MAE", "RMSE", "학습시간(초)"]].mean().round(2)
    st.dataframe(summary, width="stretch")

    st.caption(
        "위 비교는 하이퍼파라미터를 깊게 튜닝하지 않고 동등한 조건 하나로 학습한 결과입니다. "
        "각 모델을 더 세밀하게 튜닝하면 결과가 달라질 수 있습니다."
    )


if __name__ == "__main__":
    render()