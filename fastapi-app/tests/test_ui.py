import pytest
import requests
from playwright.sync_api import Page, expect

BASE_URL = "http://163.239.77.77:1548"

# ── 테스트 전 서버 상태 초기화 ──────────────────────────────
@pytest.fixture(autouse=True)
def cleanup_test_todo():
    """테스트용 todo(id=8888) 사전/사후 정리"""
    requests.delete(f"{BASE_URL}/todos/8888")
    yield
    requests.delete(f"{BASE_URL}/todos/8888")


# ══════════════════════════════════════════════════════════════
# 1. 페이지 로드
# ══════════════════════════════════════════════════════════════

def test_page_title(page: Page):
    """페이지 타이틀 확인"""
    page.goto(BASE_URL)
    expect(page).to_have_title("TODO List")

def test_header_visible(page: Page):
    """헤더 h1 텍스트 확인"""
    page.goto(BASE_URL)
    expect(page.locator(".header h1")).to_contain_text("TODO List")

def test_add_form_visible(page: Page):
    """할 일 추가 폼 표시 확인"""
    page.goto(BASE_URL)
    expect(page.locator("#todo-form")).to_be_visible()

def test_progress_bar_visible(page: Page):
    """진행바 영역 표시 확인"""
    page.goto(BASE_URL)
    expect(page.locator(".progress-wrap")).to_be_visible()

def test_filter_buttons_visible(page: Page):
    """필터 버튼(전체/미완료/완료/기한초과) 모두 표시"""
    page.goto(BASE_URL)
    expect(page.locator(".filter-btn")).to_have_count(4)


# ══════════════════════════════════════════════════════════════
# 2. 할 일 추가
# ══════════════════════════════════════════════════════════════

def test_add_todo(page: Page):
    """제목 입력 후 추가 버튼 클릭 시 카드 생성"""
    page.goto(BASE_URL)
    page.fill("#title", "UI테스트 할 일")
    page.click("button[type='submit']")
    expect(page.locator(".todo-title").first).to_contain_text("UI테스트 할 일")

def test_add_todo_with_priority(page: Page):
    """우선순위 높음으로 추가 시 red border 카드 생성"""
    page.goto(BASE_URL)
    page.fill("#title", "긴급 할 일")
    page.select_option("#priority", "high")
    page.click("button[type='submit']")
    expect(page.locator(".priority-high").first).to_be_visible()

def test_add_todo_with_category(page: Page):
    """카테고리 입력 시 배지 표시"""
    page.goto(BASE_URL)
    page.fill("#title", "카테고리 테스트")
    page.fill("#category", "업무")
    page.click("button[type='submit']")
    expect(page.locator(".badge-category").first).to_contain_text("업무")

def test_form_clears_after_submit(page: Page):
    """추가 후 입력 폼 초기화 확인"""
    page.goto(BASE_URL)
    page.fill("#title", "초기화 확인")
    page.click("button[type='submit']")
    expect(page.locator("#title")).to_have_value("")

def test_add_todo_missing_title(page: Page):
    """제목 없이 제출 시 추가되지 않음 (required 속성)"""
    page.goto(BASE_URL)
    initial_count = page.locator(".todo-card").count()
    page.click("button[type='submit']")
    assert page.locator(".todo-card").count() == initial_count


# ══════════════════════════════════════════════════════════════
# 3. 완료 토글
# ══════════════════════════════════════════════════════════════

def test_toggle_complete(page: Page):
    """체크박스 클릭 시 completed 클래스 적용"""
    page.goto(BASE_URL)
    page.fill("#title", "완료 토글 테스트")
    page.click("button[type='submit']")
    page.locator(".todo-checkbox").first.click()
    expect(page.locator(".todo-card").first).to_have_class("completed")

def test_toggle_complete_shows_badge(page: Page):
    """완료 처리 시 ✅ 완료 배지 표시"""
    page.goto(BASE_URL)
    page.fill("#title", "완료 배지 확인")
    page.click("button[type='submit']")
    page.locator(".todo-checkbox").first.click()
    expect(page.locator(".badge-done").first).to_be_visible()

def test_progress_bar_updates(page: Page):
    """완료 토글 시 완료율 레이블 업데이트"""
    page.goto(BASE_URL)
    page.fill("#title", "진행바 테스트")
    page.click("button[type='submit']")
    page.locator(".todo-checkbox").first.click()
    expect(page.locator("#progress-label")).to_contain_text("%")


# ══════════════════════════════════════════════════════════════
# 4. 삭제
# ══════════════════════════════════════════════════════════════

