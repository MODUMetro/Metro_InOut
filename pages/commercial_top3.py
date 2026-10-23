"""가장 지갑을 많이 여는 지하철역은? - 지역(행정동)별 TOP3 업종 시각화 (통합 대시보드의 pages/ 용)
단독 실행: streamlit run pages/commercial_top3.py
- 첫 번째 탭은 '데이터 이용 시 참고사항' (문구는 settings.py의 DATA_NOTICE_*)
- 탭(지역 하나 보기)과 탭(전체 지역 표)은 안에 [서울 | 부산] 하위 탭이 있음
  (부산: busan_commercial.csv 필요, 없으면 부산 탭에 안내만 표시)
- 전체 지역 지도는 서울·부산 데이터를 동시에 표시하며 버튼은 지도 중심만 이동함
  (부산: busan_commercial.csv + busan_coordinate.csv 필요)
- 전체 지역 지도 안의 [구별 보기]에서 구(군)를 고르면 그 구의 행정동만 지도에 표시하고 지도 중심도 그 구로 이동함
  (서울·부산 따로 선택. 서울 구는 행정동코드 앞 5자리, 부산 구는 행정동명 맨 앞 단어로 판별)
데이터 처리 원칙 (검수 보고서 기준)
- 서울은 분기, 부산은 월 단위라서 기간 선택을 따로 둠. 서울 분기 매출은 3으로 나누지 않음.
- 매출 결측(NaN)은 0으로 바꾸지 않음. 집계에서만 빼고, 제외한 행 수를 화면에 표시. 표에서는 '정보 없음'으로 보여줌.
- 지역 키는 행정동코드(str). 동 이름이 겹칠 때만 인근역을 붙여서 보여줌.
- 부산 평균이용금액은 월 총매출이 아니므로 여러 달을 합치지 않고 평균을 씀.
- 부산 업종 오타(음식료픔)는 새 컬럼(업종)에서만 정규화하고 원본 컬럼(업종대분류)은 그대로 둠.
"""
from html import escape
import inspect
import math
from zlib import crc32
import pandas as pd
import plotly.express as px
import pydeck as pdk
import streamlit as st
from settings import (
    DATA_PATH, COORD_PATH, BUSAN_DATA_PATH, BUSAN_COORD_PATH, OPENFREEMAP_STYLE_URL,
    TOP3_SEOUL_SOURCE_CAPTION, TOP3_INTRO_CAPTION, TOP3_REGION_CAPTION,
    TOP3_REGION_CAPTION_BUSAN, TOP3_PILLAR_CAPTION, TOP3_DOT_CAPTION, TOP3_LEGEND_CAPTION, MAP_ATTRIBUTION_CAPTION,
    BUSAN_TABLE_CAPTION, BUSAN_SOURCE_CAPTION,
    DATA_NOTICE_TITLE, DATA_NOTICE_INTRO, DATA_NOTICE_SECTIONS,
)
from util.utils import block_right_click_render_pydeck
MIN_SHARE = 0.01  # 특화도 기준일 때 지역 내 매출비중이 이 값 미만인 업종은 순위에서 뺌 (소액 업종이 튀는 것 방지)
RANK_COLORS = {"1위": "#d62728", "2위": "#ff7f0e", "3위": "#1f77b4"}
ELEV_MAX = 9000  # 기둥 최대 높이(m, 지도상 가상 높이). 가장 매출이 큰 동의 기둥 높이
MAP_MIN_ZOOM = 7.5  # 이보다 더 멀리 축소되지 않음
MAP_MAX_ZOOM = 15
GU_PILLAR_ZOOM_OUT = 2.0  # 구별 보기에서 기둥 모드일 때, 구에 맞춘 확대보다 이만큼 뒤로 물러남 (클수록 기둥이 작게 보임. 1.0이면 절반 크기)
MAP_LEGEND_TOP = 10  # 지도 범례에 색으로 보여줄 업종 수 (나머지는 회색 '기타')
GRAY = [170, 170, 170]
MAP_PALETTE = px.colors.qualitative.D3  # 서로 잘 구분되는 10색
NO_INFO = "정보 없음"      # 매출 결측 표시용 (0원이 아님)
NO_STATION = "인근역 없음"  # 800m 안에 매칭된 역이 없음 (대중교통이 없다는 뜻이 아님)
SEOUL_STATION_SLOTS = [f"인근지하철{i}" for i in range(1, 6)]  # 서울 인근역 슬롯 (최대 5개)
# ── 부산 (표의 [부산] 하위 탭, 지도의 [부산] 선택에 사용. 경로·안내/출처 문구는 settings.py) ──
SHOW_BUSAN_STATION = True  # False면 부산 표에서 인근역 칸을 숨김
# ── 구별 보기 ──
# 서울 자치구: 행정동코드 앞 5자리 → 자치구 이름 (행안부 행정동코드 기준). 서울 CSV에는 구 컬럼이 없어서 코드로 판별.
SEOUL_GU_BY_PREFIX = {
    "11110": "종로구", "11140": "중구", "11170": "용산구", "11200": "성동구", "11215": "광진구",
    "11230": "동대문구", "11260": "중랑구", "11290": "성북구", "11305": "강북구", "11320": "도봉구",
    "11350": "노원구", "11380": "은평구", "11410": "서대문구", "11440": "마포구", "11470": "양천구",
    "11500": "강서구", "11530": "구로구", "11545": "금천구", "11560": "영등포구", "11590": "동작구",
    "11620": "관악구", "11650": "서초구", "11680": "강남구", "11710": "송파구", "11740": "강동구",
}
# 부산은 행정동명 맨 앞 단어(구·군)로 판별 (예: '부산진구 부전동' → '부산진구')
# ==========================================
# 전체 페이지 마우스 우클릭 차단 스크립트 추가
block_right_click_render_pydeck()
# ==========================================
def validate_sales(df: pd.DataFrame, period_col: str, industry_col: str, sales_col: str, label: str, code_col: str = "행정동코드") -> pd.DataFrame:
    """중복과 잘못된 매출을 검사하며 원래 결측값은 유지합니다."""
    keys = [period_col, code_col, industry_col]
    missing_keys = df[keys].isna().any(axis=1) | df[keys].astype(str).apply(lambda c: c.str.strip().eq("")).any(axis=1)
    if missing_keys.any():
        raise ValueError(f"{label}: 기간·행정동코드·업종이 비어 있는 행이 {int(missing_keys.sum()):,}개 있습니다.")
    duplicates = df.duplicated(keys, keep=False)
    if duplicates.any():
        raise ValueError(f"{label}: 같은 기간·행정동·업종의 중복 행이 {int(duplicates.sum()):,}개 있습니다. 원본 자료를 확인해 주세요.")
    raw = df[sales_col]
    numbers = pd.to_numeric(raw, errors="coerce")
    invalid = (raw.notna() & numbers.isna()) | numbers.lt(0) | numbers.isin([float("inf"), float("-inf")])
    if invalid.any():
        raise ValueError(f"{label}: 숫자 변환 불가·음수·무한대 매출이 {int(invalid.sum()):,}개 있습니다. 원본 자료를 확인해 주세요.")
    df = df.copy()
    df[sales_col] = numbers
    return df
