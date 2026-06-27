# 無人アイス屋さん高井田店 賞味期限管理
## Streamlit Web版 デプロイ完全ガイド

このアプリは **Streamlit** で作られたスマホ対応のWebアプリです。
どこからでもブラウザでアクセスできます。

---

## 1. 必要なファイル（このリポジトリにあるもの）

- `app.py` — Streamlit本体（商品名・賞味期限・状態のみ）
- `requirements.txt` — 依存パッケージ
- `render.yaml` — Render.com自動デプロイ設定
- `.streamlit/config.toml` — サーバー設定
- `.streamlit/secrets.toml.example` — パスワード設定例

---

## 2. ローカルで試す方法

```bash
# 1. 依存インストール
pip install -r requirements.txt

# 2. シークレット設定（任意・推奨）
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# .streamlit/secrets.toml を編集してパスワードを変更

# 3. 起動
streamlit run app.py
```

ブラウザで `http://localhost:8501` が開きます。

---

## 3. Render.com へのデプロイ（おすすめ・永続化しやすい）

Render.com は無料枠があり、**ディスク（永続ストレージ）**を簡単に追加できます。

### ステップバイステップ

1. **GitHubにプッシュ**
   - このフォルダ全体をGitHubリポジトリにアップロード

2. **Renderにサインアップ**
   - https://render.com にアクセスしてGitHubでログイン

3. **New Web Service** を作成
   - 「Build and Deploy」→ 「Web Service」
   - 「Connect a repository」から自分のGitHubリポジトリを選択

4. **設定（render.yaml が自動で読み込まれます）**
   - Name: 任意（例: takaida-expiry）
   - Region: Oregon（おすすめ）
   - Plan: Free でOK（最初は）
   - Branch: main

5. **永続ディスクを追加（超重要）**
   - サービス作成後、ダッシュボードでアプリを開く
   - 左メニュー **「Disks」** → **「Add Disk」**
   - Name: `expiry-data`
   - **Mount Path**: `/data`  （これ大事！）
   - Size: 1 GB で十分
   - 「Create Disk」

6. **環境変数確認**
   - すでに `render.yaml` で `DATA_DIR=/data` が設定されています
   - これによりJSONファイルがディスクに永続保存されます

7. **デプロイ**
   - 「Deploy」ボタンで起動
   - ログに `streamlit run app.py` と表示されたら成功

8. **アクセスURL**
   - Renderが `https://takaida-ice-expiry.onrender.com` のようなURLを発行します
   - スマホのブラウザからでもアクセス可能

9. **パスワード変更（必須）**
   - Renderダッシュボード → Environment → Add Environment Variable
   - Key: `APP_PASSWORD`
   - Value: 自分だけが知っている強いパスワード
   - 保存後、**Manual Deploy** して反映

---

## 4. Streamlit Community Cloud へのデプロイ

https://share.streamlit.io

### 手順

1. GitHubにコードをプッシュ
2. https://share.streamlit.io にアクセス → 「Deploy an app」
3. リポジトリを選択 → `app.py` を指定
4. **Secrets** に以下を追加（Advanced settings）

```toml
APP_PASSWORD = "ここに自分のパスワード"
```

**注意**: Streamlit Community Cloud は **ファイルシステムが永続化されません**。
再デプロイや一定時間経過でデータが消える可能性があります。

→ **本格運用するなら Render.com + Disk** を強くおすすめします。

---

## 5. データ永続化の仕組み

- デフォルト: `data/products.json`
- Render利用時: `DATA_DIR=/data` により `/data/products.json` に保存
- ディスクをマウントすればサーバー再起動・再デプロイ後もデータが残ります
- バックアップしたい場合は、RenderダッシュボードからDiskをダウンロード可能

---

## 6. スマホでの使い方

- URLを開くだけ
- パスワード入力でログイン
- 画面は縦長でも見やすく設計済み
- 「＋ 新しい商品を追加」ボタンが大きくて押しやすい
- 各商品はカード形式で表示され、編集・削除も簡単

---

## 7. トラブルシューティング

**データが消える**
→ RenderでDiskを正しく `/data` にマウントしたか確認

**パスワードがわからない**
→ デプロイ時に `APP_PASSWORD` 環境変数を設定してください

**Renderでビルドエラー**
→ `requirements.txt` に `streamlit` が入っているか確認

**ローカルでシークレットが効かない**
→ `.streamlit/secrets.toml` ファイルを作ってください（.exampleをコピー）

---

## 8. セキュリティについて

- 簡易パスワード認証のみ（st.secrets使用）
- 本番運用時は：
  - 強力なパスワードを設定
  - 定期的に変更
  - 必要ならVPNやRenderのアクセス制限を組み合わせる

---

作った人：Grok
高井田店の無人アイス屋さんを応援しています！
何か質問があれば聞いてください。
