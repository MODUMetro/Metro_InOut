"""지역(행정동)별 TOP3 업종 시각화 (통합 대시보드의 pages/ 용)
단독 실행: streamlit run pages/commercial_top3.py

- 탭1(지역 하나 보기)은 서울 데이터만
- 탭2(전체 지역 표) 안에 [서울 | 부산] 하위 탭이 있어서, 서울 탭은 서울 표·부산 탭은 부산 표를 보여줌
  (부산: busan_commercial.csv 필요, 없으면 부산 탭에 안내만 표시)
- 탭3(전체 지역 지도)은 맨 위 [서울 | 부산] 선택에 따라 서울 지도 또는 부산 지도를 보여줌
  (부산: busan_commercial.csv + busan_coordinate.csv 필요)
"""
import inspect
import sys
from pathlib import Path
from zlib import crc32

import pandas as pd
import plotly.express as px
import pydeck as pdk
import streamlit as st
from settings import (
    DATA_PATH, COORD_PATH, BUSAN_DATA_PATH, BUSAN_COORD_PATH,
    COPYRIGHT_SHORT, TOP3_INTRO_CAPTION, TOP3_REGION_CAPTION,
    TOP3_PILLAR_CAPTION, TOP3_DOT_CAPTION, TOP3_LEGEND_CAPTION, MAP_ATTRIBUTION_CAPTION,
    BUSAN_TABLE_CAPTION, BUSAN_SOURCE_CAPTION,
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

# ── 부산 (탭2 표의 [부산] 하위 탭, 탭3 지도의 [부산] 선택에 사용. 경로·안내/출처 문구는 settings.py) ──
SHOW_BUSAN_STATION = True  # False면 부산 표에서 인근역 칸을 숨김

# ==========================================
# 전체 페이지 마우스 우클릭 차단 스크립트 추가
block_right_click_render_pydeck()
# ==========================================

@st.cache_data
def load_top3_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig",
                     usecols=["기준년월", "행정동", "인근지하철역명", "업종", "점포수", "매출액"])
    df["월"] = df["기준년월"].astype(str).str[:4] + "-" + df["기준년월"].astype(str).str[4:]
    # 이름이 같은데 서로 다른 곳에 있는 동(신사동)은 인근역을 붙여서 구분
    n_st = df.groupby("행정동")["인근지하철역명"].nunique()
    dup = n_st[n_st > 1].index
    df["지역"] = df["행정동"].where(~df["행정동"].isin(dup), df["행정동"] + "(" + df["인근지하철역명"] + ")")
    # 원본(cp949)에서 가운뎃점(·)이 '?'로 저장돼 있어서(예: 종로1?2?3?4가동) 화면에는 '·'로 보여줌
    df["지역"] = df["지역"].str.replace("?", "·", regex=False)
    return df


@st.cache_data
def load_top3_coords() -> pd.DataFrame | None:
    if not COORD_PATH.exists():
        return None
    coords = pd.read_csv(COORD_PATH, encoding="utf-8-sig")
    coords["지역"] = coords["지역"].str.replace("?", "·", regex=False)  # 위와 같은 이유 (이름이 같아야 지도에 합쳐짐)
    return coords


