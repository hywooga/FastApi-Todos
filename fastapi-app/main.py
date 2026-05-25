from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import json
import logging
import os
import time
from multiprocessing import Queue
from os import getenv
from prometheus_fastapi_instrumentator import Instrumentator
from logging_loki import LokiQueueHandler

app = FastAPI()

# --- 모니터링 설정 (Prometheus & Loki) ---

# 1. Prometheus 메트릭스 엔드포인트 설정 (/metrics)
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# 2. Loki 로그 핸들러 설정
# getenv를 통해 Docker Compose에 설정된 LOKI_ENDPOINT를 가져옵니다.
loki_url = getenv("LOKI_ENDPOINT", "http://loki:3100/loki/api/v1/push")

loki_logs_handler = LokiQueueHandler(
    Queue(-1),
    url=loki_url,
    tags={"application": "fastapi"},
    version="1",
)

# 3. 커스텀 액세스 로거 설정
custom_logger = logging.getLogger("custom.access")
custom_logger.setLevel(logging.INFO)
custom_logger.addHandler(loki_logs_handler)

# --- 미들웨어 설정 (로그 수집의 핵심) ---

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    모든 HTTP 요청을 가로채서 응답 시간과 상태 코드를 계산하고
    그 결과를 Loki 핸들러가 연결된 로거로 전송합니다.
    """
    start_time = time.time()

    # 다음 프로세스(엔드포인트 함수) 실행
    response = await call_next(request)

    # 응답 시간 계산
    duration = time.time() - start_time

    # 로그 메시지 포맷 구성 (IP - "METHOD PATH HTTP" STATUS DURATION)
    log_message = (
        f'{request.client.host} - "{request.method} {request.url.path} HTTP/1.1" '
        f'{response.status_code} {duration:.3f}s'
    )

    # Loki로 로그 전송
    custom_logger.info(log_message)

    return response

# To-Do 항목 모델
class TodoItem(BaseModel):
    id: int
    title: str
    description: str
    completed: bool
    priority: Optional[str] = "medium"   # high | medium | low
    due_date: Optional[str] = None        # YYYY-MM-DD
    category: Optional[str] = None
    created_at: Optional[str] = None

# JSON 파일 경로
TODO_FILE = "todo.json"

# JSON 파일에서 To-Do 항목 로드
def load_todos():
    if os.path.exists(TODO_FILE):
        with open(TODO_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    return []

# JSON 파일에 To-Do 항목 저장
def save_todos(todos):
    with open(TODO_FILE, "w", encoding="utf-8") as file:
        json.dump(todos, file, indent=4, ensure_ascii=False)

# To-Do 목록 조회
@app.get("/todos", response_model=list[TodoItem])
def get_todos():
    return load_todos()

# 신규 To-Do 항목 추가
@app.post("/todos", response_model=TodoItem)
def create_todo(todo: TodoItem):
    todos = load_todos()
    todos.append(todo.model_dump())
    save_todos(todos)
    return todo

# To-Do 항목 수정
@app.put("/todos/{todo_id}", response_model=TodoItem, responses={404: {"description": "To-Do item not found"}})
def update_todo(todo_id: int, updated_todo: TodoItem):
    todos = load_todos()
    for todo in todos:
        if todo["id"] == todo_id:
            todo.update(updated_todo.model_dump())
            save_todos(todos)
            return updated_todo
    raise HTTPException(status_code=404, detail="To-Do item not found")

# 완료된 To-Do 항목 일괄 삭제
@app.delete("/todos/completed", response_model=dict)
def delete_completed_todos():
    todos = load_todos()
    remaining = [todo for todo in todos if not todo["completed"]]
    deleted_count = len(todos) - len(remaining)
    save_todos(remaining)
    return {"message": f"완료된 항목 {deleted_count}개가 삭제되었습니다.", "deleted_count": deleted_count}

# To-Do 항목 삭제
@app.delete("/todos/{todo_id}", response_model=dict)
def delete_todo(todo_id: int):
    todos = load_todos()
    todos = [todo for todo in todos if todo["id"] != todo_id]
    save_todos(todos)
    return {"message": "To-Do item deleted"}

# HTML 파일 서빙
@app.get("/", response_class=HTMLResponse)
def read_root():
    with open("templates/index.html", "r", encoding="utf-8") as file:
        content = file.read()
    return HTMLResponse(content=content)

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)