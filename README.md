# 코드를 받고 사용하는 방법은 notion에 공유했습니다
**https://app.notion.com/p/3cf9d008ed5380d7a3e7de246ba2d0dc** 

# 스트림릿으로 보여주는 사이트 변천사
* 배포사이트
    * https://metroinoutgit-i6qqpmcuuqhatw6neryruj.streamlit.app/

* 1차 마무리
    * 최신 커밋 hash: 0b7e7952f274abb68a137b2c5b57160b0e2ad6d8
    * 브랜치이름: main    

* 2차 진행
    * 브랜치이름: main
    * 1차 진행안에 추가 및 개선사항으로 진행하기

# 서울·부산 상권 데이터

본 프로젝트는 서울·부산의 공개 데이터를 가공·결합하여 활용하였습니다.

## 데이터 출처

### 서울 — 서울 열린데이터광장

| 원본 데이터 | 제공기관 | 저작권자 | 공개연도 | 이용조건 | 출처 |
|---|---|---|---|---|---|
| 서울시 상권분석서비스(추정매출-행정동) | 서울신용보증재단 | 서울특별시 | 2023 | 공공누리 제1유형(출처표시) | [원본 데이터](https://data.seoul.go.kr/dataList/OA-22175/S/1/datasetView.do) |
| 서울시 상권분석서비스(점포-행정동) | 서울신용보증재단 | 서울특별시 | 2023 | 공공누리 제1유형(출처표시) | [원본 데이터](https://data.seoul.go.kr/dataList/OA-22172/S/1/datasetView.do) |
| 서울시 상권분석서비스(영역-행정동) | 서울신용보증재단 | 서울특별시 | 2023 | 공공누리 제1유형(출처표시) | [원본 데이터](https://data.seoul.go.kr/dataList/OA-22160/S/1/datasetView.do) |
| 서울시 지하철 호선별 역별 시간대별 승하차 인원 정보 | 서울특별시 | 서울특별시 | 2015 | 공공누리 제1유형(출처표시) | [원본 데이터](https://data.seoul.go.kr/dataList/OA-12252/S/1/datasetView.do) |
| 서울시 역사마스터 정보 | 서울특별시 | 서울특별시 | 2022 | 공공누리 제1유형(출처표시) | [원본 데이터](https://data.seoul.go.kr/dataList/OA-21232/S/1/datasetView.do) |

※ 공개연도는 원본 데이터 페이지의 공개일자를 기준으로 표시하였습니다.


### 부산 — 부산광역시 Big-데이터웨이브 및 공공데이터포털

| 원본 데이터 | 제공기관 | 출처 |
|---|---|---|
| 일별 행정동 업종(대) 소비매출 월별 일평균 | 부산광역시 Big-데이터웨이브 | [원본 데이터](https://data.busan.go.kr/bdip/opendata/detail.do?publicdatapk=PD_CS00004&uuid=ba3911c5-e5a5-48f5-b0dd-38e3d24a06f8&type=510) |
| SGIS 행정구역 통계 및 경계 | 국가데이터처(SGIS) | [원본 데이터](https://www.data.go.kr/data/15129688/fileData.do) |
| 부산교통공사 도시철도역사정보 | 부산교통공사 | [원본 데이터](https://www.data.go.kr/data/15043686/fileData.do) |
| 일별 역별 시간대별 승하차 | 부산교통공사 | [원본 데이터](https://data.busan.go.kr/bdip/opendata/detail.do?publicdatapk=3057229&uuid=30375f18-7d74-4f60-b1f8-3c2372ef5535) |


## 데이터 이용 안내

- 서울의 `당월_매출_금액`과 부산의 `평균이용금액`은 집계 기준이 달라 직접 비교할 수 없습니다.
- 데이터 제공기관이 본 프로젝트의 가공 결과를 보증하는 것은 아닙니다.