@st.cache_data
def load_busan_data() -> pd.DataFrame | None:
    """부산 상권 데이터. 파일이 없으면 None (부산 탭에 안내만 표시)."""
    if not BUSAN_DATA_PATH.exists():
        return None
    df = pd.read_csv(BUSAN_DATA_PATH, encoding="utf-8-sig",
                     usecols=["기준년월", "행정동", "인근지하철역명", "업종", "매출액"])
    df["월"] = df["기준년월"].astype(str).str[:4] + "-" + df["기준년월"].astype(str).str[4:]
    # 서울처럼 '동' 이름만 지역으로 씀. 다른 구에 같은 이름의 동이 있으면 '구 동'을 그대로 둬서 구분
    dong = df["행정동"].str.split(" ", n=1).str[1]
    names = df.drop_duplicates("행정동")["행정동"].str.split(" ", n=1).str[1]
    dup = names[names.duplicated(keep=False)]
    df["지역"] = dong.where(~dong.isin(dup), df["행정동"])
    return df


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
def build_top3(df: pd.DataFrame, start: str, end: str, mode: str) -> pd.DataFrame:
    """기간 [start, end] 매출을 합쳐서 지역별 상위 3개 업종을 (지역, 순위) 한 행씩 돌려줌."""
    d = df[(df["월"] >= start) & (df["월"] <= end)]
    g = d.groupby(["지역", "인근지하철역명", "업종"], as_index=False).agg(매출=("매출액", "sum"))
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


def color_cell(v):
    if not isinstance(v, str) or not v:
        return ""
    hue = crc32(v.split(" (")[0].encode()) % 360
    return f"background-color: hsl({hue},55%,82%); color: black"


def hex_to_rgb(h: str) -> list[int]:
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def station_label(s) -> str:
    """툴팁용 역 이름. '역'으로 끝나거나 '없음'이 들어 있으면 그대로, 아니면 '역'을 붙임."""
    s = str(s)
    return s if (s.endswith("역") or "없음" in s) else s + "역"


df = load_top3_data()
months = sorted(df["월"].unique())

# 표 우측 상단 툴바(CSV 다운로드·검색·전체화면) 숨김
st.markdown("<style>[data-testid='stElementToolbar']{display:none !important;}</style>", unsafe_allow_html=True)
CHART_CONFIG = {"displayModeBar": False}  # 차트 우측 상단 메뉴(PNG 저장 등) 숨김

st.title("지역(행정동)별 TOP3 업종")
st.caption(TOP3_INTRO_CAPTION)

c1, c2 = st.columns([2, 3])
with c1:
    mode = st.radio("순위 기준", ["매출 규모", "특화도"], horizontal=True,
                    help="매출 규모: 기간 내 매출 합계가 큰 업종 / 특화도: 서울 전체 대비 그 지역에서 유난히 비중이 높은 업종 "
                         f"(지역 내 비중 {MIN_SHARE:.0%} 미만은 제외됩니다). 부산은 부산 전체 대비로 계산됩니다.")
with c2:
    start, end = st.select_slider("기간", options=months, value=(months[-3], months[-1]))

top = build_top3(df, start, end, mode)
n_region = top["지역"].nunique()
st.write(f"**{start} ~ {end}** · 서울 {n_region}개 지역 · 기준: {mode}")

tab1, tab2, tab3 = st.tabs(["지역 하나 보기", "전체 지역 표", "전체 지역 지도"])

# ── 1. 지역 하나 ──
with tab1:
    regions = sorted(top["지역"].unique())
    default = regions.index("역삼1동") if "역삼1동" in regions else 0
    region = st.selectbox("지역 (글자를 입력하면 검색됩니다)", regions, index=default)
    r = top[top["지역"] == region].sort_values("순위")
    station = r["인근지하철역명"].iloc[0]
    st.markdown(
        "<div style='display:inline-block;padding:8px 18px;margin:4px 0 14px 0;border-radius:999px;"
        "background:#e3effc;color:#0b4a8f;font-size:1.15rem;font-weight:700;'>"
        f"🚇 인근 지하철역 : {station}역</div>",
        unsafe_allow_html=True,
    )
    cols = st.columns(len(r))
    for col, (_, row) in zip(cols, r.iterrows()):
        col.metric(f"{row['순위']} · {row['업종']}", f"{row['비중']:.1%}", f"특화도 {row['특화도']:.2f}", delta_color="off")
    plot = r.assign(매출_억=r["매출"] / 1e8)
    fig = px.bar(plot, x="매출_억", y="업종", color="순위", orientation="h", color_discrete_map=RANK_COLORS,
                 text=plot["비중"].map(lambda x: f"{x:.1%}"),
                 labels={"매출_억": "기간 매출 합계 (억 원)"})
    fig.update_layout(yaxis=dict(categoryorder="array", categoryarray=list(plot["업종"])[::-1]), height=300, margin=dict(l=0, r=0, t=10, b=0))  # 1위가 맨 위
    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
    st.caption(TOP3_REGION_CAPTION)

