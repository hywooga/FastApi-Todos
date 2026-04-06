import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import main as main_module
from fastapi.testclient import TestClient
from main import app, save_todos, load_todos, TodoItem

client = TestClient(app)

# ── 픽스처: 테스트마다 임시 JSON 파일 사용 ──────────────────
@pytest.fixture(autouse=True)
def use_temp_todo_file(tmp_path, monkeypatch):
    temp_file = str(tmp_path / "test_todo.json")
    monkeypatch.setattr(main_module, "TODO_FILE", temp_file)
    yield
    if os.path.exists(temp_file):
        os.remove(temp_file)


# ══════════════════════════════════════════════════════════════
# 1. 데이터 모델 테스트
# ══════════════════════════════════════════════════════════════

class TestTodoItemModel:
    def test_required_fields(self):
        """필수 필드(id, title, description, completed)만으로 생성 가능"""
        todo = TodoItem(id=1, title="제목", description="설명", completed=False)
        assert todo.id == 1
        assert todo.title == "제목"
        assert todo.description == "설명"
        assert todo.completed is False

    def test_optional_field_defaults(self):
        """선택 필드 기본값 확인"""
        todo = TodoItem(id=1, title="제목", description="설명", completed=False)
        assert todo.priority == "medium"
        assert todo.due_date is None
        assert todo.category is None
        assert todo.created_at is None

    def test_all_fields(self):
        """모든 필드 설정 가능"""
        todo = TodoItem(
            id=1,
            title="전체 필드",
            description="설명",
            completed=False,
            priority="high",
            due_date="2025-12-31",
            category="업무",
            created_at="2025-01-01T00:00:00"
        )
        assert todo.priority == "high"
        assert todo.due_date == "2025-12-31"
        assert todo.category == "업무"
        assert todo.created_at == "2025-01-01T00:00:00"

    def test_priority_values(self):
        """우선순위 high / medium / low 모두 허용"""
        for p in ["high", "medium", "low"]:
            todo = TodoItem(id=1, title="t", description="d", completed=False, priority=p)
            assert todo.priority == p

    def test_missing_required_title(self):
        """title 누락 시 ValidationError"""
        with pytest.raises(Exception):
            TodoItem(id=1, description="설명", completed=False)

    def test_missing_required_description(self):
        """description 누락 시 ValidationError"""
        with pytest.raises(Exception):
            TodoItem(id=1, title="제목", completed=False)

    def test_id_must_be_int(self):
        """id에 문자열 전달 시 ValidationError"""
        with pytest.raises(Exception):
            TodoItem(id="abc", title="제목", description="설명", completed=False)

    def test_completed_string_coerced_to_bool(self):
        """Pydantic V2는 'yes' 같은 문자열을 bool로 자동 변환함"""
        todo = TodoItem(id=1, title="제목", description="설명", completed="yes")
        assert isinstance(todo.completed, bool)


# ══════════════════════════════════════════════════════════════
# 2. 상태 관리 테스트 (save_todos / load_todos)
# ══════════════════════════════════════════════════════════════

