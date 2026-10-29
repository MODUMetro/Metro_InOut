#settings.py
"""
프로젝트 전역 설정값 모음.

경로 상수, 시간대 순서, 노선명 통일 매핑처럼 여러 파일(페이지)이 동일하게
참조해야 하는 값은 전부 여기서 정의하고, 각 파일은 여기서 import해서 씀.

이 파일은 순수 설정값(상수)만 담음. 데이터 로딩/학습 같은 로직 함수는
그 로직을 실제로 쓰는 모듈에 남겨둠 —
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
      (다른 페이지들도 필요하면 여기서 import)
"""

from pathlib import Path

# settings.py가 있는 폴더 = 프로젝트 루트라고 전제
BASE_DIR = Path(__file__).resolve().parent

# resource 폴더 설정
RESOURCE_DIR = BASE_DIR / "resource"
SEOUL_DATA_FOLDER = "seoul"
BUSAN_DATA_FOLDER = "busan"

# 서울지역 데이터 파일 경로
CSV_PATH = RESOURCE_DIR / SEOUL_DATA_FOLDER / "Subway_Line_Station_Boarding_Alighting_Information.csv"
PARQUET_PATH = RESOURCE_DIR / SEOUL_DATA_FOLDER / "Subway_Line_Station_Boarding_Alighting_Information.parquet"
# 서울 상권 TOP3용: 기준년분기, 행정동, 행정동코드, 업종, 당월_매출_금액(=분기 추정매출),
#                   인근지하철1~5 / 승하차인원1~5 / 승하차개월수1~5 (행정동 대표점 반경 800m, GTX 제외)
DATA_PATH = RESOURCE_DIR / SEOUL_DATA_FOLDER / "seoul_monthly_station_ridership_filled_nearest.csv"
COORD_PATH = RESOURCE_DIR / SEOUL_DATA_FOLDER / "seoul_site_coordinate.csv"  # 지도용: 행정동 중심 좌표(영역-행정동 데이터에서 변환)
METRO_PATH_SEOUL = RESOURCE_DIR / SEOUL_DATA_FOLDER / "seoul_metro_coordinates.csv"  # 지하철역 위도, 경도 (출처: 서울시 역사마스터 정보)

# 부산지역 데이터 파일 경로
# 부산 TOP3용: 기준년월, 행정동코드, 행정동명(구 포함), 구, 업종대분류, 평균이용금액, 평균이용건수, 인근지하철역
BUSAN_DATA_PATH = RESOURCE_DIR / BUSAN_DATA_FOLDER / "busan_commercial.csv"
# 부산 지도용: 행정동 중심 좌표(구 이름 포함)
BUSAN_COORD_PATH = RESOURCE_DIR / BUSAN_DATA_FOLDER / "busan_coordinate.csv"  
# 부산 상하차 인원 반영된 파일 (출처: 부산교통공사 '일별 역별 시간대별 승하차', 부산광역시 Big-데이터웨이브)
BUSAN_METRO_BOARDING_DATA_PATH = RESOURCE_DIR / BUSAN_DATA_FOLDER / "busan_metro_Line_Station_Boarding_Alighting_Information.csv"
BUSAN_METRO_BOARDING_DATA_PARQUET_PATH = RESOURCE_DIR / BUSAN_DATA_FOLDER/ "busan_metro_Line_Station_Boarding_Alighting_Information.parquet"
# 부산 지하철역 위치 위도, 경도 반영된 파일 (출처: 부산교통공사 '도시철도역사정보')
BUSAN_METRO_POSITION = RESOURCE_DIR / BUSAN_DATA_FOLDER / "busan_metro_coordinates.csv"

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

# 서울/경기
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

# 부산
BUSAN_METRO_LINE_COLORS = { 
    '1호선': '#F06A00',
    '2호선': '#81BF48',
    '3호선': '#BB8C00',
    '4호선': '#2E67CE',
    '부산김해경전철': '#875CAC',
    '동해선': '#0054A6',
}

