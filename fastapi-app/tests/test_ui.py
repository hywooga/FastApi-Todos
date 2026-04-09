import pytest
import requests
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:1548"

# ── 테스트용 todo 사전/사후 정리 ─────────────────────────────
@pytest.fixture(autouse=True)
def cleanup_test_todo():
    requests.delete(f"{BASE_URL}/todos/8888")
    yield
    requests.delete(f"{BASE_URL}/todos/8888")

def make_todo(id=8888, title="테스트 할 일", completed=False, priority="medium", category=None):
    """API로 테스트용 todo 생성"""
    res = requests.post(f"{BASE_URL}/todos", json={
        "id": id,
        "title": title,
        "description": "",
        "completed": completed,
        "priority": priority,
        "due_date": None,
        "category": category,
        "created_at": None
    })
    assert res.status_code == 200, f"make_todo 실패: {res.status_code} {res.text}"


def goto(page: Page):
    """페이지 이동 후 fetchTodos() 완료까지 대기"""
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")


# ══════════════════════════════════════════════════════════════
# 1. 페이지 로드
# ══════════════════════════════════════════════════════════════

def test_page_title(page: Page):
    goto(page)
    expect(page).to_have_title("TODO List")

def test_header_visible(page: Page):
    goto(page)
    expect(page.locator(".header h1")).to_contain_text("TODO List")

def test_add_form_visible(page: Page):
    goto(page)
    expect(page.locator("#todo-form")).to_be_visible()

def test_progress_bar_visible(page: Page):
    goto(page)
    expect(page.locator(".progress-wrap")).to_be_visible()

def test_filter_buttons_visible(page: Page):
    goto(page)
    expect(page.locator(".filter-btn")).to_have_count(4)


# ══════════════════════════════════════════════════════════════
# 2. 할 일 추가
# ══════════════════════════════════════════════════════════════

def test_add_todo(page: Page):
    goto(page)
    page.fill("#title", "UI테스트 할 일")
    with page.expect_response(
        lambda r: "/todos" in r.url and r.request.method == "POST"
    ) as resp_info:
        page.click("button[type='submit']")
    assert resp_info.value.status == 200, f"POST /todos 실패: {resp_info.value.status}"
    page.wait_for_timeout(500)
    expect(page.locator(".todo-title").first).to_contain_text("UI테스트 할 일", timeout=10000)

def test_add_todo_with_priority(page: Page):
    goto(page)
    page.fill("#title", "긴급 할 일")
    page.select_option("#priority", "high")
    with page.expect_response(
        lambda r: "/todos" in r.url and r.request.method == "POST"
    ) as resp_info:
        page.click("button[type='submit']")
    assert resp_info.value.status == 200, f"POST /todos 실패: {resp_info.value.status}"
    page.wait_for_timeout(500)
    expect(page.locator(".priority-high").first).to_be_visible(timeout=10000)

def test_add_todo_with_category(page: Page):
    goto(page)
    page.fill("#title", "카테고리 테스트")
    page.fill("#category", "업무")
    with page.expect_response(
        lambda r: "/todos" in r.url and r.request.method == "POST"
    ) as resp_info:
        page.click("button[type='submit']")
    assert resp_info.value.status == 200, f"POST /todos 실패: {resp_info.value.status}"
    page.wait_for_timeout(500)
    expect(page.locator(".badge-category").first).to_contain_text("업무", timeout=10000)

def test_form_clears_after_submit(page: Page):
    goto(page)
    page.fill("#title", "초기화 확인")
    with page.expect_response(
        lambda r: "/todos" in r.url and r.request.method == "POST"
    ) as resp_info:
        page.click("button[type='submit']")
    assert resp_info.value.status == 200, f"POST /todos 실패: {resp_info.value.status}"
    page.wait_for_timeout(500)
    expect(page.locator("#title")).to_have_value("", timeout=10000)

def test_add_todo_missing_title(page: Page):
    goto(page)
    initial_count = page.locator(".todo-card").count()
    page.click("button[type='submit']")
    page.wait_for_timeout(1000)
    assert page.locator(".todo-card").count() == initial_count


# ══════════════════════════════════════════════════════════════
# 3. 완료 토글
# ══════════════════════════════════════════════════════════════

def test_toggle_complete(page: Page):
    make_todo(title="완료 토글 테스트")
    goto(page)
    page.wait_for_selector(".todo-checkbox", timeout=10000)
    page.locator(".todo-checkbox").first.click()
    expect(page.locator(".todo-card").first).to_have_class("completed", timeout=10000)

def test_toggle_complete_shows_badge(page: Page):
    make_todo(title="완료 배지 확인")
    goto(page)
    page.wait_for_selector(".todo-checkbox", timeout=10000)
    page.locator(".todo-checkbox").first.click()
    expect(page.locator(".badge-done").first).to_be_visible(timeout=10000)

