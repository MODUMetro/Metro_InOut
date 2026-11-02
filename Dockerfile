# 베이스 이미지
FROM python:3.12-slim

# 작업 디렉터리 설정
WORKDIR /app

# 필수 패키지 설치 및 캐시 정리 (빌드 최적화)
ENV TZ=Asia/Seoul
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    gcc \
    g++ \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 애플리케이션 전체 소스 코드 복사
COPY . .

# 기본 포트 노출
EXPOSE 8501

# 헬스체크 설정 (컨테이너 정상 동작 여부 모니터링)
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# 실행 명령어 (헤드리스 모드 및 외부 접속 허용)
ENTRYPOINT ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]