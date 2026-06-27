#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
無人アイス屋さん高井田店 賞味期限管理 (Streamlit版)
スマホ対応 + 簡易パスワード認証 + 永続JSON保存
"""

import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path

import streamlit as st

# ====================== 設定 ======================
st.set_page_config(
    page_title="高井田店 賞味期限管理",
    page_icon="🍦",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DATE_FORMAT = "%Y-%m-%d"
DISPLAY_FORMAT = "%Y/%m/%d"
DEFAULT_PASSWORD = "takaida2026"


def resolve_data_dir() -> str:
    """Render の永続ディスク (/data) が使えなければローカル data にフォールバック。"""
    preferred = os.getenv("DATA_DIR", "data")
    for candidate in (preferred, "data"):
        try:
            path = Path(candidate)
            path.mkdir(parents=True, exist_ok=True)
            test_file = path / ".write_test"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink(missing_ok=True)
            return str(path)
        except OSError:
            continue
    return "data"


DATA_DIR = resolve_data_dir()
DATA_FILE = os.path.join(DATA_DIR, "products.json")


# ====================== セッション状態 ======================
def init_session_state() -> None:
    defaults = {
        "authenticated": False,
        "products": None,
        "show_add_form": False,
        "editing_id": None,
        "delete_id": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ====================== データ永続化 ======================
def get_sample_data() -> list[dict]:
    today = date.today()
    return [
        {"id": 1, "name": "ガリガリ君 コーラ", "expiry_date": (today + timedelta(days=2)).strftime(DATE_FORMAT)},
        {"id": 2, "name": "ハーゲンダッツ バニラ", "expiry_date": (today - timedelta(days=1)).strftime(DATE_FORMAT)},
        {"id": 3, "name": "アイスの実 マンゴー", "expiry_date": (today + timedelta(days=12)).strftime(DATE_FORMAT)},
        {"id": 4, "name": "雪見だいふく", "expiry_date": (today + timedelta(days=5)).strftime(DATE_FORMAT)},
        {"id": 5, "name": "明治 エッセル スーパーカップ", "expiry_date": (today + timedelta(days=30)).strftime(DATE_FORMAT)},
    ]


def load_data() -> list[dict]:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return normalize_products(data)
        except (json.JSONDecodeError, OSError):
            pass

    samples = get_sample_data()
    save_data(samples)
    return samples


def save_data(products: list[dict]) -> None:
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)


def normalize_products(products: list) -> list[dict]:
    normalized = []
    for index, item in enumerate(products, start=1):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        expiry = parse_date_input(item.get("expiry_date", ""))
        if not name or not expiry:
            continue
        try:
            product_id = int(item.get("id", index))
        except (TypeError, ValueError):
            product_id = index
        normalized.append({"id": product_id, "name": name, "expiry_date": expiry})
    return normalized


def get_next_id(products: list[dict]) -> int:
    if not products:
        return 1
    ids = []
    for product in products:
        try:
            ids.append(int(product.get("id", 0)))
        except (TypeError, ValueError):
            continue
    return max(ids, default=0) + 1


# ====================== 日付・状態 ======================
def parse_date_input(value) -> str | None:
    """文字列・date・datetime を内部形式 (YYYY-MM-DD) に正規化。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().strftime(DATE_FORMAT)
    if isinstance(value, date):
        return value.strftime(DATE_FORMAT)

    text = str(value).strip()
    if not text:
        return None

    text = text.replace("/", "-")
    for fmt in (DATE_FORMAT, "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).strftime(DATE_FORMAT)
        except ValueError:
            continue
    return None


def to_date(value: str) -> date | None:
    parsed = parse_date_input(value)
    if not parsed:
        return None
    return datetime.strptime(parsed, DATE_FORMAT).date()


def format_display(date_str: str) -> str:
    parsed = parse_date_input(date_str)
    if not parsed:
        return str(date_str)
    return datetime.strptime(parsed, DATE_FORMAT).strftime(DISPLAY_FORMAT)


def get_status(expiry_str: str) -> tuple[str, str, int, str]:
    expiry = to_date(expiry_str)
    if expiry is None:
        return "不明", "⚪", 9999, "ok"

    days = (expiry - date.today()).days
    if days < 0:
        return "期限切れ", "🔴", days, "expired"
    if days <= 7:
        return f"あと{days}日", "🟠", days, "near"
    return f"あと{days}日", "🟢", days, "ok"


# ====================== 認証 ======================
def get_password() -> str:
    env_password = os.getenv("APP_PASSWORD")
    if env_password:
        return env_password
    try:
        return st.secrets["APP_PASSWORD"]
    except Exception:
        return DEFAULT_PASSWORD


def login_screen() -> None:
    st.title("🍦 無人アイス屋さん高井田店")
    st.subheader("賞味期限管理システム")
    st.markdown("---")
    st.markdown("**スマホからもアクセスできます**")

    with st.form("login_form", clear_on_submit=False):
        password = st.text_input("パスワード", type="password", placeholder="パスワードを入力")
        submitted = st.form_submit_button("ログイン", use_container_width=True)

    if submitted:
        if password == get_password():
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("パスワードが違います")

    st.caption("パスワードは管理者にお問い合わせください")


# ====================== フォーム処理 ======================
def add_product(name: str, expiry_value) -> str | None:
    clean_name = name.strip()
    expiry = parse_date_input(expiry_value)
    if not clean_name:
        return "商品名を入力してください"
    if not expiry:
        return "賞味期限の形式が正しくありません（例: 2026/07/15）"

    products = st.session_state.products
    products.append(
        {
            "id": get_next_id(products),
            "name": clean_name,
            "expiry_date": expiry,
        }
    )
    save_data(products)
    st.session_state.show_add_form = False
    return None


def update_product(product_id: int, name: str, expiry_value) -> str | None:
    clean_name = name.strip()
    expiry = parse_date_input(expiry_value)
    if not clean_name:
        return "商品名を入力してください"
    if not expiry:
        return "日付形式が正しくありません"

    products = st.session_state.products
    for product in products:
        if product["id"] == product_id:
            product["name"] = clean_name
            product["expiry_date"] = expiry
            break
    else:
        return "対象の商品が見つかりません"

    save_data(products)
    st.session_state.editing_id = None
    return None


def delete_product(product_id: int) -> None:
    products = st.session_state.products
    st.session_state.products = [p for p in products if p["id"] != product_id]
    save_data(st.session_state.products)
    st.session_state.delete_id = None


def render_add_form() -> None:
    with st.form("add_form", clear_on_submit=False):
        st.subheader("新しい商品を追加")
        name = st.text_input("商品名", placeholder="例: ガリガリ君 コーラ")
        expiry = st.date_input("賞味期限", value=date.today() + timedelta(days=7))

        col_save, col_cancel = st.columns(2)
        save_clicked = col_save.form_submit_button("保存", use_container_width=True)
        cancel_clicked = col_cancel.form_submit_button("キャンセル", use_container_width=True)

    if save_clicked:
        error = add_product(name, expiry)
        if error:
            st.error(error)
        else:
            st.success("商品を追加しました")
            st.rerun()

    if cancel_clicked:
        st.session_state.show_add_form = False
        st.rerun()


def render_edit_form(target: dict) -> None:
    current_expiry = to_date(target["expiry_date"]) or date.today()

    with st.form(f"edit_form_{target['id']}", clear_on_submit=False):
        st.subheader(f"編集: {target['name']}")
        name = st.text_input("商品名", value=target["name"])
        expiry = st.date_input("賞味期限", value=current_expiry)

        col_save, col_cancel = st.columns(2)
        save_clicked = col_save.form_submit_button("更新する", use_container_width=True)
        cancel_clicked = col_cancel.form_submit_button("キャンセル", use_container_width=True)

    if save_clicked:
        error = update_product(target["id"], name, expiry)
        if error:
            st.error(error)
        else:
            st.success("更新しました")
            st.rerun()

    if cancel_clicked:
        st.session_state.editing_id = None
        st.rerun()


# ====================== メインアプリ ======================
def filter_products(products: list[dict], search_text: str, filter_option: str) -> list[dict]:
    filtered = []
    query = search_text.strip().lower()

    for product in products:
        name = str(product.get("name", ""))
        if query and query not in name.lower():
            continue

        _, _, _, tag = get_status(product.get("expiry_date", ""))
        if filter_option == "期限切れ" and tag != "expired":
            continue
        if filter_option == "7日以内" and tag != "near":
            continue
        if filter_option == "正常" and tag != "ok":
            continue
        filtered.append(product)

    filtered.sort(key=lambda p: to_date(p.get("expiry_date", "")) or date.max)
    return filtered


def render_product_card(product: dict) -> None:
    status_text, emoji, _, tag = get_status(product.get("expiry_date", ""))
    expiry_disp = format_display(product.get("expiry_date", ""))

    if tag == "expired":
        border_color, bg = "#ff4d4f", "#fff1f0"
    elif tag == "near":
        border_color, bg = "#faad14", "#fffbe6"
    else:
        border_color, bg = "#52c41a", "#f6ffed"

    st.markdown(
        f"""
        <div style="
            border-left: 6px solid {border_color};
            background: {bg};
            padding: 12px 14px;
            margin-bottom: 10px;
            border-radius: 8px;
        ">
            <div style="font-size:1.1rem; font-weight:600;">{product['name']}</div>
            <div style="margin-top:4px; font-size:0.95rem;">
                賞味期限: <b>{expiry_disp}</b><br>
                状態: <b>{emoji} {status_text}</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_edit, col_delete, _ = st.columns([1, 1, 2])
    product_id = product["id"]

    if col_edit.button("編集", key=f"edit_{product_id}", use_container_width=True):
        st.session_state.editing_id = product_id
        st.session_state.show_add_form = False
        st.session_state.delete_id = None
        st.rerun()

    if col_delete.button("削除", key=f"delete_{product_id}", use_container_width=True):
        st.session_state.delete_id = product_id
        st.session_state.editing_id = None
        st.session_state.show_add_form = False
        st.rerun()


def main_app() -> None:
    st.title("🍦 高井田店 賞味期限管理")
    st.caption("商品名・賞味期限のみのシンプル管理（スマホ最適化）")

    if st.session_state.products is None:
        st.session_state.products = load_data()

    products = st.session_state.products

    expired_count = 0
    near_count = 0
    for product in products:
        _, _, _, tag = get_status(product.get("expiry_date", ""))
        if tag == "expired":
            expired_count += 1
        elif tag == "near":
            near_count += 1

    col_total, col_expired, col_near = st.columns(3)
    col_total.metric("📦 総商品数", len(products))
    col_expired.metric("🔴 期限切れ", expired_count)
    col_near.metric("🟠 7日以内", near_count)

    st.divider()

    search_col, filter_col = st.columns([3, 2])
    search_text = search_col.text_input(
        "🔍 商品名で検索",
        placeholder="例: ガリガリ君",
        label_visibility="collapsed",
    )
    filter_option = filter_col.selectbox(
        "状態フィルタ",
        ["すべて", "期限切れ", "7日以内", "正常"],
        label_visibility="collapsed",
    )

    if st.button("＋ 新しい商品を追加", type="primary", use_container_width=True):
        st.session_state.show_add_form = True
        st.session_state.editing_id = None
        st.session_state.delete_id = None
        st.rerun()

    if st.session_state.show_add_form:
        render_add_form()

    editing_id = st.session_state.editing_id
    if editing_id is not None:
        target = next((p for p in products if p["id"] == editing_id), None)
        if target:
            render_edit_form(target)
        else:
            st.session_state.editing_id = None

    delete_id = st.session_state.delete_id
    if delete_id is not None:
        target = next((p for p in products if p["id"] == delete_id), None)
        if target:
            st.warning(f"「{target['name']}」を本当に削除しますか？")
            col_yes, col_no = st.columns(2)
            if col_yes.button("はい、削除する", type="primary", use_container_width=True, key=f"confirm_delete_{delete_id}"):
                delete_product(delete_id)
                st.success("削除しました")
                st.rerun()
            if col_no.button("キャンセル", use_container_width=True, key=f"cancel_delete_{delete_id}"):
                st.session_state.delete_id = None
                st.rerun()
        else:
            st.session_state.delete_id = None

    st.divider()

    filtered = filter_products(products, search_text, filter_option)
    if not filtered:
        st.info("該当する商品がありません")
    else:
        st.markdown(f"**表示中: {len(filtered)} 件**（賞味期限が近い順）")
        for product in filtered:
            render_product_card(product)

    st.divider()
    st.caption(f"データ保存先: {DATA_FILE}")
    st.caption("データは自動保存されます。スマホからもご利用ください。")

    if st.button("ログアウト"):
        st.session_state.authenticated = False
        st.rerun()


def main() -> None:
    init_session_state()
    if st.session_state.authenticated:
        main_app()
    else:
        login_screen()


main()