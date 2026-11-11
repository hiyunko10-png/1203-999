"""오늘 딱 3개 | 실행: streamlit run app.py
GitHub 저장소에 app.py, requirements.txt를 올린 뒤 Streamlit Community Cloud에서 배포.
로컬 SQLite는 배포 서버 재시작/재배포 시 유실될 수 있으므로 JSON 백업을 권장합니다.
개인 작업공간 URL은 접근키 역할을 합니다. 민감한 정보는 입력하지 마세요.
"""
import copy
import json
import os
import secrets
import sqlite3
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

st.set_page_config(page_title="오늘 딱 3개", page_icon="🌿", layout="wide", initial_sidebar_state="expanded")
KST = ZoneInfo("Asia/Seoul")
DB_PATH = os.environ.get("TODAY3_DB_PATH", "today3.sqlite3")


def today():
    return datetime.now(KST).date().isoformat()


def empty_data():
    return {"version": 1, "tasks": [], "days": {}}


def validate_data(data):
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("지원하지 않는 백업 형식입니다.")
    tasks, days = data.get("tasks"), data.get("days")
    if not isinstance(tasks, list) or not isinstance(days, dict) or len(tasks) > 10000:
        raise ValueError("백업 구조 또는 크기를 확인해주세요.")
    ids = set()
    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError("잘못된 할 일입니다.")
        tid = task.get("id")
        if not isinstance(tid, str) or not tid or tid in ids:
            raise ValueError("할 일 식별자가 잘못되었습니다.")
        ids.add(tid)
        if not isinstance(task.get("title"), str) or not 1 <= len(task["title"].strip()) <= 200:
            raise ValueError("할 일 제목은 1~200자여야 합니다.")
        if not isinstance(task.get("archived"), bool):
            raise ValueError("할 일 상태가 잘못되었습니다.")
    for day, picks in days.items():
        datetime.strptime(day, "%Y-%m-%d")
        if not isinstance(picks, list) or len(picks) > 3:
            raise ValueError("하루에 최대 3개까지 선택할 수 있습니다.")
        seen = set()
        for p in picks:
            if not isinstance(p, dict) or p.get("id") not in ids or p["id"] in seen:
                raise ValueError("기록에 잘못된 할 일 식별자가 있습니다.")
            seen.add(p["id"])
            if not isinstance(p.get("done"), bool) or not isinstance(p.get("title"), str):
                raise ValueError("완료 기록 형식이 잘못되었습니다.")
    return data


def load_data(workspace):
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS workspaces (id TEXT PRIMARY KEY, data TEXT NOT NULL)")
        row = conn.execute("SELECT data FROM workspaces WHERE id=?", (workspace,)).fetchone()
    return json.loads(row[0]) if row else empty_data()


def save_data():
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.execute("INSERT INTO workspaces(id,data) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data", (workspace, json.dumps(data, ensure_ascii=False)))
    st.rerun()


st.markdown("""
<style>
:root { --green: #267257; }
.stApp { background: #faf9f5; }
/* Streamlit 기본 사이드바는 데스크톱에서 고정, 모바일에서는 접이식 메뉴입니다. */
section[data-testid="stSidebar"] { background: #edf3eb; position: fixed; top: 0; bottom: 0; height: 100dvh; }
section[data-testid="stSidebar"] > div:first-child { height: 100%; overflow-y: auto; }
.block-container { max-width: 1020px; padding-top: 3rem; padding-bottom: 3rem; }
h1,h2,h3 { color: #234b3d; }
div.stButton > button[kind="primary"], div.stFormSubmitButton > button[kind="primary"] { background: #267257; border-color: #267257; }
div[data-testid="stMetric"] { background: #fff; border: 1px solid #e3e9df; border-radius: 16px; padding: 15px; }
@media(max-width: 768px) { .block-container { padding-top: 2rem; padding-left: 1rem; padding-right: 1rem; } }
</style>
""", unsafe_allow_html=True)

workspace = st.query_params.get("space", "")
if not isinstance(workspace, str) or len(workspace) != 48 or any(c not in "0123456789abcdef" for c in workspace):
    workspace = secrets.token_hex(24)
    st.query_params["space"] = workspace
