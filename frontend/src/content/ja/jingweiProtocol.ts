/** Jingwei Protocol - copy, glossary, story, limits, belief, and letters. */

import { SITE_URL } from '../../lib/site'

export const JW_PROTOCOL_CANONICAL = `${SITE_URL}/protocol`
export const JW_PROTOCOL_META_DESCRIPTION =
  '精卫宣言（JW）：機械可読な画像帰属と使用意図、周波数領域の不可視ウォーターマーク、創作タイプ、NO-TR/NO-ED制限、CCおよびC2PAとの関係。'
export const JW_PROTOCOL_DATE_MODIFIED = '2026-06-14'

// CC symbols and consensus language

export const JW_CC_SYMBOL_HISTORY = {
  kicker: 'JW以前',
  title: '©からCCへ：シンボルが創作の利用方法をどう変えたか',
  lead: 'JW以前から、クリエイターは世代を超えてシンボルで、作品をどのように使えるかを定義してきました。',
  paragraphs: [
    '著作権シンボル © は印刷時代に始まりました。ページに所有者がいることを読者に伝えます。しかしクリエイターには「すべての権利を留保する」以上の必要がありました。「クレジット表示のうえ利用可」「共有可だが商用改変は不可」といった意思表示も必要でした。',
    '2002年、Creative Commons（CC）はその意図を、BY、NC、ND、SAなど、世界共通のマーカーにしました。全文の法律文を読まなくても、何が開放され、何が制限されているかが分かるようになりました。',
    'そのシンボル群はエコシステムを急速に変えました。FlickrでCCフィルタが可能になり、Wikipediaはデフォルトでオープンライセンスを採用し、検索エンジンがライセンスタイプを認識し始め、再投稿時に統一された帰属形式が生まれました。十分な数のクリエイターが同じシンボルを使うと、侵害の前にプラットフォームは執行可能なシグナルを得られます。',
    '合意は規模によって力を持ちます。1枚の画像上の声明だけでは脆いですが、何千もの作品が共通言語を持つと、ツール、プラットフォーム、ユーザーはそれをデフォルトの規範として扱い始めます。',
    'AI時代には新たな空白が生じます。画像がスクリーンショット、再エンコード、学習パイプラインに取り込まれると、隣接するラベルは消え得ます。ピクセルに埋め込まれ、機械可読で、画像自体と一緒に持ち運べる宣言が必要です。JWは同じ道を続けます。目に見えるシンボルが合意を築き、不可視の符号化が再配布を越えてその合意を生かします。',
  ],
}

// Jingwei story (single source to avoid duplicate rendering)

export type JwStoryParagraph = { text: string; lead?: boolean }

export const JW_STORY_ZH: JwStoryParagraph[] = [
  {
    text: '中国の伝説では、精卫（きょうい）という名の少女が広大な東海で溺れ、鳥として生まれ変わりました。羽の一片のように小さく、意志は折れません。',
  },
  {
    text: '彼女は山の石を海に投げ込み、二度と誰も害されないように海を埋め尽くすと誓いました。日々、一つの石をくわえ、轟く波へ投げ込みました。',
  },
  {
    text: '今日、海は形を変えました。それは終わりのないデータの流れです。同意なくコピー、改変、再配布され、途中で帰属が消されていく作品。この新しい海に向き合う私たちは、精卫と同じくらい小さく感じるかもしれません。',
  },
  {
    text: 'JWはあなたの石です。ウォーターマークであり、機械可読な所有権宣言です。一つの石は小さく見えます。しかし十分な数のクリエイターが一緒に石を投げ続ければ、この海は再び境界を取り戻し、すべてのクリエイターの名前が載る余地を持てるようになります。',
    lead: true,
  },
]

/** One-line teaser for meta/cards. Do not render together with full story paragraphs. */
export const JW_STORY_TEASER_ZH = JW_STORY_ZH[0].text

export const JW_STORY = [
  '中国の伝説では、精卫という名の少女が広大な東海で溺れ、羽の一片のように小さく、意志は折れない鳥として生まれ変わりました。',
  '彼女は山の石を海に投げ込み、二度と誰も害されないように海を埋め尽くすと誓いました。日々、一つの石をくわえ、轟く波へ投げ込みました。',
  '今日、海は形を変えました。それは終わりのないデータの洪水です。同意なくコピー、改変、再配布され、途中で帰属が消されていく作品。この新しい海に向き合う私たちは、精卫と同じくらい小さく感じるかもしれません。',
  'JWはあなたの石です。ウォーターマークであり、機械可読な所有権宣言です。一つの石は小さく見えます。しかし十分な数のクリエイターが一緒に石を投げ続ければ、この海は再び境界を取り戻し、すべてのクリエイターの名前が載る余地を持てるようになります。',
]

