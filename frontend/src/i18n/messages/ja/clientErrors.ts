export const clientErrors = {
  networkFailed: 'ネットワーク接続に失敗しました。接続を確認して再度お試しください。ローカル開発中の場合は、先にバックエンドを起動してください。',
  requestFailed: 'リクエストに失敗しました（{status}）',
  apiNotFound: 'APIエンドポイントが見つかりません。バックエンドが起動しているか確認してください',
  loadFileFailed: 'ファイルを読み込めませんでした',
} as const
