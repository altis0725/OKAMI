# React Error #31 修正記録

## 問題の詳細

### エラー内容
```
Error: Minified React error #31; visit https://react.dev/errors/31?args[]=object%20with%20keys%20%7Braw%2C%20pydantic%2C%20json_dict%2C%20tasks_output%2C%20token_usage%7D
```

このエラーは「Objects are not valid as a React child」を意味し、Reactコンポーネントがオブジェクトをそのままレンダリングしようとした際に発生する。

### 発生状況
- メッセージ送信は成功
- バックエンドからレスポンスが返却される
- レスポンス表示時にクライアントサイドエラーが発生

## 原因分析

OKAMIバックエンドAPIのレスポンス構造：
```json
{
  "task_id": "task_xxxxx",
  "status": "completed",
  "result": {
    "raw": "実際のレスポンステキスト",
    "pydantic": null,
    "json_dict": null,
    "tasks_output": [...],
    "token_usage": {...}
  },
  "error": null,
  "execution_time": 30.66
}
```

問題は`data.result`がオブジェクトであり、直接Reactコンポーネントで表示できないことだった。

## 修正内容

`/Users/altis/Documents/crewAI/OKAMI/webui/nextjs-chat/src/app/page.tsx`の133-136行目：

```typescript
// 修正前
const aiMessage: Message = {
  content: data.result || 'レスポンスがありません',
  // ...
};

// 修正後
const responseContent = typeof data.result === 'object' && data.result !== null 
  ? (data.result.raw || JSON.stringify(data.result))
  : (data.result || 'レスポンスがありません');

const aiMessage: Message = {
  content: responseContent,
  // ...
};
```

## 修正のポイント

1. **型チェック**: `result`がオブジェクトか文字列かを判定
2. **安全なアクセス**: オブジェクトの場合は`raw`フィールドを取得
3. **フォールバック**: `raw`が存在しない場合はJSON文字列化
4. **後方互換性**: 文字列の場合はそのまま使用

## テスト結果

修正後、以下の動作を確認：
- メッセージ送信が正常に動作
- レスポンスが正しく表示される
- エラーが発生しない

## 今後の改善点

- エラーハンドリングの強化
- レスポンス構造の型定義追加
- より詳細なログ出力の実装