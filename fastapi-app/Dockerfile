# Python 3.9 베이스 이미지 사용
FROM python:3.9

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 파일 복사
COPY . .

# 의존성 설치 및 보안: 비root 사용자 생성 후 파일 소유권 이전
RUN pip install --no-cache-dir -r requirements.txt && \
    useradd -m appuser && \
    chown -R appuser:appuser /app
USER appuser

# FastAPI 서버 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]