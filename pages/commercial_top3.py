"""지역(행정동)별 TOP3 업종 시각화 (통합 대시보드의 pages/ 용)
단독 실행: streamlit run pages/commercial_top3.py

- 첫 번째 탭은 '데이터 이용 시 참고사항' (문구는 settings.py의 DATA_NOTICE_*)
- 탭(지역 하나 보기)과 탭(전체 지역 표)은 안에 [서울 | 부산] 하위 탭이 있음
  (부산: busan_commercial.csv 필요, 없으면 부산 탭에 안내만 표시)
- 탭(전체 지역 지도)은 맨 위 [서울 | 부산] 선택에 따라 서울 지도 또는 부산 지도를 보여줌
  (부산: busan_commercial.csv + busan_coordinate.csv 필요)

데이터 처리 원칙 (검수 보고서 기준)
- 서울은 분기, 부산은 월 단위라서 기간 선택을 따로 둠. 서울 분기 매출은 3으로 나누지 않음.
- 매출 결측(NaN)은 0으로 바꾸지 않음. 집계에서만 빼고, 제외한 행 수를 화면에 표시. 표에서는 '정보 없음'으로 보여줌.
- 지역 키는 행정동코드(str). 동 이름이 겹칠 때만 인근역을 붙여서 보여줌.
- 부산 평균이용금액은 월 총매출이 아니므로 여러 달을 합치지 않고 평균을 씀.
- 부산 업종 오타(음식료픔)는 새 컬럼(업종)에서만 정규화하고 원본 컬럼(업종대분류)은 그대로 둠.
"""
import inspect
import re
import sys
from pathlib import Path
from zlib import crc32

import pandas as pd
import plotly.express as px
import pydeck as pdk
import streamlit as st
from settings import (
    DATA_PATH, COORD_PATH, BUSAN_DATA_PATH, BUSAN_COORD_PATH,
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
MAP_LEGEND_TOP = 10  # 지도 범례에 색으로 보여줄 업종 수 (나머지는 회색 '기타')
GRAY = [170, 170, 170]
MAP_PALETTE = px.colors.qualitative.D3  # 서로 잘 구분되는 10색

NO_INFO = "정보 없음"      # 매출 결측 표시용 (0원이 아님)
NO_STATION = "인근역 없음"  # 800m 안에 매칭된 역이 없음 (대중교통이 없다는 뜻이 아님)
SEOUL_STATION_SLOTS = [f"인근지하철{i}" for i in range(1, 6)]  # 서울 인근역 슬롯 (최대 5개)

# ── 부산 (표의 [부산] 하위 탭, 지도의 [부산] 선택에 사용. 경로·안내/출처 문구는 settings.py) ──
SHOW_BUSAN_STATION = True  # False면 부산 표에서 인근역 칸을 숨김

# ==========================================
# 전체 페이지 마우스 우클릭 차단 스크립트 추가
block_right_click_render_pydeck()
# ==========================================


@st.cache_data
def load_top3_data() -> pd.DataFrame:
    """서울 상권 데이터. 돌려주는 컬럼: 기간, 코드, 지역, 인근역, 업종, 매출액 (매출 결측은 NaN 그대로 둠)."""
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig", dtype={"행정동코드": str},
                     usecols=["기준년분기", "행정동", "행정동코드", "업종", "당월_매출_금액"] + SEOUL_STATION_SLOTS)
    q = df["기준년분기"].astype(str)
    df["기간"] = q.str[:4] + "년 " + q.str[4:] + "분기"  # 문자열 정렬이 곧 시간순
    df = df.rename(columns={"행정동코드": "코드", "당월_매출_금액": "매출액"})

    # 인근역·지역 이름은 행정동(코드)마다 하나씩이라 코드 기준으로 한 번만 만들어서 붙임 (35만 행을 매번 돌지 않게)
    info = df.drop_duplicates("코드")[["코드", "행정동"] + SEOUL_STATION_SLOTS].copy()
    info["행정동"] = info["행정동"].str.replace("?", "·", regex=False)  # 옛 cp949 CSV 호환 (지금 CSV는 '·'가 이미 들어 있음)
    # 같은 슬롯 번호끼리 묶인 역 이름만 모음 (역 이름만 따로 정렬하지 않음)
    info["인근역"] = info[SEOUL_STATION_SLOTS].apply(lambda r: ", ".join(r.dropna()), axis=1).replace("", NO_STATION)
    # 이름이 같은데 서로 다른 곳에 있는 동(신사동)은 첫 번째 인근역을 붙여서 구분
    first = info[SEOUL_STATION_SLOTS[0]].fillna(NO_STATION)
    dup = info["행정동"].duplicated(keep=False)
    info["지역"] = info["행정동"].where(~dup, info["행정동"] + "(" + first + ")")
    # 그래도 겹치면(둘 다 인근역 없음 등) 코드를 붙여서 끝까지 구분
    still = info["지역"].duplicated(keep=False)
    info["지역"] = info["지역"].where(~still, info["지역"] + "[" + info["코드"] + "]")

    df = df.drop(columns=["행정동"] + SEOUL_STATION_SLOTS).merge(info[["코드", "지역", "인근역"]], on="코드", how="left")
    return df


