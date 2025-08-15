# Okamichan

このプロジェクトは [Next.js](https://nextjs.org) を使って作成されたAIチャットUI「Okamichan」です。

---

## プロジェクト仕様

### 概要
- ChatGPTやMonica AIのような**AIチャットUI**をNext.js/React/TypeScriptで実装
- フロントエンドのみ（バックエンドAPIは未実装、デモ応答）
- ダーク/ライトモード切り替え対応
- モダンでシンプルなUI/UX

### 主な機能
- サイドバーでチャット履歴・新規チャット作成・設定/アカウント/テーマ切替
- メインエリアでチャットメッセージの表示・送信
- メッセージ送信時、デモAI応答を2秒後に自動表示
- チャットセッションの追加・削除
- ファイル添付機能（複数ファイル対応）
- カスタム猫アイコン（Okamichan）の実装
- ダーク/ライトテーマ対応のファビコン
- レスポンシブ対応

### 技術スタック
- **Next.js 15**（App Router）
- **React 19**
- **TypeScript**
- **Tailwind CSS 4**
- **shadcn/ui**（Radix UIベースのUIコンポーネント）
- **Lucide React**（アイコン）
- **next-themes**（ダーク/ライトモード切替）

### UI構成
- **サイドバー**：左端固定、チャット履歴・新規作成・設定・アカウント・テーマ切替ボタン
- **メインエリア**：中央にカスタム猫アイコン・説明文・タイトル・メッセージボックス、履歴があればチャットバブル表示
- **ダーク/ライトモード**：サイドバー下部のボタンで即時切替
- **ファイル添付**：メッセージ入力欄にファイル添付ボタン、複数ファイル対応

### 今後の拡張性
- バックエンドAPI（OpenAI等）と連携し、リアルタイムAI応答やSSE/WS対応が可能
- 音声入力、プロンプトテンプレート等の追加も容易
- ユーザー認証や永続的な履歴保存も拡張可能
- ファイル添付機能は既に実装済み

---

## ディレクトリ構成と主な役割

```
ai-chat-ui/
├── src/
│   ├── app/           # Next.jsのApp Router用ディレクトリ（ページ・レイアウト・グローバルCSS）
│   │   ├── page.tsx   # メインページ（チャットUIのルート）
│   │   ├── layout.tsx # 全体レイアウト・メタデータ・ThemeProvider
│   │   ├── icon.tsx   # ファビコン生成（動的SVG）
│   │   └── globals.css# グローバルCSS（Tailwind・カスタムスタイル）
│   ├── components/    # UIコンポーネント群
│   │   ├── sidebar.tsx      # サイドバー（履歴・新規・設定・テーマ切替）
│   │   ├── chat.tsx         # メインチャットエリア全体
│   │   ├── chat-message.tsx # チャットバブル（1メッセージ表示）
│   │   ├── chat-input.tsx   # メッセージ入力欄（ファイル添付機能付き）
│   │   ├── theme-provider.tsx # ダーク/ライトモード切替用Provider
│   │   └── ui/              # shadcn/uiベースの再利用UI部品
│   │       └── okamichan-icon.tsx # カスタム猫アイコンコンポーネント
│   ├── types/         # 型定義
│   │   └── chat.ts    # チャットメッセージ・セッション型
│   └── lib/           # ユーティリティ関数
│       └── utils.ts   # クラス結合などのユーティリティ
├── public/            # 画像・アイコン等の静的ファイル
│   ├── Okamichan_icon_light.svg # ライトテーマ用猫アイコン
│   └── Okamichan_icon_dark.svg  # ダークテーマ用猫アイコン
├── package.json       # 依存パッケージ・スクリプト
├── tailwind.config.ts # Tailwind CSS設定
├── postcss.config.mjs # PostCSS設定
└── README.md          # このドキュメント
```

### 機能とディレクトリ・ファイルの対応
- **チャットUI全体**：`src/app/page.tsx`, `src/components/chat.tsx`
- **サイドバー**：`src/components/sidebar.tsx`
- **チャットバブル**：`src/components/chat-message.tsx`
- **メッセージ入力欄（ファイル添付機能付き）**：`src/components/chat-input.tsx`
- **カスタム猫アイコン**：`src/components/ui/okamichan-icon.tsx`
- **ファビコン**：`src/app/icon.tsx`
- **ダーク/ライトモード切替**：`src/components/theme-provider.tsx`, `src/components/sidebar.tsx`
- **UI部品（ボタン等）**：`src/components/ui/`
- **型定義**：`src/types/chat.ts`
- **ユーティリティ**：`src/lib/utils.ts`
- **グローバルCSS**：`src/app/globals.css`
- **Tailwind設定**：`tailwind.config.ts`

---

## はじめに

開発サーバーを起動するには、以下のコマンドを実行してください：

```bash
cd ai-chat-ui
npm run dev
# または
yarn dev
# または
pnpm dev
# または
bun dev
```

ブラウザで [http://localhost:3000](http://localhost:3000) を開くと、Okamichanアプリが表示されます。

`app/page.tsx` を編集することで、ページ内容を変更できます。ファイルを保存すると自動でリロードされます。

このプロジェクトでは、Vercelの新しいフォントファミリー [Geist](https://vercel.com/font) を [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) 機能で最適化・自動読み込みしています。

## さらに学ぶ

Next.jsについて詳しく知りたい場合は、以下の公式リソースをご覧ください：

- [Next.js ドキュメント（日本語）](https://nextjs.org/docs?hl=ja) - Next.jsの機能やAPIについて
- [Next.js チュートリアル（英語）](https://nextjs.org/learn) - インタラクティブな学習教材

Next.jsのGitHubリポジトリもご覧いただけます：[https://github.com/vercel/next.js](https://github.com/vercel/next.js)

## Vercelでデプロイ

Next.jsアプリを最も簡単にデプロイする方法は、[Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) を利用することです。

デプロイ方法の詳細は [Next.js デプロイ公式ドキュメント](https://nextjs.org/docs/app/building-your-application/deploying?hl=ja) をご覧ください。
