#subway_model_xgb.py
"""
XGBoost 버전 지하철 승하차 인원 예측 모델
- subway_model.py(LightGBM 버전)와 성능/속도를 비교하기 위해 만든 파일.

데이터 로딩/피처 생성 로직(load_and_reshape, build_multihorizon_features, get_feature_cols)은
subway_model.py 것을 그대로 import해서 씀 — 절대 여기서 다시 정의하지 않음.
두 모델이 "완전히 동일한 데이터/피처"로 학습돼야만 공정한 비교가 되기 때문.

하이퍼파라미터(XGB_PARAMS)와 조기종료 기준(EARLY_STOPPING_ROUNDS)은 settings.py에서
LightGBM 쪽과 나란히 정의해뒀고, 최대한 동등하게 맞춰져 있음(리프 개수 63개로 통일,
XGBoost도 grow_policy='lossguide'로 LightGBM과 같은 리프 중심 성장 방식 사용,
enable_categorical=True로 원-핫 인코딩 없이 범주형 네이티브 처리).

폴더 구조 전제:
  project_folder/
    main.py
    settings.py               <- 공유 설정값 (경로, XGB_PARAMS 등)
    resource/                 <- CSV 원본과 학습된 pkl들이 여기 있음
    pages/
      subway_model.py         <- 데이터 로딩/피처 생성 + LightGBM 학습
      subway_model_xgb.py     <- 이 파일. 위 로딩 함수 재사용 + XGBoost 학습
      subway_app.py
      model_comparison_app.py <- 이 파일의 결과를 subway_model.py 결과와 비교해서 보여줌
"""

import sys
import time
import pickle
from pathlib import Path

import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# subway_model.py(같은 pages 폴더)와 settings.py(프로젝트 루트) 둘 다 찾도록 경로 추가
_THIS_DIR = Path(__file__).resolve().parent
sys.path.append(str(_THIS_DIR))
sys.path.append(str(_THIS_DIR.parent))

from settings import CSV_PATH, MODEL_PATH_XGB, HORIZONS, XGB_PARAMS, EARLY_STOPPING_ROUNDS
from subway_model import load_and_reshape, build_multihorizon_features, get_feature_cols


# ---------------------------------------------------------------------------
# 호라이즌별(1/3/6시간) x 타겟별(승차/하차) XGBoost 모델 학습 및 평가
# (subway_model.py의 train_all_horizons()와 구조를 동일하게 맞춤 - 비교하기 쉽게)
# ---------------------------------------------------------------------------
def train_all_horizons_xgb(df, test_from_yyyymm: int = 202602):
    feature_cols = get_feature_cols()
    models, results = {}, {}

    for h in HORIZONS:
        for base_target in ['승차인원', '하차인원']:
            target_col = f'target_h{h}_{base_target[0]}차'
            needed = feature_cols + [target_col]
            d = df.dropna(subset=needed)

            test_mask = d['사용월'] >= test_from_yyyymm
            train_df, test_df = d[~test_mask], d[test_mask]

            model = xgb.XGBRegressor(
                **XGB_PARAMS,
                early_stopping_rounds=EARLY_STOPPING_ROUNDS,
                eval_metric="mae",
            )
            t0 = time.perf_counter()
            model.fit(
                train_df[feature_cols], train_df[target_col],
                eval_set=[(test_df[feature_cols], test_df[target_col])],
                verbose=False,
            )
            elapsed = time.perf_counter() - t0
            pred = model.predict(test_df[feature_cols])
            y_true = test_df[target_col]
            key = (h, base_target)
            results[key] = dict(
                mae=mean_absolute_error(y_true, pred),
                rmse=np.sqrt(mean_squared_error(y_true, pred)),
                r2=r2_score(y_true, pred),
                time=elapsed,
            )
            models[key] = model
            print(f"[XGBoost {h}시간 뒤 / {base_target}] "
                  f"MAE={results[key]['mae']:.1f}  "
                  f"RMSE={results[key]['rmse']:.1f}  "
                  f"R2={results[key]['r2']:.4f}  "
                  f"시간={elapsed:.1f}s")

    return models, results, feature_cols


def train_and_save_xgb(csv_path: Path = CSV_PATH, model_path: Path = MODEL_PATH_XGB):
    """csv_path로 처음부터 새로 학습해서 model_path에 저장. 이미 파일이 있어도 덮어씀"""
    wide = load_and_reshape(csv_path)
    train_df = build_multihorizon_features(wide)
    models, results, feature_cols = train_all_horizons_xgb(train_df)

    model_path.parent.mkdir(parents=True, exist_ok=True)
    with open(model_path, "wb") as f:
        pickle.dump({"models": models, "results": results,
                     "feature_cols": feature_cols}, f)
    return models, results, feature_cols


def load_or_train_models_xgb(csv_path: Path = CSV_PATH, model_path: Path = MODEL_PATH_XGB):
    """
    model_path에 학습된 pkl이 있으면 그대로 불러오고,
    없으면 train_and_save_xgb()로 새로 학습해서 저장한 뒤 불러옴.
    """
    if not model_path.exists():
        train_and_save_xgb(csv_path, model_path)

    with open(model_path, "rb") as f:
        obj = pickle.load(f)
    return obj["models"], obj["results"], obj["feature_cols"]


if __name__ == "__main__":
    # 스크립트로 직접 실행하면(streamlit 없이) 항상 새로 학습해서 저장함
    train_and_save_xgb()
    print(f"XGBoost 모델 저장 완료: {MODEL_PATH_XGB}")