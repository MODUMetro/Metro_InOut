#subway_model.py
"""
서울시 지하철 승하차 인원 예측 모델 (통합본)
- 1시간/3시간/6시간 뒤를 각각 직접(direct) 예측하는 LightGBM 모델들을 한 번에 학습
- subway_lgbm_next_hour.py + subway_lgbm_multihorizon.py 를 합친 파일

경로 상수(PARQUET_PATH, MODEL_PATH), 시간대 순서(HOUR_ORDER), 노선명 통일 매핑(LINE_NAME_MAP)은
전부 프로젝트 루트의 settings.py에서 정의하고, 이 파일은 거기서 import해서만 씀 (중복 정의 금지).

폴더 구조 전제:
  project_folder/
    main.py
    settings.py               <- 공유 설정값 (경로, HOUR_ORDER, LINE_NAME_MAP 등)
    resource/                 <- CSV 원본과 학습된 pkl이 여기 있음
    pages/
      subway_model.py         <- 이 파일 (pages 폴더 안)
      subway_app.py           <- 이 파일의 함수를 import해서 씀
"""

import sys
import time
import pickle
from pathlib import Path

import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# 프로젝트 루트(pages/의 부모 폴더)에 있는 settings.py를 확실히 찾도록 경로 추가
sys.path.append(str(Path(__file__).resolve().parent.parent))

from settings import (PARQUET_PATH, MODEL_PATH, HORIZONS, LAGS, HOUR_ORDER,
                       LINE_NAME_MAP, LINE_NAME_REGEX_MAP,
                       LGBM_PARAMS, EARLY_STOPPING_ROUNDS)


# ---------------------------------------------------------------------------
# 1) 원본 CSV(Wide) -> 역/월/시간대 단위 Long 포맷으로 변환
# ---------------------------------------------------------------------------
def load_and_reshape(path: Path = PARQUET_PATH) -> pd.DataFrame:
    """Wide format(시간대x승하차가 컬럼) -> Long format(호선/역/월/시간대 단위) 변환"""    
    df = pd.read_parquet(path)
    # 노선명 통일: 정확히 일치하는 것(LINE_NAME_MAP) 먼저, 패턴으로 잡아야 하는 것(LINE_NAME_REGEX_MAP) 그다음.
    # 카테고리로 굳히기 전에 문자열 상태에서 전부 적용함.
    df["호선명"] = df["호선명"].replace(LINE_NAME_MAP)
    for pattern, replacement in LINE_NAME_REGEX_MAP:
        df["호선명"] = df["호선명"].str.replace(pattern, replacement, regex=True)
    df["호선명"] = df["호선명"].astype("category")
    df["지하철역"] = df["지하철역"].astype("category")



    id_vars = ["사용월", "호선명", "지하철역"]
    value_vars = [c for c in df.columns if c not in id_vars + ["작업일자"]]

    # "04시-05시 승차인원" 같은 컬럼들을 하나의 변수(colname)로 melt
    long_df = df.melt(id_vars=id_vars, value_vars=value_vars,
                       var_name="colname", value_name="인원")

    # 컬럼명 안의 "시간대"와 "승차/하차" 두 변수를 정규식으로 분리
    extracted = long_df["colname"].str.extract(r"(\d{2})시-(\d{2})시 (승차|하차)인원")
    long_df["시간대"] = extracted[0] + "-" + extracted[1]
    long_df["유형"] = extracted[2]
    long_df = long_df.drop(columns="colname")

    # 승차/하차를 다시 별도 컬럼으로 pivot
    wide = long_df.pivot_table(
        index=["사용월", "호선명", "지하철역", "시간대"],
        columns="유형", values="인원", aggfunc="first"
    ).reset_index()
    wide.columns.name = None
    wide = wide.rename(columns={"승차": "승차인원", "하차": "하차인원"})

    # HOUR_ORDER를 그대로 사용 (로컬 리스트 재정의하지 않음)
    hour_idx = {h: i for i, h in enumerate(HOUR_ORDER)}
    wide["시간대_순서"] = wide["시간대"].map(hour_idx)
    return wide.sort_values(["호선명", "지하철역", "사용월", "시간대_순서"])