def validate_coords(df: pd.DataFrame, label: str) -> pd.DataFrame:
    """잘못되거나 누락된 좌표만 지도 대상에서 제외합니다."""
    df = df.copy()
    for col in ["위도", "경도"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    valid = df["위도"].between(-90, 90) & df["경도"].between(-180, 180)
    if (~valid).any():
        st.warning(f"{label}: 좌표가 없거나 올바르지 않은 {int((~valid).sum()):,}개 지점은 지도에서 제외합니다.")
    return df.loc[valid].copy()
@st.cache_data
def load_top3_data() -> pd.DataFrame:
    """서울: 식별 키는 코드, 표시용 지역명은 별도 컬럼."""
    # 서울 행정동·업종별 행은 그대로 유지하고 매출 결측도 원본 상태로 읽음.
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig", dtype={"행정동코드": str},
        usecols=["기준년분기", "행정동", "행정동코드", "업종", "당월_매출_금액"] + SEOUL_STATION_SLOTS)
    df = validate_sales(df, "기준년분기", "업종", "당월_매출_금액", "서울")
    q = df["기준년분기"].astype(str)
    df["기간"] = q.str[:4] + "년 " + q.str[4:] + "분기"
    df = df.rename(columns={"행정동코드": "코드", "당월_매출_금액": "매출액"})
    if df.empty:
        return pd.DataFrame(columns=["기간", "코드", "지역", "인근역", "업종", "매출액"])
    # 동일 행정동에 업종이 반복되므로 인근역 목록은 코드당 한 번만 구성.
    info = df.drop_duplicates("코드")[["코드", "행정동"] + SEOUL_STATION_SLOTS].copy()
    info["행정동"] = info["행정동"].str.replace("?", "·", regex=False)
    info["인근역"] = info[SEOUL_STATION_SLOTS].apply(
        lambda r: ", ".join(r.dropna().astype(str)), axis=1).replace("", NO_STATION)
    # 동명이 있을 때는 첫 번째 인근역으로 표시 이름을 구분하고 코드를 최종 식별자로 유지.
    first = info[SEOUL_STATION_SLOTS[0]].fillna(NO_STATION)
    dup = info["행정동"].duplicated(keep=False)
    info["지역"] = info["행정동"].where(~dup, info["행정동"] + "(" + first + ")")
    still = info["지역"].duplicated(keep=False)
    info["지역"] = info["지역"].where(~still, info["지역"] + "[" + info["코드"] + "]")
    return df.drop(columns=["행정동"] + SEOUL_STATION_SLOTS).merge(
        info[["코드", "지역", "인근역"]], on="코드", how="left", validate="many_to_one")
@st.cache_data
def load_top3_coords() -> pd.DataFrame | None:
    if not COORD_PATH.exists():
        return None
    coords = pd.read_csv(COORD_PATH, encoding="utf-8-sig", dtype={"행정동코드": str})
    if {"행정동코드", "위도", "경도"}.issubset(coords.columns):
        coords = coords.rename(columns={"행정동코드": "코드"})
        coords["코드"] = coords["코드"].astype(str)
        coords = validate_coords(coords[["코드", "위도", "경도"]], "서울").drop_duplicates()
        conflicts = coords.loc[coords["코드"].duplicated(keep=False), "코드"].unique()
        if len(conflicts):
            examples = ", ".join(conflicts[:10])
            raise ValueError(
                f"같은 행정동코드에 서로 다른 좌표가 있습니다 ({len(conflicts)}개 코드). "
                f"해당 코드 예시: {examples}. 좌표 파일을 확인해 주세요."
            )
        return coords
    # 예전 coordinate.csv는 지역명만 있으므로 한 번만 명칭-코드 매핑하여 키를 얻음.
    if not {"지역", "위도", "경도"}.issubset(coords.columns):
        raise ValueError("서울 좌표에는 코드/위도/경도 또는 지역/위도/경도가 필요합니다")
    names = load_top3_data()[["코드", "지역"]].drop_duplicates()
    coords["지역"] = coords["지역"].astype(str).str.replace("?", "·", regex=False)
    if coords["지역"].duplicated().any():
        raise ValueError("서울 좌표 파일에 중복 지역명이 있어. 코드가 포함된 좌표 파일을 사용해야 합니다")
    out = names.merge(coords[["지역", "위도", "경도"]], on="지역", how="left", validate="one_to_one")
    return validate_coords(out[["코드", "위도", "경도"]], "서울")
