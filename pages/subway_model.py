#subway_model.py
"""
서울시 지하철 승하차 인원 예측 모델 (통합본)
- 1시간/3시간/6시간 뒤를 각각 직접(direct) 예측하는 LightGBM 모델들을 한 번에 학습
- subway_lgbm_next_hour.py + subway_lgbm_multihorizon.py 를 합친 파일

폴더 구조 전제:
  project_folder/
    main.py
    resource/                 <- CSV 원본과 학습된 pkl이 여기 있음
    pages/
      subway_model.py         <- 이 파일 (pages 폴더 안)
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
import pickle
from pathlib import Path
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# 이 파일(pages/subway_model.py) 기준으로 프로젝트 루트의 resource 폴더를 가리킴
BASE_DIR = Path(__file__).resolve().parent        # .../project_folder/pages
RESOURCE_DIR = BASE_DIR.parent / "resource"        # .../project_folder/resource

SRC_CSV = RESOURCE_DIR / "Subway_Line_Station_Boarding_Alighting_Information.csv"
MODEL_OUT = RESOURCE_DIR / "lgbm_multihorizon_models.pkl"

HORIZONS = [1, 3, 6]  # 몇 시간 앞을 예측할지
LAGS = [1, 2, 3]      # 직전 몇 시간대까지를 입력으로 쓸지


# ---------------------------------------------------------------------------
# 1) 원본 CSV(Wide) -> 역/월/시간대 단위 Long 포맷으로 변환
# ---------------------------------------------------------------------------
def load_and_reshape(path: str) -> pd.DataFrame:
    """Wide format(시간대x승하차가 컬럼) -> Long format(호선/역/월/시간대 단위) 변환"""
    df = pd.read_csv(path, encoding="cp949")
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

    # 지하철 운영일 순서(04-05시 시작 ~ 03-04시 종료)로 정렬
    hour_order = ["04-05","05-06","06-07","07-08","08-09","09-10","10-11","11-12",
                  "12-13","13-14","14-15","15-16","16-17","17-18","18-19","19-20",
                  "20-21","21-22","22-23","23-24","00-01","01-02","02-03","03-04"]
    hour_idx = {h: i for i, h in enumerate(hour_order)}
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

            model = lgb.LGBMRegressor(
                n_estimators=500, learning_rate=0.05, num_leaves=63,
                random_state=42, n_jobs=-1, verbosity=-1,
            )
            model.fit(
                train_df[feature_cols], train_df[target_col],
                categorical_feature=cat_cols,
                eval_set=[(test_df[feature_cols], test_df[target_col])],
                callbacks=[lgb.early_stopping(30, verbose=False)],
            )
            pred = model.predict(test_df[feature_cols])
            y_true = test_df[target_col]
            key = (h, base_target)
            results[key] = dict(
                mae=mean_absolute_error(y_true, pred),
                rmse=np.sqrt(mean_squared_error(y_true, pred)),
                r2=r2_score(y_true, pred),
            )
            models[key] = model
            print(f"[{h}시간 뒤 / {base_target}] "
                  f"MAE={results[key]['mae']:.1f}  "
                  f"RMSE={results[key]['rmse']:.1f}  "
                  f"R2={results[key]['r2']:.4f}")

    return models, results, feature_cols


if __name__ == "__main__":
    wide = load_and_reshape(SRC_CSV)
    df = build_multihorizon_features(wide)
    models, results, feature_cols = train_all_horizons(df)

    with open(MODEL_OUT, "wb") as f:
        pickle.dump({"models": models, "results": results,
                     "feature_cols": feature_cols}, f)
    print(f"모델 저장 완료: {MODEL_OUT}")