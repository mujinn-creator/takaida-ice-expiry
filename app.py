#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
無人アイス屋さん高井田店 賞味期限管理 (Streamlit版)
スマホ対応 + 簡易パスワード認証 + 永続JSON保存
"""

import streamlit as st
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# ====================== 設定 ======================
st.set_page_config(
    page_title="高井田店 賞味期限管理",
    page_icon="🍦",
    layout="centered",
    initial_sidebar_state="collapsed"
)

DATA_DIR_ENV = os.getenv("DATA_DIR", "data")
DATA_FILE = os.path.join(DATA_DIR_ENV, "products.json")

DATE_FORMAT = "%Y-%m-%d"
DISPLAY_FORMAT = "%Y/%m/%d"

# 簡易パスワード（本番では必ず secrets で上書き）
DEFAULT_PASSWORD = "takaida2026"

# ====================== データ永続化 ======================
def ensure_data_dir():
    Path(DATA_DIR_ENV).mkdir(parents=True, exist_ok=True)

def load_data():
    ensure_data_dir()
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    # 初回 or エラー時はサンプル作成
    samples = get_sample_data()
    save_data(samples)
    return samples

def save_data(products):
    ensure_data_dir()
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

def get_sample_data():
    today = datetime.now().date()
    return [
        {"id": 1, "name": "ガリガリ君 コーラ", "expiry_date": (today + timedelta(days=2)).strftime(DATE_FORMAT)},
        {"id": 2, "name": "ハーゲンダッツ バニラ", "expiry_date": (today - timedelta(days=1)).strftime(DATE_FORMAT)},
        {"id": 3, "name": "アイスの実 マンゴー", "expiry_date": (today + timedelta(days=12)).strftime(DATE_FORMAT)},
        {"id": 4, "name": "雪見だいふく", "expiry_date": (today + timedelta(days=5)).strftime(DATE_FORMAT)},
        {"id": 5, "name": "明治 エッセル スーパーカップ", "expiry_date": (today + timedelta(days=30)).strftime(DATE_FORMAT)},
    ]

def get_next_id(products):
    if not products:
        return 1
    return max(p.get("id", 0) for p in products) + 1

# ====================== 状態計算 ======================
def get_status(expiry_str: str):
    """賞味期限から状態を返す"""
    try:
        expiry = datetime.strptime(expiry_str, DATE_FORMAT).date()
        today = datetime.now().date()
        days = (expiry - today).days

        if days < 0:
            return "期限切れ", "🔴", days, "expired"
        elif days <= 7:
            return f"あと{days}日", "🟠", days, "near"
        else:
            return f"あと{days}日", "🟢", days, "ok"
    except Exception:
        return "不明", "⚪", 9999, "ok"

def format_display(date_str: str) -> str:
    try:
        d = datetime.strptime(date_str, DATE_FORMAT)
        return d.strftime(DISPLAY_FORMAT)
    except:
        return date_str

# ====================== 認証 ======================
def get_password():
    """st.secrets からパスワード取得（なければデフォルト）"""
    try:
        return st.secrets["APP_PASSWORD"]
    except Exception:
        return DEFAULT_PASSWORD

def login_screen():
    st.title("🍦 無人アイス屋さん高井田店")
    st.subheader("賞味期限管理システム")

    st.markdown("---")
    st.markdown("**スマホからもアクセスできます**")

    with st.form("login_form", clear_on_submit=False):
        pw = st.text_input("パスワード", type="password", placeholder="パスワードを入力")
        submitted = st.form_submit_button("ログイン", use_container_width=True)

        if submitted:
            if pw == get_password():
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("パスワードが違います")

    st.caption("パスワードは管理者にお問い合わせください")

# ====================== メインアプリ ======================
def main_app():
    st.title("🍦 高井田店 賞味期限管理")
    st.caption("商品名・賞味期限のみのシンプル管理（スマホ最適化）")

    # データ読み込み
    if "products" not in st.session_state:
        st.session_state.products = load_data()

    products = st.session_state.products

    # サマリー（上部に大きく）
    expired_count = 0
    near_count = 0
    for p in products:
        _, _, days, tag = get_status(p["expiry_date"])
        if tag == "expired":
            expired_count += 1
        elif tag == "near":
            near_count += 1

    col1, col2, col3 = st.columns(3)
    col1.metric("📦 総商品数", len(products))
    col2.metric("🔴 期限切れ", expired_count, delta_color="inverse")
    col3.metric("🟠 7日以内", near_count)

    st.divider()

    # 検索 + フィルタ
    search_col, filter_col = st.columns([3, 1.6])
    search_text = search_col.text_input(
        "🔍 商品名で検索",
        placeholder="例: ガリガリ君",
        label_visibility="collapsed"
    )

    filter_option = filter_col.selectbox(
        "状態フィルタ",
        ["すべて", "期限切れ", "7日以内", "正常"],
        label_visibility="collapsed"
    )

    # フィルタリング
    filtered = []
    for p in products:
        # 検索
        if search_text and search_text.lower() not in p["name"].lower():
            continue
        # 状態フィルタ
        _, _, _, tag = get_status(p["expiry_date"])
        if filter_option == "期限切れ" and tag != "expired":
            continue
        if filter_option == "7日以内" and tag != "near":
            continue
        if filter_option == "正常" and tag != "ok":
            continue
        filtered.append(p)

    # 賞味期限が近い順にソート
    def sort_key(p):
        try:
            return datetime.strptime(p["expiry_date"], DATE_FORMAT)
        except:
            return datetime.max
    filtered.sort(key=sort_key)

    # ===== 商品追加 =====
    if st.button("＋ 新しい商品を追加", type="primary", use_container_width=True):
        st.session_state["show_add"] = True
        st.session_state["editing_id"] = None

    # 追加フォーム
    if st.session_state.get("show_add"):
        with st.form("add_form", clear_on_submit=True):
            st.subheader("新しい商品を追加")
            name = st.text_input("商品名", placeholder="例: ガリガリ君 コーラ")
            expiry = st.text_input("賞味期限（YYYY/MM/DD）", placeholder="2026/07/15")

            c1, c2 = st.columns(2)
            if c1.form_submit_button("保存", use_container_width=True):
                if name.strip() and expiry.strip():
                    try:
                        # 正規化して保存
                        exp_save = expiry.strip().replace("/", "-")
                        datetime.strptime(exp_save, DATE_FORMAT)
                        new_p = {
                            "id": get_next_id(products),
                            "name": name.strip(),
                            "expiry_date": exp_save.replace("-", "-")
                        }
                        # 正しい形式に
                        new_p["expiry_date"] = datetime.strptime(exp_save, DATE_FORMAT).strftime(DATE_FORMAT)

                        products.append(new_p)
                        save_data(products)
                        st.session_state.products = products
                        st.session_state["show_add"] = False
                        st.success("商品を追加しました")
                        st.rerun()
                    except:
                        st.error("賞味期限の形式が正しくありません（例: 2026/07/15）")
                else:
                    st.error("商品名と賞味期限を入力してください")

            if c2.form_submit_button("キャンセル", use_container_width=True):
                st.session_state["show_add"] = False
                st.rerun()

    st.divider()

    # ===== 商品一覧（カード形式・スマホに優しい） =====
    if not filtered:
        st.info("該当する商品がありません")
    else:
        st.markdown(f"**表示中: {len(filtered)} 件**（賞味期限が近い順）")

        for p in filtered:
            status_text, emoji, days, tag = get_status(p["expiry_date"])
            expiry_disp = format_display(p["expiry_date"])

            # 色分け用の背景
            if tag == "expired":
                border_color = "#ff4d4f"
                bg = "#fff1f0"
            elif tag == "near":
                border_color = "#faad14"
                bg = "#fffbe6"
            else:
                border_color = "#52c41a"
                bg = "#f6ffed"

            with st.container():
                # HTMLで少し装飾（スマホでも見やすい）
                st.markdown(
                    f"""
                    <div style="
                        border-left: 6px solid {border_color};
                        background: {bg};
                        padding: 12px 14px;
                        margin-bottom: 10px;
                        border-radius: 8px;
                    ">
                        <div style="font-size:1.1rem; font-weight:600;">{p['name']}</div>
                        <div style="margin-top:4px; font-size:0.95rem;">
                            賞味期限: <b>{expiry_disp}</b><br>
                            状態: <b>{emoji} {status_text}</b>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # アクションボタン
                btn_col1, btn_col2, _ = st.columns([1, 1, 2])
                edit_key = f"edit_{p['id']}"
                del_key = f"del_{p['id']}"

                if btn_col1.button("編集", key=edit_key, use_container_width=True):
                    st.session_state["editing_id"] = p["id"]
                    st.session_state["show_add"] = False

                if btn_col2.button("削除", key=del_key, use_container_width=True):
                    st.session_state["delete_id"] = p["id"]

                st.markdown("")  # 少しスペース

    # ===== 編集フォーム =====
    editing_id = st.session_state.get("editing_id")
    if editing_id is not None:
        target = next((p for p in products if p["id"] == editing_id), None)
        if target:
            with st.form("edit_form"):
                st.subheader(f"編集: {target['name']}")
                new_name = st.text_input("商品名", value=target["name"])
                new_expiry = st.text_input(
                    "賞味期限（YYYY/MM/DD）",
                    value=format_display(target["expiry_date"])
                )

                c1, c2 = st.columns(2)
                if c1.form_submit_button("更新する", use_container_width=True):
                    if new_name.strip() and new_expiry.strip():
                        try:
                            exp_save = new_expiry.strip().replace("/", "-")
                            datetime.strptime(exp_save, DATE_FORMAT)
                            target["name"] = new_name.strip()
                            target["expiry_date"] = datetime.strptime(exp_save, DATE_FORMAT).strftime(DATE_FORMAT)
                            save_data(products)
                            st.session_state.products = products
                            st.session_state["editing_id"] = None
                            st.success("更新しました")
                            st.rerun()
                        except:
                            st.error("日付形式が正しくありません")
                    else:
                        st.error("すべての項目を入力してください")

                if c2.form_submit_button("キャンセル", use_container_width=True):
                    st.session_state["editing_id"] = None
                    st.rerun()

    # ===== 削除確認 =====
    if "delete_id" in st.session_state:
        del_id = st.session_state["delete_id"]
        target = next((p for p in products if p["id"] == del_id), None)
        if target:
            st.warning(f"「{target['name']}」を本当に削除しますか？")
            c1, c2 = st.columns(2)
            if c1.button("はい、削除する", type="primary", use_container_width=True):
                products[:] = [p for p in products if p["id"] != del_id]
                save_data(products)
                st.session_state.products = products
                del st.session_state["delete_id"]
                st.success("削除しました")
                st.rerun()
            if c2.button("キャンセル", use_container_width=True):
                del st.session_state["delete_id"]
                st.rerun()

    st.divider()

    # フッター
    st.caption("データは自動保存されます。スマホからもご利用ください。")
    if st.button("ログアウト", use_container_width=False):
        st.session_state["authenticated"] = False
        st.rerun()

# ====================== エントリーポイント ======================
def main():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        login_screen()
    else:
        main_app()

if __name__ == "__main__":
    main()