# ── 2. 전체 표 ([서울] [부산] 하위 탭) ──
with tab2:
    sub_seoul, sub_busan = st.tabs(["서울", "부산"])

    with sub_seoul:
        wide = top.pivot(index=["지역", "인근지하철역명"], columns="순위", values="업종").reset_index()
        wide = wide.rename(columns={"인근지하철역명": "인근역"})
        q = st.text_input("지역 이름 검색", "", key="seoul_search")
        if q:
            wide = wide[wide["지역"].str.contains(q)]
        wide = wide.reset_index(drop=True)
        st.dataframe(wide.style.map(color_cell, subset=["1위", "2위", "3위"]), use_container_width=True, height=600, hide_index=True)

    with sub_busan:
        bdf = load_busan_data()
        if bdf is None:
            st.info(f"부산 데이터 파일({BUSAN_DATA_PATH.name})을 찾을 수 없습니다.")
        else:
            btop = build_top3(bdf, start, end, mode)  # 위에서 고른 기간·순위 기준을 부산에도 똑같이 적용
            if btop.empty:
                st.info("선택한 기간에 부산 데이터가 없습니다.")
            else:
                bwide = btop.pivot(index=["지역", "인근지하철역명"], columns="순위", values="업종").reset_index()
                bwide = bwide.rename(columns={"인근지하철역명": "인근역"})
                tbl_cols = ["지역"] + (["인근역"] if SHOW_BUSAN_STATION else []) + ["1위", "2위", "3위"]
                q_b = st.text_input("부산 지역 이름 검색", "", key="busan_search")
                if q_b:
                    bwide = bwide[bwide["지역"].str.contains(q_b)]
                bwide = bwide.sort_values("지역").reset_index(drop=True)
                st.dataframe(bwide[tbl_cols].style.map(color_cell, subset=["1위", "2위", "3위"]),
                             use_container_width=True, height=600, hide_index=True)
                st.caption(BUSAN_TABLE_CAPTION)