export const JW_STORY_TEASER = JW_STORY[0]

/** @deprecated Use JW_STORY_ZH. */
export const JW_STORY_FULL_ZH = JW_STORY_ZH

/** @deprecated Use JW_STORY_TEASER_ZH, and do not duplicate with JW_STORY_ZH. */
export const JW_STORY_SHORT_ZH = JW_STORY_TEASER_ZH

/** @deprecated Use JW_STORY. */
export const JW_STORY_FULL = JW_STORY

/** @deprecated Use JW_STORY_TEASER. */
export const JW_STORY_SHORT = JW_STORY_TEASER

// Creation type

export type JwCreationType = 'OC' | 'AI'

export const JW_CREATION_OPTIONS: { id: JwCreationType; label: string; labelZh: string; desc: string; descZh: string }[] = [
  {
    id: 'OC',
    label: 'OC — オリジナル創作',
    labelZh: 'Original Creation',
    desc: '本作品は、署名された人間のクリエイターによるオリジナル創作です（媒体は問いません）。',
    descZh: 'This work is originally created by the named human creator (any medium).',
  },
  {
    id: 'AI',
    label: 'AI — AI協作',
    labelZh: 'AI-Assisted',
    desc: '創作過程でAIツールを使用しました。人間のクリエイターが著作権を保持し、制限を設定します。',
    descZh: 'AI tools were used in the process; the human creator retains authorship and sets the restrictions.',
  },
]

// Restriction flags

export const JW_RESTRICTION_FLAGS: {
  id: string
  bit: number
  abbrev: string
  label: string
  labelZh: string
  desc: string
  descZh: string
}[] = [
  {
    id: 'NO-TR',
    bit: 0,
    abbrev: 'NO-TR',
    label: 'AI学習禁止',
    labelZh: 'No AI Training',
    desc: 'クリエイターは、本画像をAIモデルの学習またはファインチューニングに使用することを許可していません。',
    descZh: 'The creator has not authorized this image for AI model training or fine-tuning.',
  },
  {
    id: 'NO-ED',
    bit: 1,
    abbrev: 'NO-ED',
    label: 'AI編集禁止',
    labelZh: 'No AI Edit',
    desc: 'クリエイターは、本画像のAIによる改変（インペインティング、img2img、全面再描画など）を許可していません。人間による模写や学習は、このフラグの対象外です。',
    descZh: 'The creator has not authorized AI-based modification of this image (inpainting, img2img, full redraw, etc.). Human study or imitation is not covered by this flag.',
  },
]

/** Legacy flag display labels, used for verification of older embedded payloads. */
export const JW_RESTRICTION_LEGACY_LABELS: Record<string, string> = {
  'NO-RM': 'ウォーターマーク除去禁止（旧）',
  'NO-RX': '二次創作禁止（旧）',
  'NO-NC': '商用利用禁止（旧）',
}

/** Returns restriction labels in this Japanese bundle (new + legacy compatible). */
export function jwRestrictionLabel(abbrev: string): string {
  const found = JW_RESTRICTION_FLAGS.find(f => f.abbrev === abbrev)
  if (found) return found.label
  return JW_RESTRICTION_LEGACY_LABELS[abbrev] || abbrev
}

// Intro copy

export const JW_PROTECT_INTRO =
  '精卫宣言を有効にすると、不可視の周波数領域ウォーターマークと任意の目に見えるバッジを含め、所有権と使用意図を画像に埋め込めます。クリエイター名は下の「著作権メタデータ」セクションから読み取り、マニフェストとファイルメタデータに書き込まれます。不可視ウォーターマークレイヤーを保持するには、PNGエクスポートを推奨します。'