def test_delete_todo(page: Page):
    """삭제 버튼 클릭 후 confirm 승인 시 카드 제거"""
    page.goto(BASE_URL)
    page.fill("#title", "삭제 테스트")
    page.click("button[type='submit']")
    page.on("dialog", lambda d: d.accept())
    page.locator(".btn-danger").first.click()
    expect(page.locator(".todo-title")).not_to_contain_text("삭제 테스트")

def test_delete_cancel(page: Page):
    """삭제 confirm 취소 시 카드 유지"""
    page.goto(BASE_URL)
    page.fill("#title", "삭제 취소 테스트")
    page.click("button[type='submit']")
    page.on("dialog", lambda d: d.dismiss())
    page.locator(".btn-danger").first.click()
    expect(page.locator(".todo-title").first).to_contain_text("삭제 취소 테스트")


# ══════════════════════════════════════════════════════════════
# 5. 검색
# ══════════════════════════════════════════════════════════════

def test_search_filters_results(page: Page):
    """검색어 입력 시 일치하는 항목만 표시"""
    page.goto(BASE_URL)
    page.fill("#title", "검색용 항목")
    page.click("button[type='submit']")
    page.fill("#search", "검색용")
    expect(page.locator(".todo-card")).to_have_count(1)

def test_search_no_results(page: Page):
    """검색 결과 없을 때 empty-state 표시"""
    page.goto(BASE_URL)
    page.fill("#search", "절대없는검색어zzz")
    expect(page.locator(".empty-state")).to_be_visible()

def test_search_clear_restores(page: Page):
    """검색어 지우면 전체 목록 복원"""
    page.goto(BASE_URL)
    page.fill("#title", "복원 테스트")
    page.click("button[type='submit']")
    page.fill("#search", "복원")
    page.fill("#search", "")
    count = page.locator(".todo-card").count()
    assert count >= 1


# ══════════════════════════════════════════════════════════════
# 6. 필터
# ══════════════════════════════════════════════════════════════

def test_filter_active(page: Page):
    """미완료 필터 클릭 시 완료 항목 숨김"""
    page.goto(BASE_URL)
    page.fill("#title", "미완료 항목")
    page.click("button[type='submit']")
    page.locator(".filter-btn", has_text="미완료").click()
    cards = page.locator(".todo-card")
    for i in range(cards.count()):
        expect(cards.nth(i)).not_to_have_class("completed")

def test_filter_completed(page: Page):
    """완료 필터: 항목 없으면 empty-state 표시"""
    page.goto(BASE_URL)
    page.locator(".filter-btn", has_text="완료").click()
    # 완료 항목이 없으면 empty-state, 있으면 카드 표시
    empty = page.locator(".empty-state")
    cards = page.locator(".todo-card")
    assert empty.is_visible() or cards.count() >= 1

def test_filter_all_active_by_default(page: Page):
    """기본 필터는 '전체' 버튼이 active"""
    page.goto(BASE_URL)
    expect(page.locator(".filter-btn.active")).to_contain_text("전체")


# ══════════════════════════════════════════════════════════════
# 7. 인라인 수정
# ══════════════════════════════════════════════════════════════

def test_edit_form_opens(page: Page):
    """수정 버튼 클릭 시 인라인 폼 열림"""
    page.goto(BASE_URL)
    page.fill("#title", "수정 테스트")
    page.click("button[type='submit']")
    page.locator(".btn-secondary", has_text="수정").first.click()
    expect(page.locator(".edit-form.open").first).to_be_visible()

def test_edit_cancel_closes_form(page: Page):
    """취소 버튼 클릭 시 인라인 폼 닫힘"""
    page.goto(BASE_URL)
    page.fill("#title", "취소 테스트")
    page.click("button[type='submit']")
    page.locator(".btn-secondary", has_text="수정").first.click()
    page.locator(".edit-form.open .btn-secondary").first.click()
    expect(page.locator(".edit-form.open")).to_have_count(0)


# ══════════════════════════════════════════════════════════════
# 8. 다크 모드
# ══════════════════════════════════════════════════════════════

def test_dark_mode_toggle(page: Page):
    """다크모드 버튼 클릭 시 body에 dark 클래스 추가"""
    page.goto(BASE_URL)
    page.click("#dark-toggle")
    expect(page.locator("body")).to_have_class("dark")

def test_dark_mode_button_text_changes(page: Page):
    """다크모드 버튼 텍스트 전환 확인"""
    page.goto(BASE_URL)
    page.click("#dark-toggle")
    expect(page.locator("#dark-toggle")).to_contain_text("라이트모드")

def test_dark_mode_toggle_back(page: Page):
    """라이트모드로 다시 전환 시 dark 클래스 제거"""
    page.goto(BASE_URL)
    page.click("#dark-toggle")
    page.click("#dark-toggle")
    classes = page.locator("body").get_attribute("class") or ""
    assert "dark" not in classes