@st.cache_data
def load_top3_coords() -> pd.DataFrame | None:
    if not COORD_PATH.exists():
        return None
    coords = pd.read_csv(COORD_PATH, encoding="utf-8-sig")
    coords["지역"] = coords["지역"].str.replace("?", "·", regex=False)  # 이름이 같아야 지도에 합쳐짐 (옛 파일 호환)
    return coords


@st.cache_data
def load_busan_data() -> pd.DataFrame | None:
    """부산 상권 데이터. 파일이 없으면 None (부산 탭에 안내만 표시).
    돌려주는 컬럼: 기간, 코드, 지역, 인근역, 인근역_원본, 업종, 매출액(=평균이용금액). 원본 컬럼 업종대분류는 그대로 둠."""
    if not BUSAN_DATA_PATH.exists():
        return None
    df = pd.read_csv(BUSAN_DATA_PATH, encoding="utf-8-sig", dtype={"행정동코드": str},
                     usecols=["기준년월", "행정동코드", "행정동명", "업종대분류", "평균이용금액", "인근지하철역"])
    # 공백 한 칸 같은 빈 행정동명은 isna()로 안 잡히므로 strip으로 한 번 더 확인해서 뺌 (최종본에는 없어야 정상)
    df = df[~df["행정동명"].fillna("").str.strip().eq("")].copy()
    df["기간"] = df["기준년월"].astype(str).str[:4] + "-" + df["기준년월"].astype(str).str[4:]
    df = df.rename(columns={"행정동코드": "코드", "평균이용금액": "매출액"})
    df["업종"] = df["업종대분류"].replace({"음식료픔": "음식료품"})  # 원본 오타. 새 컬럼에서만 보정
    # 서울처럼 '동' 이름만 지역으로 씀. 다른 구에 같은 이름의 동이 있으면 '구 동'을 그대로 둬서 구분
    dong = df["행정동명"].str.split(" ", n=1).str[1]
    names = df.drop_duplicates("코드")["행정동명"].str.split(" ", n=1).str[1]
    dup = names[names.duplicated(keep=False)]
    df["지역"] = dong.where(~dong.isin(dup), df["행정동명"])
    # 환승역은 원본에 호선이 붙어 있음(서면역(2호선)). 화면에는 호선을 뗀 역 이름을 쓰고 원본은 따로 보관
    df["인근역_원본"] = df["인근지하철역"]
    df["인근역"] = df["인근지하철역"].str.replace(r"\(\d호선\)$", "", regex=True).fillna(NO_STATION)
    return df[["기간", "코드", "지역", "인근역", "인근역_원본", "업종", "매출액"]]


