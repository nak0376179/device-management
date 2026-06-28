# Device Management Frontend

Vite + React + TypeScript + Tailwind v4 + shadcn/ui のダッシュボード。`backend/` の FastAPI を経由してデバイスへ遠隔コマンドを実行します。UI コンポーネントは Storybook でカタログ化し、Vitest（Storybook ブラウザテスト）で検証します。

## 機能

- グループ認証ログイン
- デバイス一覧（左サイドバー、接続/切断インジケータ）
- 選択デバイスへのコマンド実行（⌘/Ctrl + Enter で送信）
- コマンド結果を 3 秒間隔でポーリング表示（ステータスバッジ / exit code / 実行時間 / stdout・stderr）
- ライト/ダークテーマ切替

## デザインシステム

shadcn/ui（new-york / zinc ベース）の UI プリミティブを `src/components/ui/` に、デバイス管理ドメインのコンポーネントを `src/components/` に配置。デザイントークンは `src/styles/globals.css` に集約し、デバイス接続状態とコマンドのライフサイクル用の機能的な status カラー拡張を定義しています。各コンポーネントには `*.stories.tsx` を併設し、`npm test` で全ストーリーをブラウザ上のコンポーネントテストとして実行します。

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
| `npm run storybook` | Storybook 開発サーバ (http://localhost:6006) |
| `npm run build-storybook` | Storybook の静的ビルド (`storybook-static/`) |
| `npm test` | Vitest で全ストーリーをブラウザテスト実行 |
| `npm run test:watch` | Vitest をウォッチモードで実行 |

## 環境変数

| 変数 | デフォルト | 説明 |
| --- | --- | --- |
| `VITE_API_URL` | `/api` (= Vite proxy 経由) | バックエンド API のベース URL |
| `VITE_PROXY_TARGET` | `http://localhost:9001` | dev で `/api` を転送する先 |

開発時は Vite が `/api/*` を `VITE_PROXY_TARGET` にプロキシするので同一オリジン扱いとなり、CORS プリフライトが発生しません。デプロイ後の SAM Outputs の `ApiUrl` を `.env.production` の `VITE_API_URL` に設定してビルドすると、本番ビルドはそのオリジンに直接アクセスします (API Gateway 側の CORS 設定が効きます)。
