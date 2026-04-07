import requests

BASE_URL = "http://163.239.77.77:1548"

def test_home_page():
    response = requests.get(f"{BASE_URL}/")
    assert response.status_code == 200

def test_create_todo():
    payload = {
        "id": 9999,
        "title": "jenkins deployed test",
        "description": "integration test",
        "completed": False,
        "priority": "medium",
        "due_date": None,
        "category": "jenkins",
        "created_at": "2026-04-07"
    }
    response = requests.post(f"{BASE_URL}/todos", json=payload)
    assert response.status_code in [200, 201]

def test_get_todos():
    response = requests.get(f"{BASE_URL}/todos")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_get_todos_after_create():
    response = requests.get(f"{BASE_URL}/todos")
    assert response.status_code == 200
    data = response.json()
    assert any(todo["id"] == 9999 for todo in data)