# ── 화면에 표시되는 안내/출처 문구 ──

# 유동인구 데이터 분석
TRANSER_INFORMATION = ("환승역의 경우 통합된 인원수를 보여주며, 차트에 마우스를 올리면 호선별 상세 인원을 확인할 수 있습니다.")
SHOW_CIRCLE_AND_BAR = ("막대, 파이 차트로 보기")
SHOW_PYDECK = ("지도로 확인하기")

# 홈 화면 하단 전체 출처표시 (st.caption은 마크다운 링크 지원)
COPYRIGHT_FULL = (
    "자료들은 서울특별시가 저작권을 보유하고 서울신용보증재단이 제공하는 공공누리 제1유형 저작물 "
    "'[서울시 상권분석서비스(추정매출-행정동)](https://data.seoul.go.kr/dataList/OA-22175/S/1/datasetView.do)'(2023년 공개), "
    "'[서울시 상권분석서비스(점포-행정동)](https://data.seoul.go.kr/dataList/OA-22172/S/1/datasetView.do)'(2023년 공개), "
    "'[서울시 상권분석서비스(영역-행정동)](https://data.seoul.go.kr/dataList/OA-22160/S/1/datasetView.do)'(2023년 공개)과, "
    "서울특별시가 저작권을 보유하고 제공하는 공공누리 제1유형 저작물 "
    "'[서울시 지하철 호선별 역별 시간대별 승하차 인원 정보](https://data.seoul.go.kr/dataList/OA-12252/S/1/datasetView.do)'(2015년 공개), "
    "'[서울시 역사마스터 정보](https://data.seoul.go.kr/dataList/OA-21232/S/1/datasetView.do)'(2022년 공개)를 이용하였으며, "
    "해당 저작물은 [서울 열린데이터광장](https://data.seoul.go.kr)에서 다운받으실 수 있습니다. "
    "또한 부산광역시가 제공하는 "
    "'[일별 행정동 업종(대) 소비매출 월별 일평균](https://data.busan.go.kr/bdip/opendata/detail.do?publicdatapk=PD_CS00004&uuid=fda5cd5f-aab7-43eb-9c92-797b04dc28eb&type=510)', "
    "국가데이터처가 제공하는 '[SGIS 행정구역 통계 및 경계](https://www.data.go.kr/data/15129688/fileData.do)', "
    "부산교통공사가 제공하는 '[도시철도역사정보](https://www.data.go.kr/data/15043686/fileData.do)', "
    "'[일별 역별 시간대별 승하차](https://data.busan.go.kr/bdip/opendata/detail.do?publicdatapk=3057229&uuid=30375f18-7d74-4f60-b1f8-3c2372ef5535)'를 이용하였습니다. "
    "본 대시보드의 분석 결과는 원본 데이터를 가공·분석한 결과이며, "
    "각 데이터 제공기관의 공식 수치나 분석 결과가 아니고 제공기관이 후원하거나 보증하는 것도 아닙니다."
)

# 각 페이지 하단 짧은 출처표시
COPYRIGHT_SHORT = (
    "이 화면의 서울 데이터는 공공누리 제1유형으로 개방된 공공데이터"
    "(저작권자: 서울특별시, 제공기관: 서울신용보증재단·서울특별시)를 "
    "가공·분석한 결과입니다. "
    "데이터별 저작권자, 제공기관 및 출처는 홈 화면 하단에서 확인하실 수 있습니다."
)

COPYRIGHT_SUBWAY = (
    "이 화면은 서울특별시가 저작권을 보유하고 제공하는 "
    "'서울시 지하철 호선별 역별 시간대별 승하차 인원 정보'(2015년 공개)를 이용하였으며, "
    "해당 저작물은 [서울 열린데이터광장](https://data.seoul.go.kr)에서 다운받으실 수 있습니다. "
    "예측값과 순위는 원본 데이터를 가공·분석한 결과이며, "
    "서울특별시의 공식 수치나 분석 결과가 아니고 서울특별시가 후원하거나 보증하는 것도 아닙니다."
)


