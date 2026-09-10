export const clientErrors = {
  networkFailed: 'ネットワーク接続に失敗しました。接続を確認して再度お試しください。ローカル開発中の場合は、先にバックエンドを起動してください。',
  holoNetworkFailed: 'ホロカードの書き出しに失敗しました。接続を確認して再度お試しください。',
  holoResultExpired: '保護画像の有効期限が切れました。もう一度保護してからホロカードをダウンロードしてください。',
  holoTooLarge: '保護画像が大きすぎてホロカードを書き出せません。小さい写真で試してください。',
  requestFailed: 'リクエストに失敗しました（{status}）',
  apiNotFound: 'APIエンドポイントが見つかりません。バックエンドが起動しているか確認してください',
  loadFileFailed: 'ファイルを読み込めませんでした',
} as const