export const JW_PROTECT_PIXEL_REWARD = {
  title: '作品を保護して精卫の海の日次クォータを増やす',
  bullets: [
    'ログイン後、JW宣言付きで正常に保護された各画像が、JW作品の合計にカウントされます。',
    '初回有効化で、日次受け取りが10セルから50セルに増えます。',
    '保護作品が1つ増えるごとに、1日あたり+5セル、最大150セル/日まで増えます。',
    '精卫の海で「今日のクォータを受け取る」をクリックして受け取ってください（1日1回）。',
  ],
  loginHint: 'ログインなしでも画像を保護できますが、クォータの増加はカウントされません。先にサインインしてください。',
}

export const JW_PNG_HINT = 'JW宣言を有効にする場合、PNG形式を推奨します。JPEG圧縮は不可視ウォーターマークレイヤーを弱める可能性があります。'

/** Protect page Manual mode hint (consistent wording: visible overlay). */
export const JW_STEALTH_MODE_HINT =
  '各層を自分でオンにし、パラメータも自分で決めます。自動レシピはありません。ロゴの位置・大きさ・濃さは自由に調整できます。'

// Protection limits

export const JW_PROTECT_LIMITS = {
  title: 'この保護でできること・できないこと',
  paragraphs: [
    'JW宣言は、機械可読な所有権と使用意図を画像に埋め込みます。クリエイター名、創作タイプ、利用設定は、視覚への影響を最小限に抑えつつ周波数領域に書き込まれます。一般的なSNS圧縮、スクリーンショット、軽い編集を乗り越えるよう設計されており、再配布後も帰属を検出できるようにしています。',
  ],
  bullets: [
    {
      strong: '絶対的なロックではありません。',
      body: '不可視ウォーターマークは、高強度の再描画、深度インペインティング、専門的な除去ツールによって弱体化または除去される可能性があります。堅牢性の向上は継続しますが、100%の持続性を約束することはできません。',
    },
    {
      strong: '即座の抑止が目的なら、',
      body: '不可視レイヤーだけでは不十分です。手動調整に切り替えて、変位ウォーターマーク、顔エンボスロック、エンボステクスチャなど、被写体の輪郭に影響する可視オーバーレイを追加してください。無許可の利用者が高い復元コストを払わざるを得なくなります。',
    },
  ],
}

export const JW_DWT_RELATION = {
  protectHint:
    'JW宣言は、可能な限り平坦な色領域を保ちつつ、詳細の多い領域に不可視データを書き込みます。必要に応じてフォールバック方式を使用します。PNGエクスポートを推奨します。',
  verifyJwNote:
    'JW宣言を通じて周波数領域の所有権データが検出されました。本画像には、独立したDWT追跡レイヤーは含まれていません。',
  verifyStandaloneDwtTitle: 'DWT周波数ウォーターマーク',
  verifyStandaloneDwtHint:
    'JW宣言の所有権マニフェストとは別に設定された、独立した機械可読追跡テキストレイヤーです。',
}

export type JwImageKind = 'flat' | 'mixed' | 'rich'

export type JwWriteHint = {
  kind: JwImageKind
  flat_ratio: number
  texture_ratio: number
  summary: string
  suggest: string
  credit_disp_x?: number
  credit_disp_y?: number
  credit_disp_w?: number
  credit_disp_h?: number
}

export const JW_INVISIBLE_INTRO =
  'システムは、変更に気づきにくい領域に自動的に精卫宣言データを書き込みます。平坦な色領域が大きい画像では、下部に白い余白を追加し、PNGでエクスポートすることを検討してください。'

/** @deprecated API always uses auto; kept for typing legacy responses. */
export type JwEmbedPriority = 'auto' | 'color' | 'balanced' | 'verify'

export const JW_EMBED_METHOD_LABEL: Record<string, string> = {
  invisible: '不可視埋め込み',
  lsb: 'フォールバック埋め込み',
}

// Verification limits

export const JW_VERIFY_LIMITS = {
  title: '検証の信頼度の読み方',
  paragraphs: [
    '本ページは、アップロードされた画像からすべての精卫保護レイヤーの抽出を試み、利用可能な場合はファイルメタデータからC2PA Content Credentialsを読み取ります。検出された場合、画像が精卫宣言で処理された、または検証可能な来歴クレデンシャルを含むことを示し、帰属および所有権の主張を支援できます。',
  ],
  bullets: [
    {
      strong: '検出されない＝保護されていなかった、ではありません。',
      body: '強い全面再描画（完全な再生成や深度インペインティングなど）はピクセル内容を再構成し、不可視ウォーターマークの痕跡の大部分を除去する可能性があります。そのような操作が行われた後、証拠を保持することはできません。',
    },
    {
      strong: '検出結果には信頼度の段階があります。',
      body: 'チェックサムを含む高信頼度の完全デコードが最も強力です。暗号学的に署名されたC2PA証拠は、一般に周波数領域シグナルより強力です。あいまい一致は参考情報のみです。紛争時は、これらの出力をメタデータ、創作記録、オリジナルファイルと組み合わせてください。',
    },
  ],
}

