#settings.py
"""
프로젝트 전역 설정값 모음.

경로 상수, 시간대 순서, 노선명 통일 매핑처럼 여러 파일(페이지)이 동일하게
참조해야 하는 값은 전부 여기서 정의하고, 각 파일은 여기서 import해서 씀.

이 파일은 순수 설정값(상수)만 담음. 데이터 로딩/학습 같은 로직 함수는
그 로직을 실제로 쓰는 모듈(예: pages/subway_model.py)에 남겨둠 —
설정 파일이 lightgbm/sklearn 같은 무거운 라이브러리에 의존하게 되는 걸 막아서,
경로 같은 값만 필요한 다른 페이지가 불필요한 패키지까지 끌어오지 않게 하기 위함.

폴더 구조 전제:
  project_folder/
    main.py
    settings.py               <- 이 파일 (프로젝트 루트)
    resource/                 <- CSV 원본과 학습된 pkl이 여기 있음
    pages/
      home.py
      in_out_data.py
      subway_model.py         <- 여기서 이 파일을 import해서 씀
      subway_app.py           <- 여기서도 이 파일을 import해서 씀
      (다른 페이지들도 필요하면 여기서 import)
"""

from pathlib import Path

# settings.py가 있는 폴더 = 프로젝트 루트라고 전제
BASE_DIR = Path(__file__).resolve().parent

# resource 폴더 설정
RESOURCE_DIR = BASE_DIR / "resource"

CSV_PATH = RESOURCE_DIR / "Subway_Line_Station_Boarding_Alighting_Information.csv"
PARQUET_PATH = RESOURCE_DIR / "Subway_Line_Station_Boarding_Alighting_Information.parquet"
MODEL_PATH = RESOURCE_DIR / "lgbm_multihorizon_models.pkl"
MODEL_PATH_XGB = RESOURCE_DIR / "xgb_multihorizon_models.pkl"
DATA_PATH = RESOURCE_DIR / "seoul_monthly_station_ridership_filled_nearest.csv"
COORD_PATH = RESOURCE_DIR / "coordinate.csv"  # 지도용: 행정동 중심 좌표(영역-행정동 데이터에서 변환)
METRO_PATH_SEOUL = RESOURCE_DIR / "seoul_metro_coordinates.csv"
BUSAN_DATA_PATH = RESOURCE_DIR / "busan_commercial.csv"  # 부산 TOP3용: 기준년월, 행정동, 인근지하철역명, 업종, 매출액(=소비매출 월별 일평균), 이용건수
BUSAN_COORD_PATH = RESOURCE_DIR / "busan_coordinate.csv"  # 부산 지도용: 행정동 중심 좌표(구 이름 포함)  ← 이 줄 추가

HORIZONS = [1, 3, 6]  # 몇 시간 앞을 예측할지
LAGS = [1, 2, 3]      # 직전 몇 시간대까지를 입력으로 쓸지
EARLY_STOPPING_ROUNDS = 30  # 두 모델 다 동일하게 적용하는 조기종료 기준
VALID_FROM_YYYYMM = 202512  # test_from(202602) 이전 구간에서 최근 N개월을 검증용으로 뗌

# LightGBM/XGBoost 성능 비교가 공정하려면 하이퍼파라미터를 최대한 맞춰야 함.
# num_leaves/max_leaves를 63으로 통일하고, XGBoost는 grow_policy='lossguide'로
# LightGBM과 같은 리프 중심(leaf-wise) 성장 방식을 쓰게 함(기본값인 depth-wise가 아님).
# enable_categorical=True로 XGBoost도 원-핫 인코딩 없이 범주형을 네이티브로 처리함.
LGBM_PARAMS = dict(
    n_estimators=500, learning_rate=0.05, num_leaves=63,
    random_state=42, n_jobs=-1, verbosity=-1,
)
XGB_PARAMS = dict(
    n_estimators=500, learning_rate=0.05, max_leaves=63,
    grow_policy="lossguide", tree_method="hist", enable_categorical=True,
    random_state=42, n_jobs=-1, verbosity=0,
)

# 지하철 운영일 순서(04-05시 시작 ~ 03-04시 종료)
HOUR_ORDER = ["04-05", "05-06", "06-07", "07-08", "08-09", "09-10", "10-11", "11-12",
              "12-13", "13-14", "14-15", "15-16", "16-17", "17-18", "18-19", "19-20",
              "20-21", "21-22", "22-23", "23-24", "00-01", "01-02", "02-03", "03-04"]