def test_progress_bar_updates(page: Page):
    make_todo(title="진행바 테스트")
    goto(page)
    page.wait_for_selector(".todo-checkbox", timeout=10000)
    page.locator(".todo-checkbox").first.click()
    expect(page.locator("#progress-label")).to_contain_text("%", timeout=10000)


# ══════════════════════════════════════════════════════════════
# 4. 삭제
# ══════════════════════════════════════════════════════════════

def test_delete_todo(page: Page):
    make_todo(title="삭제 테스트")
    goto(page)
    page.wait_for_selector(".btn-danger", timeout=10000)
    page.on("dialog", lambda d: d.accept())
    page.locator(".btn-danger").first.click()
    expect(page.locator(".todo-title")).not_to_contain_text("삭제 테스트", timeout=10000)

def test_delete_cancel(page: Page):
    make_todo(title="삭제 취소 테스트")
    goto(page)
    page.wait_for_selector(".btn-danger", timeout=10000)
    page.on("dialog", lambda d: d.dismiss())
    page.locator(".btn-danger").first.click()
    expect(page.locator(".todo-title").first).to_contain_text("삭제 취소 테스트", timeout=10000)


# ══════════════════════════════════════════════════════════════
# 5. 검색
# ══════════════════════════════════════════════════════════════

def test_search_filters_results(page: Page):
    make_todo(title="검색용 항목")
    goto(page)
    page.wait_for_selector(".todo-card", timeout=10000)
    page.fill("#search", "검색용")
    page.wait_for_timeout(500)
    expect(page.locator(".todo-card")).to_have_count(1, timeout=5000)

def test_search_no_results(page: Page):
    goto(page)
    page.fill("#search", "절대없는검색어zzz")
    expect(page.locator(".empty-state")).to_be_visible(timeout=5000)

def test_search_clear_restores(page: Page):
    make_todo(title="복원 테스트")
    goto(page)
    page.wait_for_selector(".todo-card", timeout=10000)
    page.fill("#search", "복원")
    page.wait_for_timeout(300)
    page.fill("#search", "")
    page.wait_for_timeout(300)
    assert page.locator(".todo-card").count() >= 1


# ══════════════════════════════════════════════════════════════
# 6. 필터
# ══════════════════════════════════════════════════════════════

def test_filter_active(page: Page):
    make_todo(title="미완료 항목")
    goto(page)
    page.wait_for_selector(".filter-btn", timeout=10000)
    page.get_by_role("button", name="미완료").click()
    page.wait_for_timeout(500)
    cards = page.locator(".todo-card")
    for i in range(cards.count()):
        expect(cards.nth(i)).not_to_have_class("completed")

def test_filter_completed(page: Page):
    make_todo(title="완료된 항목", completed=True)
    goto(page)
    page.wait_for_selector(".filter-btn", timeout=10000)
    page.get_by_role("button", name="완료", exact=True).click()
    page.wait_for_timeout(500)
    empty = page.locator(".empty-state")
    cards = page.locator(".todo-card")
    assert empty.is_visible() or cards.count() >= 1

def test_filter_all_active_by_default(page: Page):
    goto(page)
    expect(page.locator(".filter-btn.active")).to_contain_text("전체")


# ══════════════════════════════════════════════════════════════
# 7. 인라인 수정
# ══════════════════════════════════════════════════════════════

def test_edit_form_opens(page: Page):
    make_todo(title="수정 테스트")
    goto(page)
    page.wait_for_selector(".btn-secondary", timeout=10000)
    page.get_by_role("button", name="수정").first.click()
    expect(page.locator(".edit-form.open").first).to_be_visible(timeout=5000)

def test_edit_cancel_closes_form(page: Page):
    make_todo(title="취소 테스트")
    goto(page)
    page.wait_for_selector(".btn-secondary", timeout=10000)
    page.get_by_role("button", name="수정").first.click()
    page.wait_for_selector(".edit-form.open", timeout=5000)
    page.locator(".edit-form.open .btn-secondary").first.click()
    expect(page.locator(".edit-form.open")).to_have_count(0, timeout=5000)


# ══════════════════════════════════════════════════════════════
# 8. 다크 모드
# ══════════════════════════════════════════════════════════════

def test_dark_mode_toggle(page: Page):
    goto(page)
    page.click("#dark-toggle")
    expect(page.locator("body")).to_have_class("dark")

def test_dark_mode_button_text_changes(page: Page):
    goto(page)
    page.click("#dark-toggle")
    expect(page.locator("#dark-toggle")).to_contain_text("라이트모드")

def test_dark_mode_toggle_back(page: Page):
    goto(page)
    page.click("#dark-toggle")
    page.click("#dark-toggle")
    classes = page.locator("body").get_attribute("class") or ""
    assert "dark" not in classes