export const JW_C2PA_NOTE = {
  title: 'C2PAと精卫',
  bullets: [
    {
      strong: '補完関係。',
      body: 'C2PAはメタデータに保存され、SNS再配布時に除去される可能性があります。JWはピクセルの周波数データに埋め込まれます。共存し、互いに補完できます。C2PAがある場合は優先し、JWをフォールバック証拠として活用してください。',
    },
    {
      strong: '信頼できる証明書。',
      body: 'Adobe/SNSプラットフォームでContent Credentialsを表示するには、一般に信頼されたCA発行のC2PAまたはCAWGアイデンティティ証明書が必要です。開発者テスト証明書は内部テストに有用ですが、公開プラットフォームでは信頼されない場合があります。',
    },
  ],
}

// Core belief

export const JW_CORE_BELIEF = {
  title: 'それでも精卫宣言を埋め込む価値がある理由',
  paragraphs: [
    '不可視ウォーターマークは、破壊不能なロックではありません。AI再描画、深度インペインティング、強い圧縮、除去ツールによって弱体化または消去される可能性があります。不可視レイヤーだけでは、すべての再配布と二次編集を越えて持続することを保証できないため、目に見える宣言レイヤーの追加を推奨します。',
    '精卫のより深い目標は、統一された機械可読なクリエイター宣言標準です。「AI学習禁止」「AI編集禁止」がプロフィール文や画像キャプションだけに存在する場合、プラットフォームやモデルが大規模に検出・執行するのは困難です。精卫シンボルがCCマーカーのように広く認知され、最終的にプラットフォーム、検索エンジン、AIシステムに読み取り可能で執行可能な公開シグナルとして受け入れられることを望んでいます。',
    '精卫宣言は、海に投げ込む最初の石です。',
  ],
}

/** Protect/Verify page summary; full version lives on /protocol. */
export const JW_CORE_BELIEF_SUMMARY = {
  title: 'それでも精卫宣言を埋め込む価値がある理由',
  paragraphs: [
    '不可視ウォーターマークは、破壊不能なロックではありません。AI再描画、深度インペインティング、強い圧縮、除去ツールによって弱体化または消去される可能性があります。不可視レイヤーだけでは、すべての再配布と二次編集を越えて持続することを保証できないため、目に見える宣言レイヤーの追加を推奨します。',
    '精卫のより深い目標は、統一された機械可読なクリエイター宣言標準です。「AI学習禁止」「AI編集禁止」がプロフィール文や画像キャプションだけに存在する場合、プラットフォームやモデルが大規模に検出・執行するのは困難です。精卫シンボルがCCマーカーのように広く認知され、最終的にプラットフォーム、検索エンジン、AIシステムに読み取り可能で執行可能な公開シグナルとして受け入れられることを望んでいます。',
    '精卫宣言は、海に投げ込む最初の石です。',
  ],
  linkLabel: '精卫宣言の全文を読む →',
  linkTo: '/protocol',
}

// Tool commitments

export const JW_TOOL_PROMISE = {
  title: '本ツールはAIモデルを使用しません',
  paragraphs: [
    '本ツールのすべてのウォーターマーク（不可視の周波数領域マーク（DWT / DCT / Block-DC）、目に見えるバッジ、変位効果、顔エンボスオーバーレイ）は、古典的なデジタル信号処理のみで実装されており、AI推論への依存はありません。',
    '画像はブラウザからアップロードされ、サーバーはウォーターマークデータの埋め込みと結果の即時返却にのみ使用します。',
    'お客様の作品を、自社または第三者のいかなるAI学習セット、生成モデル、機械学習データセットにも投入することはありません。',
    '私たちの役割は、作品に機械可読な所有権声明を書き込むお手伝いをすることだけです。どのように使われるか、AIが学習できるかどうかは、依然としてお客様の判断です。',
  ],
}