# commercial_top3.py 안내 문구
TOP3_INTRO_CAPTION = (
    "한 지역에서 어떤 업종이 가장 강한지 상위 3개를 보여드립니다. "
    "서울은 분기 단위, 부산은 월 단위 자료라서 기간 선택이 따로 있습니다. "
    "서울 분기 추정매출은 3개월로 나누지 않고 선택한 분기 그대로 사용합니다."
)
TOP3_REGION_CAPTION = (
    "막대 옆 숫자는 그 지역 전체 추정매출 중 해당 업종이 차지하는 비중입니다. "
    "특화도가 1보다 크면 해당 업종의 추정매출 비중이 서울 전체의 동일 업종 비중보다 높습니다. "
    "비중과 특화도는 선택한 기간 조건을 충족한 행정동·업종 자료를 기준으로 계산합니다. 모든 분기 자료 조건으로 제외된 업종은 지역 및 서울 전체 비중 계산에서도 제외됩니다."
)
TOP3_REGION_CAPTION_BUSAN = (
    "막대 옆 숫자는 그 지역 전체 평균이용금액 중 해당 업종이 차지하는 비중입니다. "
    "특화도가 1보다 크면 해당 업종의 평균이용금액 비중이 부산 전체의 동일 업종 비중보다 높습니다. "
    "막대 길이는 자료가 있는 월별 일평균 값의 평균이며 업종별 관측 월수가 다를 수 있습니다. 월 총매출이 아니고, 서울 추정매출과 직접 비교할 수 없습니다."
)
TOP3_PILLAR_CAPTION = (
    "기둥 색은 선택한 순위의 업종이고, 기둥 높이는 그 업종 금액(서울 추정매출, 부산 평균이용금액)의 제곱근에 비례합니다. "
    "금액이 매우 큰 몇몇 동 때문에 나머지가 너무 낮아 보이는 것을 막으려고 제곱근으로 변환했습니다. "
    "그래서 높이 차이는 실제 금액 차이보다 완만하게 보이며, 실제 금액은 기둥에 마우스를 올리면 나옵니다. "
    "매출 정보가 없는 지역의 기둥 높이는 표시하지 않습니다(0원이라는 의미가 아님). "
    "마우스 오른쪽 버튼을 누른 채 끌면 지도를 돌려볼 수 있습니다."
)
TOP3_DOT_CAPTION = "점은 각 행정동의 중심 위치이며 행정구역 경계가 아닙니다. 색은 선택한 순위의 업종입니다."
TOP3_LEGEND_CAPTION = "범례의 괄호 안 숫자는 그 업종이 해당 순위인 지역의 수입니다. 점·기둥에 마우스를 올리면 1~3위가 표시됩니다."
# OpenFreeMap 공개 지도 스타일을 사용합니다. API 키가 필요하지 않습니다.
OPENFREEMAP_STYLE_URL = "https://tiles.openfreemap.org/styles/positron"
MAP_ATTRIBUTION_CAPTION = (
    "지도 배경: [OpenFreeMap](https://openfreemap.org/) · "
    "© [OpenMapTiles](https://openmaptiles.org/) · "
    "Data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright)"
)
# in_out_data.py 지도 배경(CARTO Dark Matter) 출처표시
CARTO_ATTRIBUTION_CAPTION = (
    "지도 배경: © [CARTO](https://carto.com/attributions) · "
    "Data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright)"
)