try:
    data = load_data(workspace)
except (sqlite3.Error, ValueError):
    st.error("저장된 데이터를 읽지 못했습니다. 잠시 후 다시 시도해주세요.")
    st.stop()

date_key = today()
picks = data["days"].get(date_key, [])
with st.sidebar:
    st.title("🌿 오늘 딱 3개")
    st.caption("많이 말고, 중요한 것부터.")
    page = st.radio("기능 메뉴", ["☀️ 오늘", "📋 전체 할 일", "📅 기록", "💾 백업 · 도움말"], label_visibility="collapsed")
    st.divider()
    st.caption(datetime.now(KST).strftime("%Y.%m.%d · 한국 시간"))
    st.write(f"오늘 **{sum(p['done'] for p in picks)} / {len(picks)}** 완료")
    st.caption("이 화면의 주소를 북마크하면 같은 작업공간에 돌아올 수 있어요.")
    st.caption("개인 주소를 공유하면 다른 사람도 기록에 접근할 수 있습니다.")


def add_form(key):
    with st.form(key, clear_on_submit=True):
        title = st.text_input("새 할 일", placeholder="예: 기획서 첫 페이지 작성하기", max_chars=200)
        submit = st.form_submit_button("＋ 할 일 추가", type="primary")
        if submit:
            if not title.strip():
                st.warning("할 일을 입력해주세요.")
            else:
                data["tasks"].append({"id": uuid.uuid4().hex, "title": title.strip(), "archived": False})
                save_data()


if page == "☀️ 오늘":
    st.title("오늘은 딱 3개만")
    st.caption("완료할 수 있을 만큼 작게 정하고, 하나씩 끝내세요.")
    done = sum(p["done"] for p in picks)
    a, b, c = st.columns(3)
    a.metric("오늘 선택", f"{len(picks)} / 3")
    b.metric("완료", f"{done}개")
    c.metric("남은 집중", f"{len(picks) - done}개")
    st.progress(done / len(picks) if picks else 0, text="오늘 선택한 일의 완료율")
    if picks and done == len(picks):
        st.success("오늘 선택한 일을 모두 끝냈어요. 수고하셨습니다! 🌿")
    st.subheader("오늘의 집중 목록")
    if not picks:
        st.info("아래에서 오늘 집중할 일을 최대 3개 선택해보세요.")
    for p in picks:
        with st.container(border=True):
            left, right = st.columns([6, 1])
            value = left.checkbox(p["title"], value=p["done"], key=f"done_{date_key}_{p['id']}")
            if value != p["done"]:
                p["done"] = value
                save_data()
            if right.button("빼기", key=f"remove_{p['id']}", help="오늘 목록에서만 제외합니다."):
                picks.remove(p)
                save_data()
    st.subheader("집중할 일 선택")
    picked_ids = {p["id"] for p in picks}
    available = [t for t in data["tasks"] if not t["archived"] and t["id"] not in picked_ids]
    if available:
        options = {t["id"]: t["title"] for t in available}
        with st.form("pick_form"):
            selected = st.selectbox("할 일", list(options), format_func=lambda x: options[x])
            if st.form_submit_button("오늘 집중 목록에 넣기", disabled=len(picks) >= 3):
                if len(picks) < 3:
                    data["days"].setdefault(date_key, []).append({"id": selected, "title": options[selected], "done": False})
                    save_data()
    else:
        st.caption("선택 가능한 할 일이 없습니다. 새 할 일을 추가해주세요.")
    if len(picks) == 3:
        st.caption("오늘은 3개면 충분해요. 바꾸려면 기존 항목을 먼저 빼주세요.")
    add_form("add_today")