@st.cache_data
def load_busan_coords() -> pd.DataFrame | None:
    """부산 동별 중심 좌표. 서울 coords와 같은 컬럼(지역, 위도, 경도)으로 맞춰서 돌려줌."""
    if not BUSAN_COORD_PATH.exists():
        return None
    c = pd.read_csv(BUSAN_COORD_PATH, encoding="utf-8-sig", dtype={"ADM_CD": str})
    # 1) '구 동' 전체 이름 (이름이 겹치는 동은 load_busan_data에서 이 이름으로 쓰임)
    full = c.assign(지역=c["구"] + " " + c["ADM_NM"])
    # 2) 부산 전체에서 이름이 하나뿐인 동은 '동' 이름만으로 매칭
    uniq = c.drop_duplicates("ADM_NM", keep=False).assign(지역=lambda x: x["ADM_NM"])
    out = pd.concat([full, uniq])[["지역", "lat", "lon"]]
    return out.rename(columns={"lat": "위도", "lon": "경도"})


@st.cache_data
def build_top3(df: pd.DataFrame, start: str, end: str, mode: str, agg: str = "sum") -> pd.DataFrame:
    """기간 [start, end] 매출을 모아서 지역별 상위 3개 업종을 (지역, 순위) 한 행씩 돌려줌.
    agg: 서울은 'sum'(분기 매출 합계), 부산은 'mean'(월별 일평균 값이라 더하지 않고 평균).
    매출 결측 행은 0으로 바꾸지 않고 집계에서만 뺌 (그래서 결측뿐인 지역·업종은 결과에 안 나옴)."""
    d = df[(df["기간"] >= start) & (df["기간"] <= end)].dropna(subset=["매출액"])
    g = d.groupby(["지역", "인근역", "업종"], as_index=False).agg(매출=("매출액", agg))
    g["지역매출"] = g.groupby("지역")["매출"].transform("sum")
    g["비중"] = g["매출"] / g["지역매출"]
    city_share = g.groupby("업종")["매출"].sum() / g["매출"].sum()
    g["특화도"] = g["비중"] / g["업종"].map(city_share)
    if mode == "특화도":
        g = g[g["비중"] >= MIN_SHARE]
        key = "특화도"
    else:
        key = "매출"
    g = g.sort_values(["지역", key], ascending=[True, False])
    g["순위"] = g.groupby("지역").cumcount() + 1
    top = g[g["순위"] <= 3].copy()
    top["순위"] = top["순위"].astype(str) + "위"
    return top


def period_missing(df: pd.DataFrame, start: str, end: str) -> tuple[int, int]:
    """선택 기간의 (전체 행 수, 매출 결측 행 수). 집계에서 제외한 건수를 화면에 알리려고 씀."""
    d = df[(df["기간"] >= start) & (df["기간"] <= end)]
    return len(d), int(d["매출액"].isna().sum())


