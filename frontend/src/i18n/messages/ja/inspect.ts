import { inspectReport } from './inspectReport'

export const inspect = {
  betaBadge: 'ベータ',
  title: 'AI検査アシスト',
  metaDescription:
    '精衛 AI検査アシスト（ベータ）：画像をアップロードして補助的な手がかりを確認——来歴、ファイル構造、ピクセル統計。最終判定は行いません。クリエイター参考用のみ。',
  subtitle: '画像をアップロードし、レポート内の補助的な手がかりを確認（最終判定なし）',
  principlesCard: {
    title: 'この分析の仕組み',
    intro: 'このページでは、ファイルから読み取れる手がかり——来歴証明、保存情報、ファイル構造、ピクセル統計——を一覧にした分析レポートを出します。',
  },
  unlock: {
    intro: 'AI検査アシストはクローズドベータ中です。管理者から提供されたベータコードを入力してください。',
    codeLabel: 'ベータコード',
    codePlaceholder: 'ベータコードを入力',
    checking: '確認中…',
    enter: 'ベータに入る',
    invalid: 'ベータコードが無効です',
  },
  principles: {
    expand: '展開：仕組みの説明',
    collapse: '折りたたむ：仕組みの説明',
    bodyLead:
      'このページでは、ファイルから読み取れる手がかり——来歴証明、保存情報、ファイル構造、ピクセル統計——を一覧にした分析レポートを出します。画像がAI生成かどうかの最終判定は行いません。以下の各項目は、各自で照合してください。',
    bodyBullet1:
      '各項目には基本分析と、何が見つかったかが示されます。右上の赤い表示は、より強い手がかりです。',
    bodyBullet2:
      '項目が見つからないことは、逆説明にはなりません。SNS経由の画像は再圧縮で情報が消えることが多く、「見つからない」は「手描き確定」ではありません。',
    interpretationLabel: '解釈',
    statsHint: '統計的ヒント（参考のみ）',
    metricsTitle: '生の測定値',
  },
  actions: {
    recheck: '再チェック',
    checking: 'チェック中…',
  },
  loading: {
    reading: '来歴証明とメタデータを読み取り中…',
    failed: '検査に失敗しました',
    network: 'ネットワークエラー',
  },
  strengthLabels: {
    strong: '強い証拠',
    medium: '構造的な手がかり',
    weak: '統計的参考',
  },
  summaryHint: '上の3つの数値は方向性のある証拠の件数であり、AI確率スコアではありません。',
  summaryDetail: '3つの数値は方向性のある証拠項目のみです。チェックしたが結論が出なかった項目は除外されます。これは「AI確率」スコアではありません——赤い「AI関連」フラグのみがより強い関連を示します。',
  itemStatus: {
    forensicsFound: 'ヒントのみ · 参考',
    forensicsNotFound: '異常のヒントなし',
    found: '記録あり',
    notFound: '見つかりません',
  },
  meaning: {
    aiRelevant: 'この項目：AI画像生成に関連する客観的な手がかり（他の項目と比較してください）',
    found: 'この項目：記録あり——解釈メモを参照',
    notFound: 'この項目：手がかりが見つかりません',
  },
  report: inspectReport,
} as const