# commercial_top3.py 하단 서울 데이터 출처 (st.caption은 마크다운 지원)
TOP3_SEOUL_SOURCE_CAPTION = (
    "이 화면의 서울 데이터는 서울특별시가 저작권을 보유하고 서울신용보증재단이 제공하는 공공누리 제1유형 저작물 "
    "'[서울시 상권분석서비스(추정매출-행정동)](https://data.seoul.go.kr/dataList/OA-22175/S/1/datasetView.do)'(2023년 공개), "
    "'[서울시 상권분석서비스(점포-행정동)](https://data.seoul.go.kr/dataList/OA-22172/S/1/datasetView.do)'(2023년 공개), "
    "'[서울시 상권분석서비스(영역-행정동)](https://data.seoul.go.kr/dataList/OA-22160/S/1/datasetView.do)'(2023년 공개)과, "
    "서울특별시가 저작권을 보유하고 제공하는 공공누리 제1유형 저작물 "
    "'[서울시 지하철 호선별 역별 시간대별 승하차 인원 정보](https://data.seoul.go.kr/dataList/OA-12252/S/1/datasetView.do)'(2015년 공개), "
    "'[서울시 역사마스터 정보](https://data.seoul.go.kr/dataList/OA-21232/S/1/datasetView.do)'(2022년 공개)를 이용하였으며, "
    "해당 저작물은 [서울 열린데이터광장](https://data.seoul.go.kr)에서 다운받으실 수 있습니다. "
    "분석 결과는 원본 데이터를 가공·분석한 결과이며, "
    "서울특별시 및 서울신용보증재단의 공식 수치나 분석 결과가 아니고 두 기관이 후원하거나 보증하는 것도 아닙니다."
)


# ── 부산 (commercial_top3.py의 '전체 지역 표 > 부산' 탭) ──
# 부산 표 아래 안내 문구
BUSAN_TABLE_CAPTION = (
    "부산은 업종 대분류 기준이고 수치는 소비매출의 월별 일평균(평균이용금액)이라 서울 추정매출과 직접 비교할 수 없습니다(서울은 업종 소분류·추정매출). "
    "여러 달을 고르면 월별 값을 더하지 않고 평균을 사용합니다. "
    "특화도 기준은 서울은 서울 전체, 부산은 부산 전체와 비교해 계산됩니다. "
    "'인근역 없음'은 동 중심에서 직선거리 800m 안에 매칭 대상 부산교통공사 역이 없다는 뜻입니다."
)
# 부산 데이터 출처 + 가공 사실 (st.caption은 마크다운 링크 지원)
BUSAN_SOURCE_CAPTION = (
    "이 화면의 부산 데이터는 부산광역시가 제공하는 "
    "'[일별 행정동 업종(대) 소비매출 월별 일평균](https://data.busan.go.kr/bdip/opendata/detail.do?publicdatapk=PD_CS00004&uuid=fda5cd5f-aab7-43eb-9c92-797b04dc28eb&type=510)', "
    "국가데이터처가 제공하는 '[SGIS 행정구역 통계 및 경계](https://www.data.go.kr/data/15129688/fileData.do)', "
    "부산교통공사가 제공하는 '[도시철도역사정보](https://www.data.go.kr/data/15043686/fileData.do)'(기준일 2021-02-26)를 이용하였으며, "
    "해당 자료는 공공데이터포털과 부산광역시 Big-데이터웨이브에서 확인하실 수 있습니다. "
    "부산 수치는 월 총매출이 아니라 소비매출의 월별 일평균입니다. "
    "인근 지하철역은 행정동 경계의 대표 좌표와 역 위치 사이의 직선거리(800m)로 계산한 값이며 공식 제공 정보가 아닙니다. "
    "소비매출 원본의 업종명 오타는 분석용 업종명에서 수정했으며, 행정동명이 비어 있는 행은 분석에서 제외했습니다. "
    "분석 결과는 원본 데이터를 가공·분석한 결과이며, 각 데이터 제공기관의 공식 수치나 분석 결과가 아니고 "
    "제공기관이 후원하거나 보증하는 것도 아닙니다."
)