def to_wide(top: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    """표 표시용: 모든 지역을 한 줄씩. 선택 기간에 매출 정보가 없는 칸은 '정보 없음' (표시용 값일 뿐 원본은 그대로)."""
    ranks = ["1위", "2위", "3위"]
    wide = top.pivot(index=["지역", "인근역"], columns="순위", values="업종").reindex(columns=ranks).reset_index()
    allr = df[["지역", "인근역"]].drop_duplicates()
    wide = allr.merge(wide, on=["지역", "인근역"], how="left")
    wide[ranks] = wide[ranks].fillna(NO_INFO)
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
        f"🚇 인근 지하철역 : {stations_text(station)}</div>",
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


df = load_top3_data()
quarters = sorted(df["기간"].unique())
bdf = load_busan_data()
b_months = sorted(bdf["기간"].unique()) if bdf is not None else []

# 표 우측 상단 툴바(CSV 다운로드·검색·전체화면) 숨김
st.markdown("<style>[data-testid='stElementToolbar']{display:none !important;}</style>", unsafe_allow_html=True)
CHART_CONFIG = {"displayModeBar": False}  # 차트 우측 상단 메뉴(PNG 저장 등) 숨김

st.title("지역(행정동)별 TOP3 업종")
st.caption(TOP3_INTRO_CAPTION)

c1, c2, c3 = st.columns([2, 3, 3])
with c1:
    mode = st.radio("순위 기준", ["매출 규모", "특화도"], horizontal=True,
                    help="매출 규모: 기간 내 매출이 큰 업종 / 특화도: 도시 전체 대비 그 지역에서 유난히 비중이 높은 업종 "
                         f"(지역 내 비중 {MIN_SHARE:.0%} 미만은 제외됩니다). 서울은 서울 전체, 부산은 부산 전체 대비로 계산됩니다.")
with c2:
    start, end = st.select_slider("서울 기간 (분기)", options=quarters, value=(quarters[-1], quarters[-1]))
with c3:
    if bdf is None:
        b_start = b_end = None
        st.caption("부산 데이터 파일이 없어 부산 기간 선택을 숨겼습니다.")
    else:
        b_start, b_end = st.select_slider("부산 기간 (월)", options=b_months, value=(b_months[-3], b_months[-1]))

top = build_top3(df, start, end, mode, "sum")
n_region = top["지역"].nunique()
n_all = df["지역"].nunique()
st.write(f"**서울 {start} ~ {end}** · 매출 정보가 있는 {n_region}개 지역 (전체 {n_all}개) · 기준: {mode}")
n_rows, n_miss_rows = period_missing(df, start, end)
st.caption(f"선택 기간 서울 {n_rows:,}행 중 매출 정보가 없는 {n_miss_rows:,}행은 집계에서 제외했습니다 (0원으로 처리하지 않음). "
           "여러 분기를 고르면 매출 정보가 있는 분기만 합산됩니다.")

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
        items = [t.replace("~", "\\~") for t in items]  # '~'가 취소선으로 해석되지 않게
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

# ── 3. 전체 지도 (pydeck) — [서울] [부산] 버튼 ──
with tab3:
    if "top3_map_city" not in st.session_state:
        st.session_state["top3_map_city"] = "서울"
    city = st.session_state["top3_map_city"]  # 버튼은 아래쪽에 있지만, 어떤 도시 데이터를 쓸지는 여기서 먼저 정함

    if city == "서울":
        map_top = top
        coords = load_top3_coords()
        view_lat, view_lon = 37.49, 126.99
        zoom_pillar, zoom_dot = 10.3, 10.2
        sales_label = "업종 매출"
        no_msg = "지도에 필요한 좌표 파일(coordinate.csv)을 찾을 수 없습니다."
    else:
        map_top = btop
        coords = load_busan_coords()
        view_lat, view_lon = 35.16, 129.06
        zoom_pillar, zoom_dot = 9.8, 9.8
        sales_label = "업종 평균이용금액(기간 평균)"
        no_msg = f"부산 데이터({BUSAN_DATA_PATH.name}) 또는 좌표 파일({BUSAN_COORD_PATH.name})을 찾을 수 없습니다."

    can_reset = "key" in inspect.signature(st.container).parameters
    if "top3_map_reset" not in st.session_state:
        st.session_state["top3_map_reset"] = 0

    def pick_city(name: str):
        """서울/부산 버튼 동작. 이미 그 도시여도 reset 번호를 올려서 지도를 새로 그림 -> 지도를 옮겨 놨어도 처음 시점으로 돌아옴."""
        st.session_state["top3_map_city"] = name
        st.session_state["top3_map_reset"] += 1
        st.rerun()

    if map_top is None or coords is None or map_top.empty:
        st.info(no_msg)
        # 데이터가 없어도 서울/부산 버튼은 있어야 다시 돌아갈 수 있음
        e1, e2, _ = st.columns(3)
        with e1:
            if st.button("서울", key="city_btn_seoul_empty", use_container_width=True,
                         type="primary" if city == "서울" else "secondary"):
                pick_city("서울")
        with e2:
            if st.button("부산", key="city_btn_busan_empty", use_container_width=True,
                         type="primary" if city == "부산" else "secondary"):
                pick_city("부산")
    else:
        m1, m2 = st.columns(2)
        with m1:
            rank_pick = st.radio("지도에 색으로 표시할 순위", ["1위", "2위", "3위"], horizontal=True, key="top3_map_rank")
        with m2:
            style = st.radio("표시 방식", ["기둥", "점"], horizontal=True, key="top3_map_style")
        ranks = ["1위", "2위", "3위"]
        wide3 = (map_top.pivot(index=["지역", "인근역"], columns="순위", values="업종")
                 .reindex(columns=ranks).fillna(NO_INFO).reset_index())  # 순위가 비는 지역은 '정보 없음'
        pts = wide3.merge(coords, on="지역", how="inner").rename(
            columns={"지역": "name", "인근역": "station", "1위": "r1", "2위": "r2", "3위": "r3", "위도": "lat", "경도": "lon"})
        n_miss = wide3["지역"].nunique() - pts["name"].nunique()
        if n_miss > 0:
            st.caption(f"⚠️ 좌표를 못 찾아 지도에서 빠진 지역: {n_miss}개")

        if pts.empty:
            st.warning("지도에 표시할 지역이 없습니다. 좌표 파일의 지역 이름이 데이터와 맞는지 확인해주세요.")
        else:
            pts["station"] = pts["station"].map(stations_text)

            # 선택한 순위 업종의 매출 → 기둥 높이. 소수의 큰 동이 압도적이라 제곱근으로 완만하게 변환
            sales = map_top[map_top["순위"] == rank_pick].set_index("지역")["매출"]
            pts["sales"] = pts["name"].map(sales)
            if city == "서울":
                fmt = lambda x: f"{x / 1e8:,.1f}억 원"
            else:
                fmt = lambda x: f"{x:,.0f}원"  # 부산은 '월별 일평균' 값이라 억 원으로 바꾸지 않음
            pts["sales_txt"] = pts["sales"].map(lambda x: NO_INFO if pd.isna(x) else fmt(x))
            # 해당 순위가 없는 지역(NaN)은 기둥 높이만 0으로 표시 (표시용. 매출을 0원으로 보여주지 않고 '정보 없음'이라고 씀)
            pts["elev"] = (ELEV_MAX * (pts["sales"] / pts["sales"].max()) ** 0.5).fillna(0)

            pick_col = {"1위": "r1", "2위": "r2", "3위": "r3"}[rank_pick]
            counts = pts.loc[pts[pick_col] != NO_INFO, pick_col].value_counts()
            legend_names = list(counts.index[:MAP_LEGEND_TOP])
            color_of = {n: hex_to_rgb(MAP_PALETTE[i % len(MAP_PALETTE)]) for i, n in enumerate(legend_names)}
            pts["color"] = pts[pick_col].map(lambda n: color_of.get(n, GRAY))

            chips = "".join(
                f"<span style='display:inline-flex;align-items:center;margin:2px 14px 2px 0;font-size:0.9rem;'>"
                f"<span style='width:12px;height:12px;border-radius:50%;background:rgb({','.join(map(str, color_of[n]))});"
                f"display:inline-block;margin-right:6px;'></span>{n} ({counts[n]})</span>"
                for n in legend_names)
            n_other = int(counts.drop(legend_names).sum())
            if n_other:
                chips += (f"<span style='display:inline-flex;align-items:center;font-size:0.9rem;'>"
                          f"<span style='width:12px;height:12px;border-radius:50%;background:rgb(170,170,170);"
                          f"display:inline-block;margin-right:6px;'></span>그 외 업종 ({n_other})</span>")
            n_noinfo = int((pts[pick_col] == NO_INFO).sum())
            if n_noinfo:
                chips += (f"<span style='display:inline-flex;align-items:center;font-size:0.9rem;'>"
                          f"<span style='width:12px;height:12px;border-radius:50%;background:rgb(170,170,170);"
                          f"display:inline-block;margin-right:6px;'></span>{NO_INFO} ({n_noinfo})</span>")
            st.markdown(f"<div>{chips}</div>", unsafe_allow_html=True)

            # [서울] [부산] 두 칸. 버튼을 누르면 (지도를 옮겨 놨어도, 이미 선택된 도시여도) 그 도시의 처음 시점으로 지도를 새로 그림
            # (지도를 감싼 container와 pydeck_chart의 key를 바꿔서 새로 그리는 방식. key 기능이 없는 오래된 Streamlit에서는 새로 그리기만 안 됨)
            c_seoul, c_busan = st.columns(2)
            with c_seoul:
                if st.button("서울", key="city_btn_seoul", use_container_width=True,
                             type="primary" if city == "서울" else "secondary"):
                    pick_city("서울")
            with c_busan:
                if st.button("부산", key="city_btn_busan", use_container_width=True,
                             type="primary" if city == "부산" else "secondary"):
                    pick_city("부산")

            keep_cols = ["name", "station", "r1", "r2", "r3", "lat", "lon", "color", "sales_txt", "elev"]
            if style == "기둥":
                layer = pdk.Layer(
                    "ColumnLayer", data=pts[keep_cols], get_position="[lon, lat]", get_elevation="elev", elevation_scale=1,
                    radius=330, disk_resolution=12, extruded=True, get_fill_color="color", pickable=True, auto_highlight=True)
                view = pdk.ViewState(latitude=view_lat, longitude=view_lon, zoom=zoom_pillar, pitch=50, bearing=0,
                                      min_zoom=MAP_MIN_ZOOM, max_zoom=MAP_MAX_ZOOM)
            else:
                layer = pdk.Layer(
                    "ScatterplotLayer", data=pts[keep_cols], get_position="[lon, lat]", get_fill_color="color",
                    get_radius=380, radius_min_pixels=5, radius_max_pixels=24, opacity=0.88, stroked=True,
                    get_line_color=[255, 255, 255], line_width_min_pixels=1, pickable=True)
                view = pdk.ViewState(latitude=view_lat, longitude=view_lon, zoom=zoom_dot, pitch=0,
                                      min_zoom=MAP_MIN_ZOOM, max_zoom=MAP_MAX_ZOOM)

            station_line = "<br/>🚇 {station}" if (city == "서울" or SHOW_BUSAN_STATION) else ""
            deck = pdk.Deck(
                layers=[layer], map_style="light", initial_view_state=view,
                tooltip={"html": "<b>{name}</b>" + station_line + "<br/>1위 {r1}<br/>2위 {r2}<br/>3위 {r3}"
                                 f"<br/><b>{rank_pick} {sales_label} {{sales_txt}}</b>",
                         "style": {"backgroundColor": "white", "color": "#222", "fontSize": "13px"}})
            # key에 city와 reset 번호를 넣어서 버튼을 누를 때마다 지도 시점이 새로 잡힘
            map_key = f"top3_mapwrap_{city}_{st.session_state['top3_map_reset']}"
            map_box = st.container(key=map_key) if can_reset else st.container()
            with map_box:
                if "key" in inspect.signature(st.pydeck_chart).parameters:
                    st.pydeck_chart(deck, use_container_width=True, height=600, key=map_key + "_deck")
                else:
                    st.pydeck_chart(deck, use_container_width=True, height=600)
            if style == "기둥":
                st.caption(TOP3_PILLAR_CAPTION)
            else:
                st.caption(TOP3_DOT_CAPTION)
            st.caption(TOP3_LEGEND_CAPTION)
            if city == "부산":
                st.caption(BUSAN_TABLE_CAPTION)
            st.caption(MAP_ATTRIBUTION_CAPTION)

# ── 공공누리 출처표시: 짧은 안내 + 홈 화면 링크 (전체 출처표시는 홈 화면 하단에 있음) ──
st.markdown("---")
st.caption(TOP3_SEOUL_SOURCE_CAPTION)
st.caption(BUSAN_SOURCE_CAPTION)
try:
    st.page_link("pages/home.py", label="데이터 출처 확인하기 (홈 화면)", icon="📄")
except Exception:  # 이 페이지만 단독 실행해서 홈 페이지가 없을 때는 링크만 생략
    pass