@st.cache_data
def load_busan_data() -> pd.DataFrame | None:
    if not BUSAN_DATA_PATH.exists():
        return None
    df = pd.read_csv(BUSAN_DATA_PATH, encoding="utf-8-sig", dtype={"행정동코드": str},
        usecols=["기준년월", "행정동코드", "행정동명", "업종대분류", "평균이용금액", "인근지하철역"])
    # 원본의 공백 한 칸은 isna()로 잡히지 않으므로 strip()으로 필터링.
    df = df[~df["행정동명"].fillna("").str.strip().eq("")].copy()
    df["기간"] = df["기준년월"].astype(str).str[:4] + "-" + df["기준년월"].astype(str).str[4:]
    df = df.rename(columns={"행정동코드": "코드", "평균이용금액": "매출액"})
    # 원본 업종대분류 컬럼은 보존하고 오타는 분석용 업종 컬럼에서만 정규화.
    df["업종"] = df["업종대분류"].replace({"음식료픔": "음식료품"})
    df = validate_sales(df, "기준년월", "업종", "매출액", "부산", code_col="코드")
    if df.empty:
        return None
    # 행정동코드 10자리와 SGIS ADM_CD 8자리는 동일한 코드 체계가 아님.
    df["지역_전체"] = df["행정동명"].str.strip()
    code_name = df[["코드", "지역_전체"]].drop_duplicates()
    if code_name["코드"].duplicated().any():
        raise ValueError("부산 행정동코드에 여러 지역명이 대응해")
    simple = code_name["지역_전체"].str.split(" ", n=1).str[1]
    name_count = simple.value_counts()
    name_map = dict(zip(code_name["코드"],
        simple.where(simple.map(name_count).eq(1), code_name["지역_전체"])))
    df["지역"] = df["코드"].map(name_map)
    df["인근역_원본"] = df["인근지하철역"]
    df["인근역"] = (df["인근지하철역"].str.replace(r"\s*\(\d+호선\)\s*$", "", regex=True)
        .fillna(NO_STATION))
    return df[["기간", "코드", "지역", "지역_전체", "인근역", "인근역_원본", "업종", "매출액"]]
@st.cache_data
def load_busan_coords() -> pd.DataFrame | None:
    if not BUSAN_COORD_PATH.exists():
        return None
    c = pd.read_csv(BUSAN_COORD_PATH, encoding="utf-8-sig", dtype={"ADM_CD": str})
    c["지역_전체"] = c["구"].astype(str).str.strip() + " " + c["ADM_NM"].astype(str).str.strip()
    if c["지역_전체"].duplicated().any():
        raise ValueError("부산 좌표 원본에 같은 구·동이 여러 개 존재해")
    # 부산은 매출 CSV의 10자리 행정동코드와 좌표 CSV의 8자리 ADM_CD가 달라
    # 구·동으로 연결한 뒤 매출 CSV의 10자리 코드를 붙여서 나머지 단계에서 사용.
    names = load_busan_data()[["코드", "지역_전체"]].drop_duplicates()
    out = names.merge(c[["지역_전체", "lat", "lon"]], on="지역_전체", how="left", validate="one_to_one")
    out = out[["코드", "lat", "lon"]].rename(columns={"lat": "위도", "lon": "경도"})
    return validate_coords(out, "부산")
@st.cache_data
def load_gu_maps() -> tuple[dict, dict]:
    """구별 보기용 (서울 {코드: 자치구}, 부산 {코드: 구·군}).
    서울은 행정동코드 앞 5자리, 부산은 행정동명 맨 앞 단어로 판별. 서울에서 판별 못 한 코드는 값이 None."""
    seoul = {c: SEOUL_GU_BY_PREFIX.get(c[:5]) for c in load_top3_data()["코드"].astype(str).drop_duplicates()}
    b = load_busan_data()
    busan = {} if b is None else {
        c: str(n).split(" ")[0] for c, n in b.drop_duplicates("코드").set_index("코드")["지역_전체"].items()}
    return seoul, busan