class TestStateManagement:
    def test_load_todos_when_file_not_exist(self):
        """파일이 없으면 빈 리스트 반환"""
        result = load_todos()
        assert result == []

    def test_save_and_load_single_todo(self):
        """단일 항목 저장 후 동일하게 로드"""
        data = [{"id": 1, "title": "저장테스트", "description": "설명",
                 "completed": False, "priority": "medium",
                 "due_date": None, "category": None, "created_at": None}]
        save_todos(data)
        loaded = load_todos()
        assert loaded == data

    def test_save_and_load_multiple_todos(self):
        """여러 항목 저장/로드"""
        data = [
            {"id": 1, "title": "항목1", "description": "설명1",
             "completed": False, "priority": "high",
             "due_date": None, "category": None, "created_at": None},
            {"id": 2, "title": "항목2", "description": "설명2",
             "completed": True, "priority": "low",
             "due_date": "2025-06-01", "category": "개인", "created_at": None},
        ]
        save_todos(data)
        loaded = load_todos()
        assert len(loaded) == 2
        assert loaded[0]["title"] == "항목1"
        assert loaded[1]["category"] == "개인"

    def test_save_empty_list(self):
        """빈 리스트 저장 후 로드"""
        save_todos([])
        assert load_todos() == []

    def test_overwrite_existing_data(self):
        """기존 데이터를 새 데이터로 덮어쓰기"""
        save_todos([{"id": 1, "title": "구버전", "description": "",
                     "completed": False, "priority": "medium",
                     "due_date": None, "category": None, "created_at": None}])
        save_todos([{"id": 2, "title": "신버전", "description": "",
                     "completed": True, "priority": "low",
                     "due_date": None, "category": None, "created_at": None}])
        loaded = load_todos()
        assert len(loaded) == 1
        assert loaded[0]["title"] == "신버전"

    def test_korean_characters_saved_correctly(self):
        """한글 데이터 저장/로드 시 깨지지 않음"""
        data = [{"id": 1, "title": "한글제목", "description": "한글설명",
                 "completed": False, "priority": "medium",
                 "due_date": None, "category": "카테고리", "created_at": None}]
        save_todos(data)
        loaded = load_todos()
        assert loaded[0]["title"] == "한글제목"
        assert loaded[0]["category"] == "카테고리"


# ══════════════════════════════════════════════════════════════
# 3. API CRUD 테스트
# ══════════════════════════════════════════════════════════════

# ── GET /todos ───────────────────────────────────────────────
class TestGetTodos:
    def test_get_empty_list(self):
        response = client.get("/todos")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_todos_returns_all(self):
        save_todos([
            {"id": 1, "title": "A", "description": "", "completed": False,
             "priority": "medium", "due_date": None, "category": None, "created_at": None},
            {"id": 2, "title": "B", "description": "", "completed": True,
             "priority": "low", "due_date": None, "category": None, "created_at": None},
        ])
        response = client.get("/todos")
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_get_todos_field_integrity(self):
        """반환된 항목의 필드 구조 확인"""
        save_todos([{"id": 1, "title": "필드확인", "description": "desc",
                     "completed": False, "priority": "high",
                     "due_date": "2025-12-31", "category": "업무", "created_at": None}])
        data = client.get("/todos").json()[0]
        assert data["id"] == 1
        assert data["priority"] == "high"
        assert data["due_date"] == "2025-12-31"
        assert data["category"] == "업무"


# ── POST /todos ──────────────────────────────────────────────
class TestCreateTodo:
    def test_create_basic_todo(self):
        payload = {"id": 1, "title": "새 할 일", "description": "설명",
                   "completed": False}
        response = client.post("/todos", json=payload)
        assert response.status_code == 200
        assert response.json()["title"] == "새 할 일"

    def test_create_todo_with_all_fields(self):
        payload = {"id": 2, "title": "전체필드", "description": "설명",
                   "completed": False, "priority": "high",
                   "due_date": "2025-12-31", "category": "업무",
                   "created_at": "2025-01-01T00:00:00"}
        response = client.post("/todos", json=payload)
        assert response.status_code == 200
        body = response.json()
        assert body["priority"] == "high"
        assert body["due_date"] == "2025-12-31"
        assert body["category"] == "업무"

    def test_create_todo_persisted(self):
        """생성 후 GET으로 조회 가능한지 확인"""
        payload = {"id": 3, "title": "저장확인", "description": "",
                   "completed": False}
        client.post("/todos", json=payload)
        todos = client.get("/todos").json()
        assert any(t["id"] == 3 for t in todos)

    def test_create_todo_missing_title(self):
        """title 누락 → 422"""
        payload = {"id": 1, "description": "설명", "completed": False}
        response = client.post("/todos", json=payload)
        assert response.status_code == 422

    def test_create_todo_missing_description(self):
        """description 누락 → 422"""
        payload = {"id": 1, "title": "제목", "completed": False}
        response = client.post("/todos", json=payload)
        assert response.status_code == 422

    def test_create_todo_missing_completed(self):
        """completed 누락 → 422"""
        payload = {"id": 1, "title": "제목", "description": "설명"}
        response = client.post("/todos", json=payload)
        assert response.status_code == 422

    def test_create_todo_invalid_id_type(self):
        """id에 문자열 → 422"""
        payload = {"id": "abc", "title": "제목", "description": "설명",
                   "completed": False}
        response = client.post("/todos", json=payload)
        assert response.status_code == 422

    def test_create_multiple_todos(self):
        """여러 항목 연속 생성"""
        for i in range(1, 4):
            client.post("/todos", json={"id": i, "title": f"항목{i}",
                                        "description": "", "completed": False})
        assert len(client.get("/todos").json()) == 3


