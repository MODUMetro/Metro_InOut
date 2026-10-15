# https://www.data.go.kr/data/15129688/fileData.do - 국가데이터처_SGIS 행정구역 통계 및 경계

import geopandas as gpd
from pathlib import Path

base = Path(r"여기에_SGIS_경계폴더_경로")  # 예: ...\국가데이터처_SGIS 행정구역 통계 및 경계\2. 경계
shp_path = Path(r"여기에_행정동_shp파일_경로")  # 예: ...\bnd_dong_00_2025_2Q.shp
out_path = Path(r"여기에_저장할_csv파일_경로")  # 예: ...\resource\busan_coordinate.csv

# 시군구 shp를 base 아래에서 자동으로 찾음
sgg_files = list(base.rglob("bnd_sigungu*.shp"))
print(sgg_files)  # 어떤 파일을 찾았는지 확인용
if not sgg_files:
    raise FileNotFoundError("bnd_sigungu 로 시작하는 shp를 못 찾음. 탐색기에서 파일명 확인해줘.")

sgg = gpd.read_file(sgg_files[0], encoding="utf-8")  # 한글 깨지면 "cp949"
sgg["SIGUNGU_CD"] = sgg["SIGUNGU_CD"].astype(str)
sgg_map = dict(zip(sgg["SIGUNGU_CD"], sgg["SIGUNGU_NM"]))  # 5자리 코드 → 구 이름

gdf = gpd.read_file(shp_path, encoding="utf-8")
gdf["ADM_CD"] = gdf["ADM_CD"].astype(str)
busan = gdf[gdf["ADM_CD"].str.startswith("21")].copy()

cent = busan.geometry.centroid.to_crs(epsg=4326)
busan["lon"] = cent.x
busan["lat"] = cent.y
busan["구"] = busan["ADM_CD"].str[:5].map(sgg_map)

print("구 매칭 실패:", busan["구"].isna().sum())
print(busan["구"].value_counts())

cols = ["ADM_CD", "구", "ADM_NM", "lon", "lat"]
busan[cols].to_csv(out_path, index=False, encoding="utf-8-sig")
print(f"저장 완료: {out_path}")