# 과거에 분리 표기되던 노선명을 지금 기준 통합 노선명으로 정리하는 매핑.
# 여기 키에 없는 노선명(3호선, 4호선 등 이미 통합된 이름)은 그대로 유지됨.
LINE_NAME_MAP = {
    "일산선": "3호선",
    "과천선": "4호선",
    "안산선": "4호선",
    "경부선": "1호선",
    "경원선": "1호선",
    "경인선": "1호선",
    "경의선": "경의중앙선",
    "중앙선": "경의중앙선",
    "수인선": "수인분당선",
    "분당선": "수인분당선",
}

# 정확한 문자열 매칭(LINE_NAME_MAP)이 아니라 패턴으로 잡아야 하는 노선명 규칙.
# (정규식, 치환할 이름) 튜플 리스트 — LINE_NAME_MAP 적용 후 순서대로 적용됨.
# 9호선은 개통 단계별로 "9호선2단계", "9호선 3단계" 등으로 표기가 갈리는데 전부 9호선으로 통일.
LINE_NAME_REGEX_MAP = [
    (r"^9호선.*단계$", "9호선"),
]

# 노선 공식 색상 세팅
SUBWAY_COLORS = {
    '1호선': '#0052A4', '2호선': '#00A84D', '3호선': '#EF7C1C', 
    '4호선': '#00A5DE', '5호선': '#996CAC', '6호선': '#CD7C2F', 
    '7호선': '#747F00', '8호선': '#E6186C', '9호선': '#BDB092',
    '수인분당선': '#FABE00', '신분당선': '#D4003B', 
    '경의중앙선': '#77C4A3', '공항철도 1호선': '#0090D2',
    '경강선': '#003DA5', '경부선': '#0052A4', '경원선': '#0052A4', 
    '경인선': '#0052A4', '경의선': '#77C4A3', '경춘선': '#0C8E72', 
    '과천선': '#00A5DE', '분당선': '#FABE00', '서해선': '#81A914', 
    '수인선': '#FABE00', '신림선': '#6789CA', '안산선': '#00A5DE', 
    '우이신설선': '#B0CE18', '일산선': '#EF7C1C', '장항선': '#0052A4', '중앙선': '#77C4A3'
}
# ── 화면에 표시되는 안내/출처 문구 ──

# 유동인구 데이터 분석
TRANSER_INFORMATION = ("환승역의 경우 통합된 인원수를 보여주며, 차트에 마우스를 올리면 호선별 상세 인원을 확인할 수 있습니다.")
SHOW_CIRCLE_AND_BAR = ("막대, 파이 차트로 보기")
SHOW_PYDECK = ("지도로 확인하기")

# 홈 화면 하단 전체 출처표시 (st.caption은 마크다운 링크 지원)
COPYRIGHT_FULL = (
    "본 대시보드는 서울특별시가 저작권을 보유하고 서울신용보증재단이 제공하는 공공누리 제1유형 저작물 "
    "'서울시 상권분석서비스(추정매출-행정동)'(2023년 공개), "
    "'서울시 상권분석서비스(점포-행정동)'(2023년 공개), "
    "'서울시 상권분석서비스(상주인구-행정동)'(2023년 공개), "
    "'서울시 상권분석서비스(영역-행정동)'(2023년 공개)과, "
    "서울특별시가 저작권을 보유하고 제공하는 "
    "'서울시 지하철 호선별 역별 시간대별 승하차 인원 정보'(2015년 공개), "
    "'서울시 역사마스터 정보'(2022년 공개)를 이용하였으며, "
    "해당 저작물은 [서울 열린데이터광장](https://data.seoul.go.kr)에서 다운받으실 수 있습니다. "
    "본 대시보드의 분석 결과는 원본 데이터를 가공·분석한 결과이며, "
    "서울특별시 및 서울신용보증재단의 공식 수치나 분석 결과가 아니고 두 기관이 후원하거나 보증하는 것도 아닙니다."
)

# 각 페이지 하단 짧은 출처표시
COPYRIGHT_SHORT = (
    "이 화면의 서울 데이터는 공공누리 제1유형으로 개방된 공공데이터"
    "(저작권자: 서울특별시, 제공기관: 서울신용보증재단·서울특별시)를 "
    "가공·분석한 결과입니다. "
    "데이터별 저작권자, 제공기관 및 출처는 홈 화면 하단에서 확인하실 수 있습니다."
)