# ── PUT /todos/{id} ──────────────────────────────────────────
class TestUpdateTodo:
    def test_update_title(self):
        save_todos([{"id": 1, "title": "원본", "description": "",
                     "completed": False, "priority": "medium",
                     "due_date": None, "category": None, "created_at": None}])
        payload = {"id": 1, "title": "수정됨", "description": "",
                   "completed": False, "priority": "medium",
                   "due_date": None, "category": None, "created_at": None}
        response = client.put("/todos/1", json=payload)
        assert response.status_code == 200
        assert response.json()["title"] == "수정됨"

    def test_update_completed_status(self):
        """미완료 → 완료로 상태 변경"""
        save_todos([{"id": 1, "title": "테스트", "description": "",
                     "completed": False, "priority": "medium",
                     "due_date": None, "category": None, "created_at": None}])
        payload = {"id": 1, "title": "테스트", "description": "",
                   "completed": True, "priority": "medium",
                   "due_date": None, "category": None, "created_at": None}
        response = client.put("/todos/1", json=payload)
        assert response.status_code == 200
        assert response.json()["completed"] is True

    def test_update_priority(self):
        save_todos([{"id": 1, "title": "우선순위", "description": "",
                     "completed": False, "priority": "low",
                     "due_date": None, "category": None, "created_at": None}])
        payload = {"id": 1, "title": "우선순위", "description": "",
                   "completed": False, "priority": "high",
                   "due_date": None, "category": None, "created_at": None}
        response = client.put("/todos/1", json=payload)
        assert response.status_code == 200
        assert response.json()["priority"] == "high"

    def test_update_persisted(self):
        """수정 후 GET으로 변경사항 반영 확인"""
        save_todos([{"id": 1, "title": "원본", "description": "",
                     "completed": False, "priority": "medium",
                     "due_date": None, "category": None, "created_at": None}])
        client.put("/todos/1", json={"id": 1, "title": "수정후", "description": "",
                                     "completed": False, "priority": "medium",
                                     "due_date": None, "category": None, "created_at": None})
        todos = client.get("/todos").json()
        assert todos[0]["title"] == "수정후"

    def test_update_not_found(self):
        """존재하지 않는 id → 404"""
        payload = {"id": 999, "title": "없음", "description": "",
                   "completed": False, "priority": "medium",
                   "due_date": None, "category": None, "created_at": None}
        response = client.put("/todos/999", json=payload)
        assert response.status_code == 404

    def test_update_missing_required_field(self):
        """수정 시 필수 필드 누락 → 422"""
        save_todos([{"id": 1, "title": "제목", "description": "",
                     "completed": False, "priority": "medium",
                     "due_date": None, "category": None, "created_at": None}])
        response = client.put("/todos/1", json={"id": 1, "title": "제목"})
        assert response.status_code == 422