// Angie letters (three styles)

export type LetterStyle = 'narrative' | 'declaration' | 'poetic'

export interface JwLetter {
  id: LetterStyle
  styleLabel: string
  title: string
  paragraphs: string[]
  signature: string
}

export const JW_LETTER_VERSIONS: JwLetter[] = [
  {
    id: 'narrative',
    styleLabel: '物語 · 温かみ',
    title: 'あなたへの最後のひと言',
    paragraphs: [
      'Angieです。',
      '精卫を作り始めたとき、誰かと戦おうとしていたわけではありません。私もAIを使います。コーディング、アイデア整理、時には伴侶としても。',
      'ある日、友人の作品がAIで改変されるのを見ました。髪型が変わり、表情が差し替えられ、署名が消され、別のプラットフォームに再投稿され、「AIをコピーした」と非難されました。彼女はその作品に3週間を費やしていました。',
      'その瞬間、一つだけはっきりしました。技術は速く動いても、「誰かが本当の時間をかけて作った」という文は、途中で消えてはいけない、と。',
      '精卫宣言が行うのは、小さなことです。各画像に機械可読な一行を残します。「これは人間が作ったものです。特定し、尊重してください。」すべてを止めることはできませんし、すべての強力な復元パイプラインに勝てるわけでもありません。ただ、その文が聞こえるチャンスを与えるだけです。',
      '次の作品に載せてくださるなら、それをまた一緒に投げる石だと受け取ります。',
      '海が完全に埋まることはありません。しかし一つ一つの石が、少しだけ海を後退させます。',
    ],
    signature: '— Angie、2026年、長い思索の後の深夜',
  },
  {
    id: 'declaration',
    styleLabel: '静か · 宣言',
    title: 'これを読んでいるすべての方へ',
    paragraphs: [
      '精卫を作ったのは、誰かに反対するためではありません。',
      'AIは、私を含め誰の働き方も本当に変えた、稀有な技術の一つだと認識しています。',
      'しかし一つだけ覚えておくべきことがあります。各画像、各段落、各曲の背後には、具体的な時間をかけて創作した、特定の人がいる、と。',
      '精卫宣言が行う小さなことは、各画像に機械可読な一文を残すことです。「これは人間の創作です。特定し、尊重してください。」',
      'すべてを遮断することはできません。しかし十分な数の画像がこの文を携えるとき、AIシステムを含め、誰も「見なかったふり」をし続けることはできなくなります。',
      '一つの石は小さい。石を積み重ねれば、海は覚えています。',
    ],
    signature: '— Angie、2026年',
  },
  {
    id: 'poetic',
    styleLabel: '詩的 · 比喩',
    title: '石',
    paragraphs: [
      '私はよくあの鳥のことを思い出します。',
      '彼女は海を倒すことを期待していなかった。毎日、一つの石をくわえ、水の上を飛び、放し、落ちるのを見て、また戻った。',
      '海は決して完全には埋まらないと分かっていたのだと思います。彼女が実践していたのは計算ではなく、持続でした。「ここにいた。これを見た。同意しない。」という姿勢です。',
      '今日の海は形を変えましたが、海は依然として海です。私たちの時間、選択、意図は洗い流され、許可なく集められ、別の名前のもと別の場所で再生されます。',
      '精卫宣言は、私が作れる限りで、その石に最も近いものです。海を空にはしませんし、AIを止めもしません。ただ、あなたの名前を作品にもう少し深く書き込み、次の波がそれを消しにくくします。',
      'この石も運んでくださるなら、海を埋め尽くすことはできないかもしれません。しかし一つ一つの石が、海にもう一人の人間の名前を教えます。',
    ],
    signature: '— Angie、2026年、眠れない夜',
  },
]

/** Letter version used on protocol page. */
export const JW_ACTIVE_LETTER_ID: LetterStyle = 'narrative'

export function getActiveLetter(): JwLetter {
  return JW_LETTER_VERSIONS.find(v => v.id === JW_ACTIVE_LETTER_ID) ?? JW_LETTER_VERSIONS[0]
}

// Badge string preview

/** Example badge strings (logo + abbrev placeholders, bottom-right). */
export function formatBadgePreview(creation: JwCreationType, restrictions: string[]): string {
  const parts = ['JW', creation, ...restrictions.slice(0, 3)]
  return parts.join(' · ')
}