# ---------------------------------------------------------------------------
# 2) 다중 호라이즌(1/3/6시간 뒤) 학습용 lag / target 피처 생성
# ---------------------------------------------------------------------------
def build_multihorizon_features(wide: pd.DataFrame) -> pd.DataFrame:
    wide = wide.sort_values(['호선명', '지하철역', '사용월', '시간대_순서']).copy()
    grp = wide.groupby(['호선명', '지하철역', '사용월'], observed=True)

    for lag in LAGS:
        wide[f'lag{lag}_승차'] = grp['승차인원'].shift(lag)
        wide[f'lag{lag}_하차'] = grp['하차인원'].shift(lag)

    for h in HORIZONS:
        wide[f'target_h{h}_승차'] = grp['승차인원'].shift(-h)
        wide[f'target_h{h}_하차'] = grp['하차인원'].shift(-h)

    wide['년'] = (wide['사용월'] // 100).astype(int)
    wide['월'] = (wide['사용월'] % 100).astype(int)
    return wide


def get_feature_cols():
    cols = ['시간대_순서', '월', '년', '호선명', '지하철역']
    for lag in LAGS:
        cols += [f'lag{lag}_승차', f'lag{lag}_하차']
    return cols


# ---------------------------------------------------------------------------
# 3) 호라이즌별(1/3/6시간) x 타겟별(승차/하차) 모델 학습 및 평가
# ---------------------------------------------------------------------------
def train_all_horizons(df: pd.DataFrame, test_from_yyyymm: int = 202602):
    feature_cols = get_feature_cols()
    cat_cols = ['호선명', '지하철역']
    models, results = {}, {}

    for h in HORIZONS:
        for base_target in ['승차인원', '하차인원']:
            target_col = f'target_h{h}_{base_target[0]}차'  # target_h3_승차, target_h3_하차 형태
            needed = feature_cols + [target_col]
            d = df.dropna(subset=needed)

            test_mask = d['사용월'] >= test_from_yyyymm
            train_df, test_df = d[~test_mask], d[test_mask]

            model = lgb.LGBMRegressor(**LGBM_PARAMS)
            t0 = time.perf_counter()
            model.fit(
                train_df[feature_cols], train_df[target_col],
                categorical_feature=cat_cols,
                eval_set=[(test_df[feature_cols], test_df[target_col])],
                callbacks=[lgb.early_stopping(EARLY_STOPPING_ROUNDS, verbose=False)],
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
            print(f"[{h}시간 뒤 / {base_target}] "
                  f"MAE={results[key]['mae']:.1f}  "
                  f"RMSE={results[key]['rmse']:.1f}  "
                  f"R2={results[key]['r2']:.4f}  "
                  f"시간={elapsed:.1f}s")

    return models, results, feature_cols


# ---------------------------------------------------------------------------
# 4) 학습 + 저장 / 로드 (subway_app.py의 load_models()와 아래 __main__이 공유하는 부분)
# ---------------------------------------------------------------------------
def train_and_save(file_path: Path = PARQUET_PATH, model_path: Path = MODEL_PATH):
    """처음부터 새로 학습해서 model_path에 저장. 이미 파일이 있어도 덮어씀"""
    wide = load_and_reshape(file_path)
    train_df = build_multihorizon_features(wide)
    models, results, feature_cols = train_all_horizons(train_df)

    model_path.parent.mkdir(parents=True, exist_ok=True)
    with open(model_path, "wb") as f:
        pickle.dump({"models": models, "results": results,
                     "feature_cols": feature_cols}, f)
    return models, results, feature_cols


def load_or_train_models(file_path: Path = PARQUET_PATH, model_path: Path = MODEL_PATH):
    """
    model_path에 학습된 pkl이 있으면 그대로 불러오고,
    없으면 train_and_save()로 새로 학습해서 저장한 뒤 불러옴.
    subway_app.py의 load_models()가 이 함수 하나만 호출하면 됨.
    """
    if not model_path.exists():
        train_and_save(file_path, model_path)

    with open(model_path, "rb") as f:
        obj = pickle.load(f)
    return obj["models"], obj["results"], obj["feature_cols"]


if __name__ == "__main__":
    # 스크립트로 직접 실행하면(streamlit 없이) 항상 새로 학습해서 저장함
    train_and_save()
    print(f"모델 저장 완료: {MODEL_PATH}")