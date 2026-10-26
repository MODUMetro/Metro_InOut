# setting_DB.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# .env 파일 내의 변수들을 활성화
load_dotenv()

# DB 엔진 생성
engine = create_engine(os.getenv("DB_URL"))


# 테이블 초기화 함수
def init_db():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS consultations (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50),
                phone VARCHAR(11) CHECK (phone ~ '^[0-9]{10,11}$'),
                location VARCHAR(100),
                category VARCHAR(50),
                purpose TEXT,
                created_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Seoul')
            )
        """))
        conn.commit()