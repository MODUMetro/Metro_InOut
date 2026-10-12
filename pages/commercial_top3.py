"""지역(행정동)별 TOP3 업종 시각화 (통합 대시보드의 pages/ 용)
단독 실행: streamlit run pages/commercial_top3.py
"""
import sys
from pathlib import Path
from zlib import crc32

import pandas as pd
import plotly.express as px
import streamlit as st

# CSV는 resource 폴더(pages 폴더와 같은 위치)에 둠. exe(PyInstaller)로 묶였을 때는 압축 해제 폴더(_MEIPASS) 기준
BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
DATA_PATH = BASE / "resource" / "seoul_monthly_station_ridership_filled_nearest.csv"
MIN_SHARE = 0.01  # 특화도 기준일 때 지역 내 매출비중이 이 값 미만인 업종은 순위에서 뺌 (소액 업종이 튀는 것 방지)
RANK_COLORS = {"1위": "#d62728", "2위": "#ff7f0e", "3위": "#1f77b4"}


@st.cache_data
def load_top3_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig",
                     usecols=["기준년월", "행정동", "인근지하철역명", "업종", "점포수", "매출액"])
    df["월"] = df["기준년월"].astype(str).str[:4] + "-" + df["기준년월"].astype(str).str[4:]
    # 이름이 같은데 서로 다른 곳에 있는 동(신사동)은 인근역을 붙여서 구분
    n_st = df.groupby("행정동")["인근지하철역명"].nunique()
    dup = n_st[n_st > 1].index
    df["지역"] = df["행정동"].where(~df["행정동"].isin(dup), df["행정동"] + "(" + df["인근지하철역명"] + ")")
    return df


@st.cache_data
def build_top3(df: pd.DataFrame, start: str, end: str, mode: str) -> pd.DataFrame:
    """기간 [start, end] 매출을 합쳐서 지역별 상위 3개 업종을 (지역, 순위) 한 행씩 돌려줌."""
    d = df[(df["월"] >= start) & (df["월"] <= end)]
    g = d.groupby(["지역", "인근지하철역명", "업종"], as_index=False).agg(매출=("매출액", "sum"))
    g["지역매출"] = g.groupby("지역")["매출"].transform("sum")
    g["비중"] = g["매출"] / g["지역매출"]
    seoul = g.groupby("업종")["매출"].sum() / g["매출"].sum()
    g["특화도"] = g["비중"] / g["업종"].map(seoul)
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


df = load_top3_data()
months = sorted(df["월"].unique())

# 표 우측 상단 툴바(CSV 다운로드·검색·전체화면) 숨김
st.markdown("<style>[data-testid='stElementToolbar']{display:none !important;}</style>", unsafe_allow_html=True)
CHART_CONFIG = {"displayModeBar": False}  # 차트 우측 상단 메뉴(PNG 저장 등) 숨김

st.title("지역(행정동)별 TOP3 업종")
st.caption("한 지역에서 어떤 업종이 가장 강한지 상위 3개를 보여줘. 데이터는 분기 값을 3개월로 나눈 것이라 월 단위로 고르면 같은 분기 안에서는 순위가 거의 안 변해.")

c1, c2 = st.columns([2, 3])
with c1:
    mode = st.radio("순위 기준", ["매출 규모", "특화도"], horizontal=True,
                    help="매출 규모: 기간 내 매출 합계가 큰 업종 / 특화도: 서울 전체 대비 그 지역에서 유난히 비중이 높은 업종 "
                         f"(지역 내 비중 {MIN_SHARE:.0%} 미만은 제외)")
with c2:
    start, end = st.select_slider("기간", options=months, value=(months[-3], months[-1]))

top = build_top3(df, start, end, mode)
n_region = top["지역"].nunique()
st.write(f"**{start} ~ {end}** · {n_region}개 지역 · 기준: {mode}")

tab1, tab2, tab3 = st.tabs(["지역 하나 보기", "전체 지역 표", "업종별 TOP3 개수"])

# ── 1. 지역 하나 ──
with tab1:
    regions = sorted(top["지역"].unique())
    default = regions.index("역삼1동") if "역삼1동" in regions else 0
    region = st.selectbox("지역 (글자를 입력하면 검색돼)", regions, index=default)
    r = top[top["지역"] == region].sort_values("순위")
    st.caption(f"인근 지하철역: {r['인근지하철역명'].iloc[0]}")
    cols = st.columns(len(r))
    for col, (_, row) in zip(cols, r.iterrows()):
        col.metric(f"{row['순위']} · {row['업종']}", f"{row['비중']:.1%}", f"특화도 {row['특화도']:.2f}", delta_color="off")
    plot = r.assign(매출_억=r["매출"] / 1e8)
    fig = px.bar(plot, x="매출_억", y="업종", color="순위", orientation="h", color_discrete_map=RANK_COLORS,
                 text=plot["비중"].map(lambda x: f"{x:.1%}"), category_orders={"업종": list(plot["업종"])},
                 labels={"매출_억": "기간 매출 합계 (억 원)"})
    fig.update_layout(yaxis=dict(autorange="reversed"), height=300, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
    st.caption("막대 옆 숫자는 그 지역 전체 매출 중 해당 업종의 비중이야. 특화도 1보다 크면 서울 평균보다 이 지역에서 더 강한 업종이야.")

# ── 2. 전체 표 ──
with tab2:
    wide = top.pivot(index=["지역", "인근지하철역명"], columns="순위", values="업종").reset_index()
    wide = wide.rename(columns={"인근지하철역명": "인근역"})
    q = st.text_input("지역 이름 검색", "")
    if q:
        wide = wide[wide["지역"].str.contains(q)]
    wide = wide.reset_index(drop=True)
    st.dataframe(wide.style.map(color_cell, subset=["1위", "2위", "3위"]), use_container_width=True, height=600, hide_index=True)

# ── 3. 업종별 개수 ──
with tab3:
    cnt = top.groupby(["업종", "순위"]).size().reset_index(name="지역수")
    order = cnt.groupby("업종")["지역수"].sum().sort_values(ascending=False)
    n_show = st.slider("보여줄 업종 수", 5, min(40, len(order)), 20)
    keep = list(order.index[:n_show])
    fig2 = px.bar(cnt[cnt["업종"].isin(keep)], x="지역수", y="업종", color="순위", orientation="h", text="지역수",
                  color_discrete_map=RANK_COLORS, category_orders={"업종": keep, "순위": ["1위", "2위", "3위"]})
    fig2.update_traces(textposition="inside", insidetextanchor="middle", textfont_color="white")  # 칸 안: 순위별 지역수
    for name in keep:  # 막대 끝: 1·2·3위 합계
        fig2.add_annotation(x=order[name], y=name, text=f"<b>{order[name]}</b>", showarrow=False, xanchor="left", xshift=6)
    fig2.update_layout(yaxis=dict(autorange="reversed"), height=max(400, 24 * n_show), margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig2, use_container_width=True, config=CHART_CONFIG)
    st.caption("각 업종이 몇 개 지역에서 1·2·3위 안에 들었는지 보여줘.")