# ── 3. 전체 지도 (pydeck) — [서울] [부산] [처음 위치로] 버튼 ──
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
        bdf_map = load_busan_data()
        map_top = None if bdf_map is None else build_top3(bdf_map, start, end, mode)
        coords = load_busan_coords()
        view_lat, view_lon = 35.16, 129.06
        zoom_pillar, zoom_dot = 9.8, 9.8
        sales_label = "업종 소비매출"
        no_msg = f"부산 데이터({BUSAN_DATA_PATH.name}) 또는 좌표 파일({BUSAN_COORD_PATH.name})을 찾을 수 없습니다."

    can_reset = "key" in inspect.signature(st.container).parameters
    if "top3_map_reset" not in st.session_state:
        st.session_state["top3_map_reset"] = 0

    if map_top is None or coords is None or map_top.empty:
        st.info(no_msg)
        # 데이터가 없어도 서울/부산 버튼은 있어야 다시 돌아갈 수 있음
        e1, e2, _ = st.columns(3)
        with e1:
            if st.button("서울", key="city_btn_seoul_empty", use_container_width=True,
                         type="primary" if city == "서울" else "secondary"):
                st.session_state["top3_map_city"] = "서울"
                st.rerun()
        with e2:
            if st.button("부산", key="city_btn_busan_empty", use_container_width=True,
                         type="primary" if city == "부산" else "secondary"):
                st.session_state["top3_map_city"] = "부산"
                st.rerun()
    else:
        m1, m2 = st.columns(2)
        with m1:
            rank_pick = st.radio("지도에 색으로 표시할 순위", ["1위", "2위", "3위"], horizontal=True, key="top3_map_rank")
        with m2:
            style = st.radio("표시 방식", ["기둥", "점"], horizontal=True, key="top3_map_style")
        wide3 = map_top.pivot(index=["지역", "인근지하철역명"], columns="순위", values="업종").reset_index()
        pts = wide3.merge(coords, on="지역", how="inner").rename(
            columns={"지역": "name", "인근지하철역명": "station", "1위": "r1", "2위": "r2", "3위": "r3", "위도": "lat", "경도": "lon"})
        n_miss = wide3["지역"].nunique() - pts["name"].nunique()
        if n_miss > 0:
            st.caption(f"⚠️ 좌표를 못 찾아 지도에서 빠진 지역: {n_miss}개")

        if pts.empty:
            st.warning("지도에 표시할 지역이 없습니다. 좌표 파일의 지역 이름이 데이터와 맞는지 확인해주세요.")
        else:
            pts["station"] = pts["station"].map(station_label)

            # 선택한 순위 업종의 매출 → 기둥 높이. 소수의 큰 동이 압도적이라 제곱근으로 완만하게 변환
            sales = map_top[map_top["순위"] == rank_pick].set_index("지역")["매출"]
            pts["sales"] = pts["name"].map(sales)
            if city == "서울":
                pts["sales_txt"] = (pts["sales"] / 1e8).map(lambda x: f"{x:,.1f}억 원")
            else:
                pts["sales_txt"] = pts["sales"].map(lambda x: f"{x:,.0f}")  # 부산은 단위가 '월별 일평균'이라 억 원으로 바꾸지 않음
            pts["elev"] = ELEV_MAX * (pts["sales"] / pts["sales"].max()) ** 0.5

            pick_col = {"1위": "r1", "2위": "r2", "3위": "r3"}[rank_pick]
            counts = pts[pick_col].value_counts()
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
            st.markdown(f"<div>{chips}</div>", unsafe_allow_html=True)

            # [서울] [부산] [처음 위치로] 세 칸. st.columns(3)이 똑같은 너비로 삼등분해줌
            # '처음 위치로'는 지도를 감싼 container의 key를 바꿔 지도를 새로 그리면 처음 시점으로 돌아가는 방식
            # (container의 key 기능이 없는 오래된 Streamlit에서는 그 칸만 비워둠)
            c_seoul, c_busan, c_home = st.columns(3)
            with c_seoul:
                if st.button("서울", key="city_btn_seoul", use_container_width=True,
                             type="primary" if city == "서울" else "secondary"):
                    st.session_state["top3_map_city"] = "서울"
                    st.rerun()
            with c_busan:
                if st.button("부산", key="city_btn_busan", use_container_width=True,
                             type="primary" if city == "부산" else "secondary"):
                    st.session_state["top3_map_city"] = "부산"
                    st.rerun()
            with c_home:
                if can_reset:
                    if st.button("🏠 처음 위치로", key="top3_map_home", use_container_width=True):
                        st.session_state["top3_map_reset"] += 1
                        st.session_state["top3_map_city"] = "서울"
                        st.rerun()

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
            # key에 city를 넣어서 서울↔부산을 바꿀 때 지도 시점이 새로 잡힘
            map_box = (st.container(key=f"top3_mapwrap_{city}_{st.session_state['top3_map_reset']}")
                       if can_reset else st.container())
            with map_box:
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
st.caption(COPYRIGHT_SHORT)
st.caption(BUSAN_SOURCE_CAPTION)
try:
    st.page_link("pages/home.py", label="데이터 출처 확인하기 (홈 화면)", icon="📄")
except Exception:  # 이 페이지만 단독 실행해서 홈 페이지가 없을 때는 링크만 생략
    pass