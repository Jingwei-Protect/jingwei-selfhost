export const apiErrors = {
  dispTextRequired: '変位透かしを有効にする場合、透かしテキストは必須です',
  logoFileRequired: 'ロゴ透かしを有効にする場合、画像のアップロードが必要です',
  betaCodeRequired: '有効なベータコードが必要です',
  betaCodeInvalid: 'ベータコードが無効です',
  betaNotOpen: 'AI検査アシストのベータはまだ公開されていません。しばらくしてから再度お試しいただくか、サポートまでお問い合わせください。',
  serverError: 'サーバーエラー：{detail}',
  outputFailed: '出力に失敗しました：{detail}',
  previewFailed: 'プレビューに失敗しました：{detail}',
  holoCaptureUnavailable: 'ホロカードの録画は一時的に利用できません。しばらくしてから再試行してください。',
  holoCaptureFailed: 'ホロカードの録画に失敗しました：{detail}',
} as const