# ── 데이터 이용 시 참고사항 (commercial_top3.py 첫 번째 탭) ──
# 구조: (소제목, [문장, ...]). 문장이 1개뿐인 항목은 목록 기호 없이 문단으로 표시됨.
DATA_NOTICE_TITLE = "데이터 이용 시 참고사항"
DATA_NOTICE_INTRO = (
    "본 프로젝트는 서울시와 부산시에서 제공하는 공공데이터를 가공하여 지역별 상권 정보를 제공합니다. "
    "데이터의 산정 기준과 제공 범위에 따라 실제 상권 현황과 차이가 있을 수 있으니 다음 사항을 참고해 주세요."
)
DATA_NOTICE_SECTIONS = [
    ("1. 서울·부산 매출 데이터의 차이", [
        "서울: 업종 소분류별 분기 단위 추정매출 데이터를 사용합니다. 실제 사업자의 확정 매출액을 의미하지 않습니다.",
        "부산: 업종 대분류별 월별 일평균 소비매출 데이터를 사용합니다. 월 총매출액이나 개별 점포의 매출액을 의미하지 않습니다.",
        "두 지역은 매출 산정 방식, 업종 분류 및 집계 기간이 다르므로 매출 금액을 직접 비교할 수 없습니다.",
    ]),
    ("2. 매출 데이터의 결측값", [
        "일부 지역·업종은 매출 자료가 제공되지 않을 수 있습니다.",
        "'정보 없음'은 매출이 0원이라는 의미가 아닙니다.",
        "매출 평균과 합계 등 통계는 데이터가 존재하는 항목을 기준으로 산정됩니다.",
        "서울에서 여러 분기를 선택하면 기본적으로 모든 분기에 매출 자료가 있는 업종만 비교합니다.",
    ]),
    ("3. 인근 지하철역의 선정 기준", [
        "인근 지하철역은 행정동 대표 좌표에서 직선거리 반경 800m 이내의 역을 기준으로 연결했습니다.",
        "실제 도보거리 및 이동시간과는 차이가 있을 수 있습니다.",
        "'인근역 없음'은 지정된 거리 안에 매칭 대상 역이 없다는 뜻이며, 주변에 대중교통이 없다는 의미는 아닙니다.",
    ]),
    ("4. 지역별 지하철 데이터의 차이", [
        "서울: 반경 800m 이내의 서로 다른 인근역을 최대 5개까지 표시하며, GTX 역은 매칭 대상에서 제외했습니다.",
        "서울 지하철 승하차 인원: 월별 승차·하차 인원을 3개월 단위로 합산한 수치입니다. 해당 행정동의 전체 유동인구나 실제 방문객 수를 의미하지 않습니다.",
        "부산: 부산교통공사 1~4호선 역사정보를 기준으로 가장 가까운 역을 연결했습니다. 부산김해경전철과 동해선 등 다른 운영기관의 역은 포함되지 않습니다.",
        "부산 자료에는 지하철 승하차 인원이 포함되어 있지 않습니다.",
    ]),
    ("5. 데이터의 기간 및 누락", [
        "서울은 분기별, 부산은 월별 자료를 사용하며, 현재 자료의 사용 가능 기간은 상권 분석 화면 상단의 기간 선택에서 확인하실 수 있습니다.",
        "서울 지하철 승하차 자료는 일부 역에서 3개월 전체의 자료가 존재하지 않을 수 있습니다. 이 경우 실제 집계된 월의 수를 함께 확인해야 합니다.",
        "부산 역사 위치 정보는 2021년 기준이므로 이후 신설되거나 변경된 역이 반영되지 않았을 수 있습니다.",
        "부산 자료는 행정동명이 누락된 일부 원본 행을 제외하고 구성했습니다.",
    ]),
    ("6. 분석 결과의 활용", [
        "매출액이나 지하철 이용 규모가 높다는 사실만으로 해당 지역의 창업 수익성 또는 성공 가능성이 높다고 판단할 수 없습니다.",
        "본 프로젝트의 자료는 지역별 상권 특성을 비교하기 위한 참고 정보이며, 실제 창업 의사결정에는 임대료, 초기 투자비용, 경쟁 환경 등을 추가로 고려해야 합니다.",
    ]),
]
