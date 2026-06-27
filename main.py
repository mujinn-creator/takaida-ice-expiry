#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
無人アイス屋さん高井田店 賞味期限管理システム
シンプルなTkinterデスクトップアプリ
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import csv
import os
from datetime import datetime, timedelta
import tkinter.font as tkFont

# データファイル
DATA_FILE = "products.json"
DATE_FORMAT = "%Y-%m-%d"  # 内部保存はISO形式
DISPLAY_DATE_FORMAT = "%Y/%m/%d"

# 色設定（Treeviewタグ用）
EXPIRED_TAG = "expired"       # 期限切れ：赤
NEAR_EXPIRY_TAG = "near"      # 7日以内：オレンジ
NORMAL_TAG = "normal"


def get_japanese_font(size=11, bold=False):
    """Windowsで日本語表示できるフォントを取得"""
    candidates = [
        "Yu Gothic UI",
        "Yu Gothic",
        "Meiryo",
        "MS Gothic",
        "Noto Sans CJK JP",
        "Hiragino Sans",
        "TakaoGothic",
    ]
    weight = "bold" if bold else "normal"
    for name in candidates:
        try:
            return tkFont.Font(family=name, size=size, weight=weight)
        except tk.TclError:
            continue
    # フォールバック
    return tkFont.Font(size=size, weight=weight)


class ExpiryManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("無人アイス屋さん高井田店 賞味期限管理")
        self.root.geometry("820x520")
        self.root.minsize(700, 420)

        # 日本語フォント（シンプルで見やすく）
        self.font_normal = get_japanese_font(13)
        self.font_bold = get_japanese_font(13, bold=True)
        self.font_title = get_japanese_font(16, bold=True)

        # データ
        self.products = []  # リスト of dict
        self.filtered_products = []  # 表示用

        # スタイル設定
        self.setup_styles()

        # UI構築
        self.create_widgets()

        # データ読み込み
        self.load_data()

        # 初回表示
        self.refresh_table()

        # 起動時にアラート表示（期限切れ/近い商品があれば）
        self.show_startup_alert()

    def setup_styles(self):
        style = ttk.Style()
        # シンプルで見やすいスタイル
        style.configure("Treeview", font=self.font_normal, rowheight=32)
        style.configure("Treeview.Heading", font=self.font_bold)
        style.configure("TButton", font=self.font_normal, padding=8)
        style.configure("TLabel", font=self.font_normal)
        style.configure("TEntry", font=self.font_normal)

        # タグ色は refresh_table() で tag_configure により設定する
        self.root.option_add("*Treeview*Background", "white")

    def create_widgets(self):
        # === メインフレーム ===
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # === タイトル（シンプル） ===
        title_label = ttk.Label(main_frame, text="無人アイス屋さん高井田店 賞味期限管理", font=self.font_title)
        title_label.pack(pady=(0, 8))

        # === 検索行（シンプル） ===
        filter_frame = ttk.Frame(main_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(filter_frame, text="検索（商品名）:").pack(side=tk.LEFT, padx=(0, 6))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, width=28, font=self.font_normal)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_table())
        self.search_entry.bind("<Return>", lambda e: self.refresh_table())

        # 右側ボタン
        btn_frame = ttk.Frame(filter_frame)
        btn_frame.pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text="更新", command=self.refresh_table).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="CSVエクスポート", command=self.export_csv).pack(side=tk.LEFT, padx=3)

        # === テーブル（超シンプル3カラム） ===
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        columns = ("name", "expiry", "status")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        # カラム設定（シンプル）
        self.tree.heading("name", text="商品名", command=lambda: self.sort_by("name"))
        self.tree.heading("expiry", text="賞味期限", command=lambda: self.sort_by("expiry"))
        self.tree.heading("status", text="状態", command=lambda: self.sort_by("status"))

        # 列幅と配置（見やすく）
        self.tree.column("name", width=420, minwidth=280)
        self.tree.column("expiry", width=140, minwidth=120, anchor=tk.CENTER)
        self.tree.column("status", width=140, minwidth=110, anchor=tk.CENTER)

        # スクロールバー
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        # ダブルクリックで編集 + キーボード
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Delete>", lambda e: self.delete_product())
        self.tree.bind("<Return>", lambda e: self.edit_product())

        # === 操作ボタン（シンプル） ===
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=(6, 0))

        ttk.Button(action_frame, text="＋ 商品追加", command=self.add_product, width=15).pack(side=tk.LEFT, padx=4)
        ttk.Button(action_frame, text="編集", command=self.edit_product, width=9).pack(side=tk.LEFT, padx=3)
        ttk.Button(action_frame, text="削除", command=self.delete_product, width=9).pack(side=tk.LEFT, padx=3)

        ttk.Button(action_frame, text="再読込", command=self.reload_data, width=9).pack(side=tk.LEFT, padx=(18, 3))

        # 右寄せ
        ttk.Button(action_frame, text="終了", command=self.on_close, width=9).pack(side=tk.RIGHT, padx=3)

        # === ステータスバー ===
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(8, 0))

        self.status_label = ttk.Label(status_frame, text="", anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.alert_label = ttk.Label(status_frame, text="", foreground="#cc0000", anchor=tk.E)
        self.alert_label.pack(side=tk.RIGHT, padx=10)

    def load_data(self):
        """JSONからデータを読み込む。初回はサンプルデータを作成"""
        self.products = []
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.products = data
            except Exception as e:
                messagebox.showerror("読み込みエラー", f"データの読み込みに失敗しました:\n{e}\n\n空のデータで起動します。")
                self.products = []
        else:
            # 初回起動：アイスクリーム向けサンプルデータ
            self.products = self._get_sample_data()
            self.save_data()

    def _get_sample_data(self):
        """シンプルなサンプルデータ（商品名＋賞味期限のみ）"""
        today = datetime.now().date()
        samples = [
            {"id": 1, "name": "ガリガリ君 コーラ", "expiry_date": (today + timedelta(days=2)).strftime(DATE_FORMAT)},
            {"id": 2, "name": "ハーゲンダッツ バニラ", "expiry_date": (today - timedelta(days=1)).strftime(DATE_FORMAT)},
            {"id": 3, "name": "アイスの実 マンゴー", "expiry_date": (today + timedelta(days=12)).strftime(DATE_FORMAT)},
            {"id": 4, "name": "雪見だいふく", "expiry_date": (today + timedelta(days=5)).strftime(DATE_FORMAT)},
            {"id": 5, "name": "明治 エッセル スーパーカップ チョコ", "expiry_date": (today + timedelta(days=30)).strftime(DATE_FORMAT)},
            {"id": 6, "name": "ロッテ クールミントガム", "expiry_date": (today + timedelta(days=180)).strftime(DATE_FORMAT)},
        ]
        return samples

    def save_data(self):
        """JSONに保存"""
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.products, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("保存エラー", f"データの保存に失敗しました:\n{e}")

    def reload_data(self):
        self.load_data()
        self.refresh_table()

    def get_product_status(self, expiry_str):
        """賞味期限から状態を返す"""
        try:
            expiry = datetime.strptime(expiry_str, DATE_FORMAT).date()
            today = datetime.now().date()
            days_left = (expiry - today).days

            if days_left < 0:
                return "期限切れ", EXPIRED_TAG
            elif days_left <= 7:
                return f"あと{days_left}日", NEAR_EXPIRY_TAG
            else:
                return f"あと{days_left}日", NORMAL_TAG
        except Exception:
            return "不明", NORMAL_TAG

    def refresh_table(self):
        """テーブルを更新（商品名検索のみ）"""
        search_text = self.search_var.get().strip().lower()

        self.filtered_products = []
        for p in self.products:
            if search_text and search_text not in p.get("name", "").lower():
                continue
            self.filtered_products.append(p)

        # テーブルをクリア
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 行を挿入（商品名 / 賞味期限 / 状態）
        for p in self.filtered_products:
            status_text, tag = self.get_product_status(p["expiry_date"])
            expiry_disp = self.format_date_for_display(p.get("expiry_date", ""))

            values = (
                p.get("name", ""),
                expiry_disp,
                status_text
            )
            iid = str(p.get("id"))
            self.tree.insert("", tk.END, iid=iid, values=values, tags=(tag,))

        # 色設定（見やすく）
        self.tree.tag_configure(EXPIRED_TAG, background="#ffcccc", foreground="#990000")
        self.tree.tag_configure(NEAR_EXPIRY_TAG, background="#ffe8b3", foreground="#8b4500")
        self.tree.tag_configure(NORMAL_TAG, background="#f8fff8", foreground="#003300")

        self.update_status_bar()

    def format_date_for_display(self, date_str):
        """保存形式 → 表示形式"""
        try:
            d = datetime.strptime(date_str, DATE_FORMAT)
            return d.strftime(DISPLAY_DATE_FORMAT)
        except:
            return date_str

    def parse_display_date(self, disp_str):
        """表示形式や柔軟な入力 → 保存形式 (YYYY-MM-DD)"""
        s = disp_str.strip().replace("/", "-")
        # いくつかのフォーマットを試す
        for fmt in (DATE_FORMAT, DISPLAY_DATE_FORMAT.replace("/", "-"), "%Y/%m/%d"):
            try:
                d = datetime.strptime(s, fmt)
                return d.strftime(DATE_FORMAT)
            except ValueError:
                continue
        # 最後の手段
        return disp_str.strip()

    def update_status_bar(self):
        total = len(self.products)
        expired = sum(1 for p in self.products if self.get_product_status(p["expiry_date"])[1] == EXPIRED_TAG)
        near = sum(1 for p in self.products if self.get_product_status(p["expiry_date"])[1] == NEAR_EXPIRY_TAG)

        self.status_label.config(
            text=f"商品数: {total}   |   期限切れ: {expired}   |   7日以内: {near}   |   表示中: {len(self.filtered_products)}"
        )

        if expired > 0 or near > 0:
            self.alert_label.config(text=f"⚠ 期限切れ {expired} / 近づき {near}")
        else:
            self.alert_label.config(text="")

    def show_startup_alert(self):
        """起動時に期限切れ・近い商品をダイアログで知らせる"""
        expired = [p for p in self.products if self.get_product_status(p["expiry_date"])[1] == EXPIRED_TAG]
        near = [p for p in self.products if self.get_product_status(p["expiry_date"])[1] == NEAR_EXPIRY_TAG]

        if expired or near:
            msg_lines = []
            if expired:
                msg_lines.append("【期限切れの商品】")
                for p in expired[:5]:
                    msg_lines.append(f"  ・{p['name']} （{self.format_date_for_display(p['expiry_date'])}）")
                if len(expired) > 5:
                    msg_lines.append(f"  ...他 {len(expired)-5}点")
            if near:
                msg_lines.append("\n【7日以内に期限が切れる商品】")
                for p in near[:5]:
                    status, _ = self.get_product_status(p["expiry_date"])
                    msg_lines.append(f"  ・{p['name']} （{status}）")
                if len(near) > 5:
                    msg_lines.append(f"  ...他 {len(near)-5}点")

            messagebox.showwarning(
                "賞味期限アラート",
                "起動時に期限が近い商品を検出しました。\n\n" + "\n".join(msg_lines)
            )

    def on_double_click(self, event):
        self.edit_product()

    def get_selected_product(self):
        """現在選択されている商品のデータを返す（iid = 商品ID）"""
        sel = self.tree.selection()
        if not sel:
            return None, None
        item = sel[0]
        try:
            prod_id = int(item)
        except ValueError:
            return None, None
        for p in self.products:
            if p.get("id") == prod_id:
                return p, item
        return None, None

    def add_product(self):
        self._open_product_dialog()

    def edit_product(self):
        product, _ = self.get_selected_product()
        if not product:
            messagebox.showinfo("選択してください", "編集する商品をテーブルから選択してください。")
            return
        self._open_product_dialog(product)

    def delete_product(self):
        product, tree_item = self.get_selected_product()
        if not product:
            messagebox.showinfo("選択してください", "削除する商品をテーブルから選択してください。")
            return

        if not messagebox.askyesno("削除確認", f"以下の商品を削除しますか？\n\n{product['name']}"):
            return

        self.products = [p for p in self.products if p.get("id") != product.get("id")]
        self.save_data()
        self.refresh_table()

    def _open_product_dialog(self, product=None):
        """超シンプル追加・編集ダイアログ（商品名＋賞味期限のみ）"""
        is_edit = product is not None

        dialog = tk.Toplevel(self.root)
        dialog.title("商品を追加" if not is_edit else "商品を編集")
        dialog.geometry("420x220")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # 入力変数（必要なものだけ）
        name_var = tk.StringVar(value=product.get("name", "") if product else "")
        expiry_var = tk.StringVar(value=self.format_date_for_display(product.get("expiry_date", "")) if product else "")

        # フォーム
        frm = ttk.Frame(dialog, padding=20)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="商品名", font=self.font_bold).grid(row=0, column=0, sticky="w", pady=(0, 2))
        name_entry = ttk.Entry(frm, textvariable=name_var, width=36, font=self.font_normal)
        name_entry.grid(row=1, column=0, columnspan=2, pady=(0, 14))
        name_entry.focus_set()

        ttk.Label(frm, text="賞味期限（YYYY/MM/DD）", font=self.font_bold).grid(row=2, column=0, sticky="w", pady=(0, 2))
        expiry_entry = ttk.Entry(frm, textvariable=expiry_var, width=20, font=self.font_normal)
        expiry_entry.grid(row=3, column=0, sticky="w")

        ttk.Label(frm, text="※ 半角数字で入力してください", foreground="#666666").grid(row=4, column=0, columnspan=2, sticky="w", pady=(10, 0))

        # 保存ボタン
        btn_frm = ttk.Frame(frm)
        btn_frm.grid(row=5, column=0, columnspan=2, pady=(18, 0))

        def on_save():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("入力エラー", "商品名を入力してください。", parent=dialog)
                return

            expiry_str = expiry_var.get().strip()
            if not expiry_str:
                messagebox.showwarning("入力エラー", "賞味期限を入力してください。", parent=dialog)
                return

            try:
                expiry_save = self.parse_display_date(expiry_str)
                datetime.strptime(expiry_save, DATE_FORMAT)
            except Exception:
                messagebox.showwarning("日付エラー", "賞味期限の形式が正しくありません。\n例: 2026/07/15", parent=dialog)
                return

            new_product = {
                "id": product["id"] if is_edit else self._generate_new_id(),
                "name": name,
                "expiry_date": expiry_save
            }

            if is_edit:
                for i, p in enumerate(self.products):
                    if p.get("id") == new_product["id"]:
                        self.products[i] = new_product
                        break
            else:
                self.products.append(new_product)

            self.save_data()
            self.refresh_table()
            dialog.destroy()

        ttk.Button(btn_frm, text="保存", command=on_save, width=14).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frm, text="キャンセル", command=dialog.destroy, width=14).pack(side=tk.LEFT, padx=8)

    def _generate_new_id(self):
        if not self.products:
            return 1
        return max(p.get("id", 0) for p in self.products) + 1

    def sort_by(self, col):
        """カラムクリックでソート（シンプル版）"""
        reverse = False
        if hasattr(self, "_last_sort") and self._last_sort == col:
            reverse = not getattr(self, "_last_sort_reverse", False)

        def key_func(p):
            val = p.get(col, "")
            if col == "expiry":
                try:
                    return datetime.strptime(val, DATE_FORMAT)
                except:
                    return datetime.min
            return str(val).lower()

        self.products.sort(key=key_func, reverse=reverse)
        self._last_sort = col
        self._last_sort_reverse = reverse
        self.refresh_table()

    def export_csv(self):
        """現在の表示内容をシンプルCSVでエクスポート"""
        if not self.filtered_products:
            messagebox.showinfo("エクスポート", "エクスポートするデータがありません。")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSVファイル", "*.csv"), ("すべてのファイル", "*.*")],
            initialfile="賞味期限一覧.csv"
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["商品名", "賞味期限", "状態"])

                for p in self.filtered_products:
                    status_text, _ = self.get_product_status(p["expiry_date"])
                    writer.writerow([
                        p.get("name", ""),
                        self.format_date_for_display(p.get("expiry_date", "")),
                        status_text
                    ])

            messagebox.showinfo("エクスポート完了", f"CSVを保存しました:\n{file_path}")
        except Exception as e:
            messagebox.showerror("エクスポート失敗", str(e))

    def on_close(self):
        self.save_data()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ExpiryManagerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