# ── DELETE /todos/{id} ───────────────────────────────────────
class TestDeleteTodo:
    def test_delete_existing_todo(self):
        save_todos([{"id": 1, "title": "삭제할항목", "description": "",
                     "completed": False, "priority": "medium",
                     "due_date": None, "category": None, "created_at": None}])
        response = client.delete("/todos/1")
        assert response.status_code == 200
        assert response.json()["message"] == "To-Do item deleted"

    def test_delete_actually_removes_item(self):
        """삭제 후 GET에서 해당 항목 없음 확인"""
        save_todos([{"id": 1, "title": "삭제대상", "description": "",
                     "completed": False, "priority": "medium",
                     "due_date": None, "category": None, "created_at": None}])
        client.delete("/todos/1")
        todos = client.get("/todos").json()
        assert all(t["id"] != 1 for t in todos)

    def test_delete_one_of_multiple(self):
        """여러 항목 중 하나만 삭제"""
        save_todos([
            {"id": 1, "title": "남길항목", "description": "", "completed": False,
             "priority": "medium", "due_date": None, "category": None, "created_at": None},
            {"id": 2, "title": "삭제항목", "description": "", "completed": False,
             "priority": "medium", "due_date": None, "category": None, "created_at": None},
        ])
        client.delete("/todos/2")
        todos = client.get("/todos").json()
        assert len(todos) == 1
        assert todos[0]["id"] == 1

    def test_delete_nonexistent_returns_200(self):
        """존재하지 않는 id 삭제는 200 반환 (현재 API 동작)"""
        response = client.delete("/todos/999")
        assert response.status_code == 200
        assert response.json()["message"] == "To-Do item deleted"


# ══════════════════════════════════════════════════════════════
# 4. 유효성 검사 테스트
# ══════════════════════════════════════════════════════════════

class TestValidation:
    def test_empty_title_allowed(self):
        """빈 문자열 title은 API에서 허용됨 (모델 레벨 제약 없음)"""
        payload = {"id": 1, "title": "", "description": "", "completed": False}
        response = client.post("/todos", json=payload)
        assert response.status_code == 200

    def test_due_date_format_stored_as_string(self):
        """due_date는 문자열로 저장됨"""
        payload = {"id": 1, "title": "날짜테스트", "description": "",
                   "completed": False, "due_date": "2025-06-15"}
        response = client.post("/todos", json=payload)
        assert response.status_code == 200
        assert response.json()["due_date"] == "2025-06-15"

    def test_create_without_optional_fields_uses_defaults(self):
        """선택 필드 없이 생성 시 기본값 적용"""
        payload = {"id": 1, "title": "기본값확인", "description": "", "completed": False}
        response = client.post("/todos", json=payload)
        body = response.json()
        assert body["priority"] == "medium"
        assert body["due_date"] is None
        assert body["category"] is None

    def test_completed_false_to_true_via_update(self):
        """완료 상태 토글: False → True → False"""
        save_todos([{"id": 1, "title": "토글", "description": "",
                     "completed": False, "priority": "medium",
                     "due_date": None, "category": None, "created_at": None}])
        base = {"id": 1, "title": "토글", "description": "",
                "priority": "medium", "due_date": None,
                "category": None, "created_at": None}

        client.put("/todos/1", json={**base, "completed": True})
        assert client.get("/todos").json()[0]["completed"] is True

        client.put("/todos/1", json={**base, "completed": False})
        assert client.get("/todos").json()[0]["completed"] is False

    def test_category_and_due_date_can_be_updated_to_none(self):
        """category, due_date를 None으로 업데이트 가능"""
        save_todos([{"id": 1, "title": "수정", "description": "",
                     "completed": False, "priority": "medium",
                     "due_date": "2025-01-01", "category": "업무", "created_at": None}])
        payload = {"id": 1, "title": "수정", "description": "",
                   "completed": False, "priority": "medium",
                   "due_date": None, "category": None, "created_at": None}
        response = client.put("/todos/1", json=payload)
        assert response.status_code == 200
        body = response.json()
        assert body["due_date"] is None
        assert body["category"] is None