# 지하철 승하차 인원 페이지(subway_app.py) 하단 출처표시
COPYRIGHT_SUBWAY = (
    "이 화면은 서울특별시가 저작권을 보유하고 제공하는 "
    "'서울시 지하철 호선별 역별 시간대별 승하차 인원 정보'(2015년 공개)를 이용하였으며, "
    "해당 저작물은 [서울 열린데이터광장](https://data.seoul.go.kr)에서 다운받으실 수 있습니다. "
    "예측값과 순위는 원본 데이터를 가공·분석한 결과이며, "
    "서울특별시의 공식 수치나 분석 결과가 아니고 서울특별시가 후원하거나 보증하는 것도 아닙니다."
)


# commercial_top3.py 안내 문구
TOP3_INTRO_CAPTION = (
    "한 지역에서 어떤 업종이 가장 강한지 상위 3개를 보여드립니다. 데이터는 분기 값을 3개월로 나눈 것이라, "
    "월 단위로 고르셔도 같은 분기 안에서는 순위가 거의 바뀌지 않습니다."
)
TOP3_REGION_CAPTION = (
    "막대 옆 숫자는 그 지역 전체 매출 중 해당 업종이 차지하는 비중입니다. "
    "특화도가 1보다 크면 서울 평균보다 이 지역에서 더 강한 업종입니다."
)
TOP3_PILLAR_CAPTION = (
    "기둥 색은 선택한 순위의 업종이고, 기둥 높이는 그 업종 매출의 제곱근에 비례합니다. "
    "매출이 매우 큰 몇몇 동 때문에 나머지가 너무 낮아 보이는 것을 막으려고 제곱근으로 변환했습니다. "
    "그래서 높이 차이는 실제 매출 차이보다 완만하게 보이며, 실제 금액은 기둥에 마우스를 올리면 나옵니다. "
    "마우스 오른쪽 버튼을 누른 채 끌면 지도를 돌려볼 수 있습니다."
)
TOP3_DOT_CAPTION = "점은 각 행정동의 중심 위치이며 행정구역 경계가 아닙니다. 색은 선택한 순위의 업종입니다."
TOP3_LEGEND_CAPTION = "범례의 괄호 안 숫자는 그 업종이 해당 순위인 지역의 수입니다. 점·기둥에 마우스를 올리면 1~3위가 표시됩니다."
MAP_ATTRIBUTION_CAPTION = "지도 배경: © OpenStreetMap contributors © CARTO"


# ── 부산 (commercial_top3.py의 '전체 지역 표 > 부산' 탭) ──
# 부산 표 아래 안내 문구
BUSAN_TABLE_CAPTION = (
    "부산은 업종 대분류 기준이고 수치는 소비매출의 월별 일평균(평균이용금액)이라 서울 매출과 직접 비교할 수 없습니다(서울은 업종 소분류·매출). "
    "특화도 기준은 서울은 서울 전체, 부산은 부산 전체와 비교해 계산됩니다. "
    "'근처역 없음'은 동 중심에서 가까운 지하철역이 없는 동입니다."
)
# 부산 데이터 출처 + 가공 사실 (st.caption은 마크다운 링크 지원)
BUSAN_SOURCE_CAPTION = (
    "부산 데이터 출처: "
    "[부산광역시 Big-데이터웨이브 · 일별 행정동 업종 소비매출 월별 일평균]"
    "(https://data.busan.go.kr/bdip/opendata/detail.do?publicdatapk=PD_CS00004&uuid=fda5cd5f-aab7-43eb-9c92-797b04dc28eb&type=510), "
    "[공공데이터포털 · 부산교통공사_도시철도역사정보](https://www.data.go.kr/data/15043686/fileData.do), "
    "[공공데이터포털 · 국가데이터처_SGIS행정구역 통계 및 경계](https://www.data.go.kr/data/15129688/fileData.do). "
    "부산 수치는 매출이 아니라 소비매출의 월별 일평균입니다. "
    "인근 지하철역은 부산교통공사 도시철도역사정보(기준일 2021-02-26)의 역 위치와 SGIS 행정동 경계의 중심점을 이용해 "
    "직선거리가 가장 가까운 역을 계산한 값이며 공식 제공 정보가 아닙니다. "
    "소비매출 원본의 업종명 오타와 일부 빈 행정동명은 보정했습니다."
)