@st.cache_data
def build_top3(df: pd.DataFrame, start: str, end: str, mode: str,
               agg: str = "sum", require_complete: bool = False) -> pd.DataFrame:
    """지역 식별은 코드로 하고 표시 이름은 별도 유지. 결측은 0으로 변경하지 않음."""
    # 선택 기간의 매출 정보가 없는 행은 0으로 채우지 않음.
    window = df[(df["기간"] >= start) & (df["기간"] <= end)]
    periods = window["기간"].nunique()
    d = window.dropna(subset=["매출액"])
    if d.empty:
        return pd.DataFrame(columns=["코드", "지역", "인근역", "업종", "매출", "지역매출", "비중", "특화도", "순위", "관측기간수"])
    g = d.groupby(["코드", "지역", "인근역", "업종"], as_index=False).agg(
        매출=("매출액", agg), 관측기간수=("기간", "nunique"))
    # 여러 분기 비교에서 불완전한 관측 기간의 합계를 완전한 기간과 섞지 않는 옵션.
    if require_complete and periods > 1:
        g = g[g["관측기간수"] == periods].copy()
    if g.empty:
        return g.assign(지역매출=pd.Series(dtype=float), 비중=pd.Series(dtype=float),
                        특화도=pd.Series(dtype=float), 순위=pd.Series(dtype=str))
    # 지역 내 업종 비중과 도시 전체 업종 비중을 이용해 특화도를 계산.
    g["지역매출"] = g.groupby("코드")["매출"].transform("sum")
    g["비중"] = g["매출"].div(g["지역매출"].replace(0, float("nan")))
    city_total = g["매출"].sum()
    if city_total <= 0:
        return g.iloc[:0].assign(특화도=pd.Series(dtype=float), 순위=pd.Series(dtype=str))
    city_share = g.groupby("업종")["매출"].sum() / city_total
    g["특화도"] = g["비중"] / g["업종"].map(city_share).replace(0, float("nan"))
    if mode == "특화도":
        g = g[g["비중"] >= MIN_SHARE]
        key = "특화도"
    else:
        key = "매출"
    g = g.sort_values(["코드", key, "업종"], ascending=[True, False, True])
    g["순위"] = (g.groupby("코드").cumcount() + 1).astype(str) + "위"
    return g[g["순위"].isin(["1위", "2위", "3위"])].copy()
def period_missing(df: pd.DataFrame, start: str, end: str) -> tuple[int, int]:
    """선택 기간의 (전체 행 수, 매출 결측 행 수). 집계에서 제외한 건수를 화면에 알리려고 씀."""
    d = df[(df["기간"] >= start) & (df["기간"] <= end)]
    return len(d), int(d["매출액"].isna().sum())
def to_wide(top: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    ranks = ["1위", "2위", "3위"]
    if top.empty:
        wide = pd.DataFrame(columns=["코드", "지역", "인근역"] + ranks)
    else:
        wide = top.pivot(index=["코드", "지역", "인근역"], columns="순위", values="업종").reindex(columns=ranks).reset_index()
    allr = df[["코드", "지역", "인근역"]].drop_duplicates()
    wide = allr.merge(wide, on=["코드", "지역", "인근역"], how="left", validate="one_to_one")
    # 수치 NaN은 보존하며, 이 치환은 순위표의 표시용 문자열에만 적용.
    wide[ranks] = wide[ranks].fillna(NO_INFO)  # 표시용 문자열만 치환, 수치 NaN은 유지
    return wide.sort_values("지역").reset_index(drop=True)
def color_cell(v):
    if not isinstance(v, str) or not v:
        return ""
    if v == NO_INFO:
        return "background-color: #eeeeee; color: #888888"
    hue = crc32(v.split(" (")[0].encode()) % 360
    return f"background-color: hsl({hue},55%,82%); color: black"
def hex_to_rgb(h: str) -> list[int]:
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]
def station_label(s) -> str:
    """툴팁용 역 이름 하나. '역'으로 끝나거나 '없음'이 들어 있으면 그대로, 아니면 '역'을 붙임."""
    s = str(s)
    return s if (s.endswith("역") or "없음" in s) else s + "역"
def stations_text(s) -> str:
    """'강남, 역삼' 처럼 쉼표로 이어진 인근역 문자열을 '강남역, 역삼역'으로."""
    s = str(s)
    if s == NO_STATION:
        return s
    return ", ".join(station_label(x) for x in s.split(", "))
def render_region_view(top_df: pd.DataFrame, key: str, default_region: str | None, unit: str, region_caption: str):
    """'지역 하나 보기' 화면 한 벌 (서울/부산 하위 탭에서 같이 씀).
    unit: '억'이면 매출을 억 원으로, '원'이면 그대로(부산 평균이용금액) 막대로 보여줌."""
    regions = sorted(top_df["지역"].unique())
    if not regions:
        st.info("선택한 기간에 매출 정보가 있는 지역이 없습니다.")
        return
    default = regions.index(default_region) if default_region in regions else 0
    region = st.selectbox("지역 (글자를 입력하면 검색됩니다)", regions, index=default, key=f"{key}_region")
    r = top_df[top_df["지역"] == region].sort_values("순위")
    station = r["인근역"].iloc[0]
    st.markdown(
        "<div style='display:inline-block;padding:8px 18px;margin:4px 0 14px 0;border-radius:999px;"
        "background:#e3effc;color:#0b4a8f;font-size:1.15rem;font-weight:700;'>"
        f"🚇 인근 지하철역 : {escape(stations_text(station))}</div>",
        unsafe_allow_html=True,
    )
    cols = st.columns(len(r))
    for col, (_, row) in zip(cols, r.iterrows()):
        col.metric(f"{row['순위']} · {row['업종']}", f"{row['비중']:.1%}", f"특화도 {row['특화도']:.2f}", delta_color="off")
    if len(r) < 3:
        st.caption(f"이 지역은 선택 기간에 매출 정보가 있는 업종이 {len(r)}개뿐이라 나머지 순위는 '{NO_INFO}'입니다.")
    if unit == "억":
        plot = r.assign(값=r["매출"] / 1e8)
        x_label = "기간 매출 합계 (억 원)"
    else:
        plot = r.assign(값=r["매출"])
        x_label = "기간 평균이용금액 (원, 월별 값의 평균)"
    fig = px.bar(plot, x="값", y="업종", color="순위", orientation="h", color_discrete_map=RANK_COLORS,
                 text=plot["비중"].map(lambda x: f"{x:.1%}"), labels={"값": x_label})
    fig.update_layout(yaxis=dict(categoryorder="array", categoryarray=list(plot["업종"])[::-1]), height=300, margin=dict(l=0, r=0, t=10, b=0))  # 1위가 맨 위
    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG, key=f"{key}_chart")
    st.caption(region_caption)
