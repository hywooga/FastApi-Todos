import requests
import pytest

BASE_URL = "http://163.239.77.77:1548"

def test_home_page():
    response = requests.get(f"{BASE_URL}/")
    assert response.status_code == 200

def test_get_todos():
    response = requests.get(f"{BASE_URL}/todos")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_todo():
    payload = {"title": "jenkins deployed test", "completed": False}
    response = requests.post(f"{BASE_URL}/todos", json=payload)
    assert response.status_code in [200, 201]

def test_get_todos_after_create():
    response = requests.get(f"{BASE_URL}/todos")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)