# Device Management Frontend

Vite + React + TypeScript のダッシュボード。`backend/` の FastAPI を経由して AWS IoT Device Shadow を操作します。

## 機能

- デバイス一覧（左サイドバー）
- 選択デバイスの Shadow を 3 秒間隔でポーリング表示
- System ステータス（uptime / CPU / memory）
- インターフェーステーブル
  - ON/OFF トグル
  - description のクリック編集（Enter で保存、Esc でキャンセル）
  - Rx/Tx 表示
  - desired と reported が乖離している間は `(pending)` 表示

## セットアップ

```bash
cd frontend
cp .env.example .env          # 必要なら VITE_API_URL を変更
npm install
npm run dev                   # http://localhost:5173
```

API サーバ (`backend/`) と仮想デバイス (`device/`) を起動した状態で開くこと。

## スクリプト

| コマンド | 用途 |
| --- | --- |
| `npm run dev` | Vite 開発サーバ |
| `npm run build` | 型チェック + プロダクションビルド (`dist/`) |
| `npm run preview` | ビルド成果物のローカルプレビュー |
| `npm run typecheck` | `tsc --noEmit` |

## 環境変数

| 変数 | デフォルト | 説明 |
| --- | --- | --- |
| `VITE_API_URL` | `/api` (= Vite proxy 経由) | バックエンド API のベース URL |
| `VITE_PROXY_TARGET` | `http://localhost:9001` | dev で `/api` を転送する先 |

開発時は Vite が `/api/*` を `VITE_PROXY_TARGET` にプロキシするので同一オリジン扱いとなり、CORS プリフライトが発生しません。デプロイ後の SAM Outputs の `ApiUrl` を `.env.production` の `VITE_API_URL` に設定してビルドすると、本番ビルドはそのオリジンに直接アクセスします (API Gateway 側の CORS 設定が効きます)。