elif page == "📋 전체 할 일":
    st.title("전체 할 일")
    st.caption("오늘 목록에서 제외해도 이곳의 할 일은 남습니다.")
    add_form("add_all")
    search = st.text_input("검색", placeholder="제목 검색")
    include_archived = st.toggle("보관한 할 일도 보기")
    tasks = [t for t in data["tasks"] if (include_archived or not t["archived"]) and search.casefold() in t["title"].casefold()]
    st.caption(f"{len(tasks)}개")
    if not tasks:
        st.info("아직 표시할 할 일이 없습니다.")
    for t in reversed(tasks):
        with st.expander(("📦 " if t["archived"] else "▫️ ") + t["title"]):
            with st.form(f"edit_{t['id']}"):
                new_title = st.text_input("제목", value=t["title"], max_chars=200)
                archived = st.checkbox("보관하기 (새로운 집중 목록에서 숨기기)", value=t["archived"])
                if st.form_submit_button("변경 저장"):
                    if not new_title.strip():
                        st.warning("제목을 입력해주세요.")
                    else:
                        t.update(title=new_title.strip(), archived=archived)
                        # 과거 기록은 당시 제목을 유지하고 오늘 제목만 동기화합니다.
                        for p in picks:
                            if p["id"] == t["id"]:
                                p["title"] = t["title"]
                        save_data()
    st.caption("기록 보호를 위해 영구 삭제 대신 보관을 사용합니다. 오늘의 완료 여부는 날짜별로 관리됩니다.")

elif page == "📅 기록":
    st.title("쌓이는 작은 성취")
    history = sorted(data["days"].items(), reverse=True)
    total = sum(sum(p["done"] for p in items) for _, items in history)
    a, b = st.columns(2)
    a.metric("누적 완료", f"{total}개")
    b.metric("집중한 날", f"{sum(bool(items) for _, items in history)}일")
    if not any(items for _, items in history):
        st.info("오늘의 집중 목록을 선택하면 기록이 시작됩니다.")
    for day, items in history:
        if items:
            count = sum(p["done"] for p in items)
            with st.expander(f"{day} · {count}/{len(items)} 완료", expanded=day == date_key):
                for p in items:
                    st.write(("✅ " if p["done"] else "⬜ ") + p["title"])

else:
    st.title("백업 · 도움말")
    st.warning("Streamlit Community Cloud의 로컬 파일은 영구 저장소가 아닙니다. 재배포·서버 재시작으로 기록이 사라질 수 있으니 정기적으로 백업하세요.")
    st.download_button("JSON 백업 다운로드", json.dumps(data, ensure_ascii=False, indent=2), file_name=f"today3-{date_key}.json", mime="application/json", type="primary")
    uploaded = st.file_uploader("JSON 백업 복원", type=["json"])
    confirmed = st.checkbox("복원하면 현재 작업공간의 기록 전체가 백업 내용으로 교체됨을 확인했습니다.")
    if st.button("백업 복원", disabled=uploaded is None or not confirmed):
        try:
            if uploaded.size > 5 * 1024 * 1024:
                raise ValueError("5MB 이하의 백업만 복원할 수 있습니다.")
            restored = validate_data(json.loads(uploaded.getvalue().decode("utf-8")))
        except (ValueError, TypeError, KeyError, AttributeError, UnicodeDecodeError) as e:
            st.error(f"복원할 수 없습니다: {e}")
        else:
            data = copy.deepcopy(restored)
            save_data()
    st.subheader("사용 방법")
    st.markdown("1. 할 일을 추가합니다.\n2. 오늘 집중할 일을 최대 3개 선택합니다.\n3. 끝낸 일은 체크합니다.\n4. 다음 날에는 새 목록을 선택하고, 지난 결과는 기록에서 확인합니다.")
    st.info("왼쪽 메뉴는 데스크톱에서 고정됩니다. 작은 화면에서는 Streamlit 기본 접이식 사이드바로 표시되며, 왼쪽 위 버튼으로 열 수 있습니다.")
    st.caption("로그인 기능이 없는 개인용 MVP입니다. 작업공간 주소는 접근키이므로 비공개로 보관해주세요. 여러 기기에서 같은 주소로 접근할 수 있지만 동시에 편집하면 마지막 저장 내용이 적용됩니다. 장기 운영 시 인증과 외부 데이터베이스를 연결하세요.")