try:
    df = load_top3_data()
except (OSError, ValueError, pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
    st.error(f"서울 자료를 읽을 수 없습니다: {exc}")
    st.stop()
if df.empty:
    st.info("서울 매출 자료가 없어 분석을 표시할 수 없습니다.")
    st.stop()
quarters = sorted(df["기간"].unique())
try:
    bdf = load_busan_data()
except (OSError, ValueError, pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
    st.error(f"부산 자료를 읽을 수 없습니다: {exc}")
    st.stop()
b_months = sorted(bdf["기간"].unique()) if bdf is not None else []
# 표 우측 상단 툴바(CSV 다운로드·검색·전체화면) 숨김
st.markdown("<style>[data-testid='stElementToolbar']{display:none !important;}</style>", unsafe_allow_html=True)
CHART_CONFIG = {"displayModeBar": False}  # 차트 우측 상단 메뉴(PNG 저장 등) 숨김
st.title("가장 지갑을 많이 여는 지하철역은?")
try:
    st.page_link("pages/home.py", label="홈으로 돌아가기", icon="🏠")
except Exception:  # 이 페이지만 단독 실행해서 홈 페이지가 없을 때는 링크만 생략
    pass
st.session_state.setdefault("top3_map_city", "서울")
st.session_state.setdefault("top3_map_reset", 0)
def set_map_city(city_name: str):
    """기간 또는 도시 선택 변경을 지도 초기 시점에 반영합니다."""
    st.session_state["top3_map_city"] = city_name
    st.session_state["top3_map_reset"] = st.session_state.get("top3_map_reset", 0) + 1
c1, c2, c3 = st.columns([2, 3, 3])
with c1:
    mode = st.radio("순위 기준", ["매출 규모", "특화도"], horizontal=True,
                    help="매출 규모: 기간 내 매출이 큰 업종 / 특화도: 도시 전체 대비 그 지역에서 유난히 비중이 높은 업종 "
                         f"(지역 내 비중 {MIN_SHARE:.0%} 미만은 제외됩니다). 서울은 서울 전체, 부산은 부산 전체 대비로 계산됩니다.")
with c2:
    if len(quarters) == 1:
        start = end = quarters[0]
        st.caption(f"서울 기간: {start}")
    else:
        start, end = st.select_slider("서울 기간 (분기)", options=quarters,
            value=(quarters[-1], quarters[-1]), key="top3_seoul_period",
            on_change=set_map_city, args=("서울",))
with c3:
    if bdf is None:
        b_start = b_end = None
        st.caption("부산 자료가 없어 부산 기간 선택을 숨겼습니다.")
    elif len(b_months) == 1:
        b_start = b_end = b_months[0]
        st.caption(f"부산 기간: {b_start}")
    else:
        b_start, b_end = st.select_slider("부산 기간 (월)", options=b_months,
            value=(b_months[max(0, len(b_months) - 3)], b_months[-1]),
            key="top3_busan_period", on_change=set_map_city, args=("부산",))
strict_periods = st.checkbox("서울: 선택한 모든 분기에 매출 자료가 있는 업종만 비교", value=True,
    help="여러 분기 선택 시 일부 분기에 매출이 없는 업종이 불리하게 비교되지 않도록 합니다.")
top = build_top3(df, start, end, mode, "sum", require_complete=strict_periods)
n_region = top["지역"].nunique()
n_all = df["지역"].nunique()
st.write(f"**서울 {start} ~ {end}** · 매출 정보가 있는 {n_region}개 지역 (전체 {n_all}개) · 기준: {mode}")
n_rows, n_miss_rows = period_missing(df, start, end)
# 메모장 모양 안내 상자의 문구 (상자는 탭 아래에 그림). 결측 행 수가 기간에 따라 바뀌므로 계산 뒤에 만듦
memo_lines = [
    TOP3_INTRO_CAPTION,
    "서울의 비중과 특화도는 선택한 기간 조건을 충족한 행정동·업종 자료를 기준으로 계산합니다. "
    "모든 분기 자료 조건을 적용하면 제외된 업종은 지역 및 서울 전체 비중의 계산에서도 제외됩니다. "
    "부산은 자료가 있는 월별 값의 평균을 사용하므로 업종별 관측 월수가 다를 수 있습니다.",
    f"선택 기간 서울 {n_rows:,}행 중 매출 정보가 없는 {n_miss_rows:,}행은 집계에서 제외했습니다 (0원으로 처리하지 않음). "
    "여러 분기를 고르면 선택한 집계 조건에 따라 포함되는 분기가 달라질 수 있습니다.",
]
btop = None
if bdf is not None:
    btop = build_top3(bdf, b_start, b_end, mode, "mean")  # 부산은 월별 일평균 값이라 더하지 않고 평균
tab0, tab1, tab2, tab3 = st.tabs(["📌 데이터 이용 참고사항", "지역 하나 보기", "전체 지역 표", "전체 지역 지도"])
# ── 0. 데이터 이용 시 참고사항 (첫 화면) ──
with tab0:
    st.subheader(DATA_NOTICE_TITLE)
    st.write(DATA_NOTICE_INTRO)
    for title, items in DATA_NOTICE_SECTIONS:
        st.markdown(f"**{title}**")
        items = [t.replace("~", r"\~") for t in items]  # '~'가 취소선으로 해석되지 않게
        if len(items) == 1:
            st.markdown(items[0])
        else:
            st.markdown("\n".join(f"- {t}" for t in items))
# ── 1. 지역 하나 ([서울] [부산] 하위 탭) ──
with tab1:
    one_seoul, one_busan = st.tabs(["서울", "부산"])
    with one_seoul:
        render_region_view(top, "one_seoul", "역삼1동", "억", TOP3_REGION_CAPTION)
    with one_busan:
        if bdf is None:
            st.info(f"부산 데이터 파일({BUSAN_DATA_PATH.name})을 찾을 수 없습니다.")
        else:
            st.write(f"**부산 {b_start} ~ {b_end}** · 기준: {mode}")
            render_region_view(btop, "one_busan", None, "원", TOP3_REGION_CAPTION_BUSAN)
# ── 2. 전체 표 ([서울] [부산] 하위 탭) ──
with tab2:
    sub_seoul, sub_busan = st.tabs(["서울", "부산"])
    with sub_seoul:
        wide = to_wide(top, df)
        q = st.text_input("지역 이름 검색", "", key="seoul_search")
        if q:
            wide = wide[wide["지역"].str.contains(q, regex=False)]
        wide = wide.reset_index(drop=True)
        st.dataframe(wide.style.map(color_cell, subset=["1위", "2위", "3위"]), use_container_width=True, height=600, hide_index=True)
        st.caption(f"'{NO_INFO}'은 선택 기간에 매출 자료가 제공되지 않았다는 뜻이며, 매출이 0원이라는 의미가 아닙니다. "
                   f"'{NO_STATION}'은 반경 800m 안에 매칭된 역이 없다는 뜻입니다.")
    with sub_busan:
        if bdf is None:
            st.info(f"부산 데이터 파일({BUSAN_DATA_PATH.name})을 찾을 수 없습니다.")
        else:
            st.write(f"**부산 {b_start} ~ {b_end}** · 매출 정보가 있는 {btop['지역'].nunique() if not btop.empty else 0}개 지역 "
                     f"(전체 {bdf['지역'].nunique()}개) · 기준: {mode}")
            if btop.empty:
                st.info("선택한 기간에 부산 데이터가 없습니다.")
            else:
                bwide = to_wide(btop, bdf)
                tbl_cols = ["지역"] + (["인근역"] if SHOW_BUSAN_STATION else []) + ["1위", "2위", "3위"]
                q_b = st.text_input("부산 지역 이름 검색", "", key="busan_search")
                if q_b:
                    bwide = bwide[bwide["지역"].str.contains(q_b, regex=False)]
                bwide = bwide.reset_index(drop=True)
                st.dataframe(bwide[tbl_cols].style.map(color_cell, subset=["1위", "2위", "3위"]),
                             use_container_width=True, height=600, hide_index=True)
                st.caption(BUSAN_TABLE_CAPTION)
# ── 3. 전체 지도: 서울·부산 모두 같은 지도에 표시, 버튼은 시점 이동만 담당 ──
with tab3:
    city = st.session_state["top3_map_city"]
    focus = {
        "서울": (37.49, 126.99, 10.3, 10.2),
        "부산": (35.16, 129.06, 9.8, 9.8),
    }
    view_lat, view_lon, zoom_pillar, zoom_dot = focus[city]
    col_rank, col_style = st.columns(2)
    with col_rank:
        rank_pick = st.radio("지도에 색으로 표시할 순위", ["1위", "2위", "3위"],
                             horizontal=True, key="top3_map_rank")
    with col_style:
        style = st.radio("표시 방식", ["기둥", "점"],
                         horizontal=True, key="top3_map_style")
    city_buttons = st.columns(2)
    with city_buttons[0]:
        st.button("서울로 이동", key="city_btn_seoul", use_container_width=True,
                  type="primary" if city == "서울" else "secondary",
                  on_click=set_map_city, args=("서울",))
    with city_buttons[1]:
        st.button("부산으로 이동", key="city_btn_busan", use_container_width=True,
                  type="primary" if city == "부산" else "secondary",
                  on_click=set_map_city, args=("부산",))
    # 구별 보기: 구(군)를 고르면 그 구의 행정동만 지도에 표시하고 지도 중심도 그 구로 옮김 (서울·부산 별개).
    seoul_gu_of, busan_gu_of = load_gu_maps()
    n_unmapped = sum(1 for g in seoul_gu_of.values() if g is None)
    if n_unmapped:
        st.warning(f"서울 자치구를 판별하지 못한 행정동 {n_unmapped}개는 '전체'에서만 보입니다. 행정동코드 체계를 확인해야 합니다.")
    gu_cols = st.columns(2)
    with gu_cols[0]:
        gu_seoul_pick = st.selectbox("서울 구별 보기", ["전체"] + sorted({g for g in seoul_gu_of.values() if g}),
                                     key="map_gu_seoul", on_change=set_map_city, args=("서울",))
    with gu_cols[1]:
        gu_busan_pick = st.selectbox("부산 구·군별 보기", ["전체"] + sorted(set(busan_gu_of.values())),
                                     key="map_gu_busan", on_change=set_map_city, args=("부산",),
                                     disabled=bdf is None)
    def make_city_points(city_name: str, city_top: pd.DataFrame | None,
                         city_coords: pd.DataFrame | None,
                         gu_of: dict | None = None, gu_pick: str = "전체") -> pd.DataFrame:
        """도시별 TOP3 자료를 지도 표현용으로 가공. 결측 매출은 0으로 만들지 않음.
        gu_pick이 '전체'가 아니면 마지막에 그 구(군)의 행정동만 남김. 기둥 높이·색 기준은 도시 전체로 먼저 계산함."""
        columns = ["코드", "name", "station", "r1", "r2", "r3", "lat", "lon",
                   "city", "color", "sales_txt", "elev", "sales_label"]
        if city_top is None or city_coords is None or city_top.empty:
            return pd.DataFrame(columns=columns)
        ranks = ["1위", "2위", "3위"]
        wide = (city_top.pivot(index=["코드", "지역", "인근역"], columns="순위", values="업종")
                .reindex(columns=ranks).fillna(NO_INFO).reset_index())
        points = wide.merge(city_coords, on="코드", how="left", validate="one_to_one")
        missing = int(points[["위도", "경도"]].isna().any(axis=1).sum())
        if missing:
            st.warning(f"{city_name}: 좌표가 없어 지도에서 제외된 지역 {missing}개")
        points = points.dropna(subset=["위도", "경도"]).copy()
        if points.empty:
            return pd.DataFrame(columns=columns)
        points = points.rename(columns={"지역": "name", "인근역": "station",
                    "1위": "r1", "2위": "r2", "3위": "r3",
                    "위도": "lat", "경도": "lon"})
        points["city"] = city_name
        points["station"] = points["station"].map(stations_text)
        sales = city_top.loc[city_top["순위"] == rank_pick, ["코드", "매출"]]
        if sales["코드"].duplicated().any():
            raise ValueError(f"{city_name}: 동일 코드·순위의 매출이 중복되어 있습니다")
        # 해당 순위에 매출값이 없는 지역도 점 모드에서는 정보 없음으로 안내.
        points["sales"] = points["코드"].map(sales.set_index("코드")["매출"])
        points["sales_txt"] = points["sales"].map(
            lambda x: NO_INFO if pd.isna(x) else
            (f"{x / 1e8:,.1f}억 원" if city_name == "서울" else f"{x:,.0f}원"))
        points["sales_label"] = ("업종 추정매출 (선택 분기 기준)" if city_name == "서울"
                                  else "업종 평균이용금액 (선택 기간 평균)")
        # 높이는 각 도시 내 최대값을 9000으로 정규화: 도시 간 매출액 비교가 아님.
        maximum = points["sales"].max(skipna=True)
        points["elev"] = ((ELEV_MAX * (points["sales"] / maximum) ** 0.5)
                          if pd.notna(maximum) and maximum > 0 else float("nan"))
        # 색상은 도시별 업종을 따로 계산. 서로 다른 도시 업종이 같은 색일 수 있음.
        pick_col = {"1위": "r1", "2위": "r2", "3위": "r3"}[rank_pick]
        counts = points.loc[points[pick_col] != NO_INFO, pick_col].value_counts()
        names = list(counts.index[:MAP_LEGEND_TOP])
        colors = {name: hex_to_rgb(MAP_PALETTE[i % len(MAP_PALETTE)]) for i, name in enumerate(names)}
        points["color"] = points[pick_col].map(lambda value: colors.get(value, GRAY))
        if gu_pick != "전체":
            points = points[points["코드"].map(gu_of) == gu_pick]
        st.caption(f"{city_name} 표시 지역 {len(points)}개" + (f" ({gu_pick})" if gu_pick != "전체" else ""))
        return points[columns]
    try:
        seoul_coords = load_top3_coords()
    except ValueError as exc:
        st.error(f"서울 지도 표시를 중단합니다. {exc}")
        seoul_coords = None
    seoul_points = make_city_points("서울", top, seoul_coords, seoul_gu_of, gu_seoul_pick)
    busan_points = (make_city_points("부산", btop, load_busan_coords(), busan_gu_of, gu_busan_pick)
                    if bdf is not None else pd.DataFrame())
    point_frames = [points for points in (seoul_points, busan_points) if not points.empty]
    if not point_frames:
        st.warning("지도에 표시할 서울·부산 데이터 또는 좌표가 없습니다.")
    else:
        pts = pd.concat(point_frames, ignore_index=True)
        needed = ["코드", "name", "station", "r1", "r2", "r3", "lat", "lon",
                  "city", "color", "sales_txt", "sales_label"]
        # NaN이 브라우저 JSON으로 전달되지 않도록 점 모드에서는 elev 자체를 전달하지 않음.
        if style == "점":
            # 점 모드에는 높이(elev)가 필요하지 않으며 NaN을 JSON에 전달하지 않음.
            visible = pts[needed].dropna(subset=["lat", "lon"]).copy()
            layer = pdk.Layer(
                "ScatterplotLayer", data=visible, get_position="[lon, lat]",
                get_fill_color="color", get_radius=380, radius_min_pixels=5,
                radius_max_pixels=24, opacity=0.88, stroked=True,
                get_line_color=[255, 255, 255], line_width_min_pixels=1,
                pickable=True, auto_highlight=True,
            )
            zoom = zoom_dot
            pitch = 0
        else:
            # 기둥 모드에서는 매출 정보가 없는 지역에 기둥을 만들지 않음.
            visible = pts.loc[pts["elev"].notna(), needed + ["elev"]].copy()
            layer = pdk.Layer(
                "ColumnLayer", data=visible, get_position="[lon, lat]",
                get_elevation="elev", elevation_scale=1, radius=330,
                disk_resolution=12, extruded=True, get_fill_color="color",
                pickable=True, auto_highlight=True,
            )
            zoom = zoom_pillar
            pitch = 50
        # JSON에 비표준 NaN 토큰이 직렬화되지 않도록 체크.
        if visible.isna().any().any():
            raise ValueError("지도에 전달할 데이터에 결측이 있습니다. 표시용 필드를 확인해주세요.")
        # 현재 보고 있는 도시에서 구를 골랐으면, 그 구의 행정동이 한눈에 보이게 중심과 확대를 맞춤.
        gu_now = gu_seoul_pick if city == "서울" else gu_busan_pick
        if gu_now != "전체":
            sub = visible[visible["city"] == city]
            if not sub.empty:
                view_lat, view_lon = float(sub["lat"].mean()), float(sub["lon"].mean())
                span_m = max((sub["lat"].max() - sub["lat"].min()) * 111_000,
                             (sub["lon"].max() - sub["lon"].min()) * 111_000 * math.cos(math.radians(view_lat)),
                             1500)  # 행정동이 한두 개여도 너무 확대되지 않게 최소 폭
                zoom = min(max(math.log2(156543.03 * math.cos(math.radians(view_lat)) / (span_m / 450)),
                               MAP_MIN_ZOOM), MAP_MAX_ZOOM)
                if style == "기둥":  # 기둥 높이(m)는 확대할수록 크게 보이므로 조금 뒤로 물러남
                    zoom = max(zoom - GU_PILLAR_ZOOM_OUT, MAP_MIN_ZOOM)
        view = pdk.ViewState(latitude=view_lat, longitude=view_lon, zoom=zoom,
                             pitch=pitch, bearing=0, min_zoom=MAP_MIN_ZOOM,
                             max_zoom=MAP_MAX_ZOOM)
        # API 키 없이 사용하는 OpenFreeMap 지도 스타일을 지정합니다.
        deck = pdk.Deck(
            layers=[layer], map_provider="maplibre", map_style=OPENFREEMAP_STYLE_URL,
            initial_view_state=view,
            tooltip={"html": "<b>{city} · {name}</b><br/>🚇 {station}"
                             "<br/>1위 {r1}<br/>2위 {r2}<br/>3위 {r3}"
                             f"<br/><b>{rank_pick} {{sales_label}}: {{sales_txt}}</b>",
                     "style": {"backgroundColor": "white", "color": "#222", "fontSize": "13px"}},
        )
        map_key = f"top3_map_both_{city}_{st.session_state['top3_map_reset']}"
        map_box = (st.container(key=map_key) if "key" in inspect.signature(st.container).parameters
                   else st.container())
        with map_box:
            if "key" in inspect.signature(st.pydeck_chart).parameters:
                st.pydeck_chart(deck, use_container_width=True, height=600,
                                key=map_key + "_deck")
            else:
                st.pydeck_chart(deck, use_container_width=True, height=600)
        # 지도 저작권 표시는 지도 바로 아래에 둠 (다른 안내 문구보다 먼저)
        st.caption(MAP_ATTRIBUTION_CAPTION)
        if style == "기둥":
            st.caption("서울·부산의 기둥 높이는 직접 비교하면 안 됩니다. 매출 정보가 없는 지점은 기둥을 표시하지 않습니다.")
        else:
            st.caption("점은 매출 정보가 없는 지역도 표시할 수 있습니다. 이 경우 툴팁에는 '정보 없음'으로 나옵니다.")
        st.caption("서울과 부산은 업종 분류·지표가 달라 색상과 금액을 도시 간 직접 비교하면 안 됩니다.")
        st.caption(BUSAN_TABLE_CAPTION)
# ── 페이지 설명·계산 기준 안내 (탭 아래, 메모장 모양) ──
st.markdown("---")
st.markdown(
    "<div style='background:#fff8c5;border:1px solid #e6d77a;border-radius:6px;"
    "padding:10px 14px;color:#4a4a3a;font-size:0.85rem;line-height:1.55;"
    "box-shadow:2px 2px 6px rgba(0,0,0,0.08);'>"
    "<div style='font-weight:600;margin-bottom:4px;'>📝 메모</div>"
    + "".join(f"<p style='margin:0 0 6px 0;'>{escape(t)}</p>" for t in memo_lines)
    + "</div>",
    unsafe_allow_html=True)
# ── 공공누리 출처표시: 짧은 안내 + 홈 화면 링크 (전체 출처표시는 홈 화면 하단에 있음) ──
st.markdown("---")
st.caption(TOP3_SEOUL_SOURCE_CAPTION)
st.caption(BUSAN_SOURCE_CAPTION)
try:
    st.page_link("pages/home.py", label="데이터 출처 확인하기 (홈 화면)", icon="📄")
except Exception:  # 이 페이지만 단독 실행해서 홈 페이지가 없을 때는 링크만 생략
    pass
