/** FAQ - single source for /faq SEO page + FAQPage JSON-LD */

import { CONTACT_EMAIL, SITE_NAME, SITE_URL } from '../../lib/site'

export const FAQ_META_TITLE = `よくある質問 | ${SITE_NAME} · 防AI洗い落とし · 追跡可能な透かし`

export const FAQ_META_DESCRIPTION =
  'Jingweiとは？Glaze / Nightshadeとの違いは？画像は保存される？スクリーンショットでも検証できる？クイック署名の使い方、サンプル画像の再利用可否。2026年8月更新。'

export const FAQ_DATE_MODIFIED = '2026-08-30'

export const FAQ_INTRO = {
  title: 'よくある質問',
  lead: `${SITE_NAME}は、イラスト・写真・デザイン向けの画像帰属保護です。投稿や納品の前に jwprotect.com/protect を開き、JW宣言と任意の可視防盗レイヤーを書き込みます。1枚およそ30秒。深層学習は使いません。処理後にサーバーから削除します。以下は、検索でよく聞かれる形の問いです。`,
  updated: '2026年8月30日',
}

export type FaqAnswerBlock =
  | string
  | { type: 'list'; items: string[] }

export interface FaqItem {
  id: string
  question: string
  answer: FaqAnswerBlock[]
  relatedLinks?: readonly { to: string; label: string }[]
}

export interface FaqCategory {
  id: string
  title: string
  items: FaqItem[]
}

export function faqPlainAnswer(blocks: FaqAnswerBlock[]): string {
  return blocks
    .map(b => {
      if (typeof b === 'string') return b
      return b.items.map(i => `- ${i}`).join('\n')
    })
    .join('\n')
}

export const FAQ_CATEGORIES: FaqCategory[] = [
  {
    id: 'what',
    title: 'Jingweiとは',
    items: [
      {
        id: 'what-is-jingwei',
        question: 'Jingweiとは何ですか？画像はどう保護しますか？',
        answer: [
          `${SITE_NAME}は個人クリエイター向けの画像帰属保護ツールです。jwprotect.com に PNG / JPEG / WebP を上げ、検証可能なJW宣言を書き、必要なら可視の盗難防止レイヤーを重ねます。1枚およそ30秒。登録は不要です。`,
          '保護ページの初期値はクイック署名です。位移・エンボス・ぼかし帯などを自分で切り替えるなら手動調整へ。検証は、今ダウンロードしたPNGを上げてください。',
        ],
        relatedLinks: [
          { to: '/protect', label: '保護ページを開く' },
          { to: '/protocol', label: 'JW宣言を読む' },
        ],
      },
      {
        id: 'why-jingwei-vs-glaze-nightshade',
        question: 'Jingweiは Glaze や Nightshade と何が違いますか？',
        answer: [
          'Glaze と Nightshade は、公開後に大量スクレイピングされて学習へ回る場面が主対象です。Jingwei は、相手がすでにファイルを持ち、AI編集・合成・部分再描画をする場面が主対象です。三つは併用できます。',
          {
            type: 'list',
            items: [
              'Glaze / Nightshade：ローカルアプリ、強いGPUが必要なことが多く、1枚が遅く、摂動が見えやすい',
              'Jingwei：ブラウザ、古典的な画像処理、深層学習のモデルファイルは読み込まない',
              '共通の限界：将来のすべてのツールが失敗する保証はない。原ファイルは残す',
            ],
          },
        ],
        relatedLinks: [{ to: '/protect', label: '作品を保護する' }],
      },
      {
        id: 'no-retain-no-ai',
        question: 'Jingweiは画像を保存しますか？AIで処理しますか？',
        answer: [
          '長期保存しません。AI処理もしません。Protect / Verify / AI Inspect Assist に上げた画像は、処理が終わるとすぐにサーバーから削除します。作品ライブラリは作らず、学習や商用分析にも使いません。',
          '埋め込みは古典的な画像処理とデジタル信号処理です。深層学習は呼びません。.pth / .onnx / .ckpt も読み込みません。プライバシーポリシーを見てください。',
        ],
        relatedLinks: [
          { to: '/privacy', label: 'プライバシーポリシー' },
          { to: '/terms', label: '利用規約' },
        ],
      },
    ],
  },
  {
    id: 'effect',
    title: '効果と限界',
    items: [
      {
        id: 'ai-fusion-limits',
        question: '透かしを入れれば AI 合成や学習を永久に防げますか？',
        answer: [
          '防げません。強い圧縮、何度も再保存、狙い撃ちの除去で、不可視レイヤーは弱くなったり消えます。可視レイヤーはきれいな復元のコストを上げます。将来のすべてのツールが失敗する保証はありません。',
          'JW宣言は Creative Commons に近い、機械可読の意思マークにしたい、という長期の方向です。法律の代わりにはなりません。',
        ],
        relatedLinks: [{ to: '/protocol', label: 'JWについて詳しく' }],
      },
      {
        id: 'anti-ai-edit',
        question: 'JingweiはAI編集や画像合成を防げますか？',
        answer: [
          'Jingwei が対象にするのは、相手がすでに画像を持ち、AI編集や合成にかける場合です。多層の摂動と可視の盗難防止レイヤーで、きれいな復元を難しくし、悪用コストを上げます。',
          '結果は原画、ツール、後処理で変わります。2026年8月の実測对比は実測マトリクスにあります。',
        ],
        relatedLinks: [
          { to: '/protect', label: '保護オプションを選ぶ' },
          { to: '/guide/watermark-matrix', label: '実測マトリクスを見る' },
        ],
      },
      {
        id: 'quality-formats',
        question: '対応形式は？画質は落ちますか？',
        answer: [
          'アップロードは PNG、JPEG、WebP です。JW など不可視の周波数レイヤーを入れるなら PNG で書き出してください。JPEG の非可逆圧縮は不可視信号を弱めます。',
          'JW、DWT、LSB は日常の閲覧では目立ちにくくしています。強くすると薄い纹理が出ることがあります。位移、エンボス、ぼかし帯は意図して絵を変えます。EXIF や C2PA は見た目をほぼ変えません。まずは中〜弱でプレビューしてください。',
        ],
      },
    ],
  },
  {
    id: 'verify',
    title: '検証と追跡',
    items: [
      {
        id: 'screenshot-verify',
        question: 'スクリーンショットやSNSから再ダウンロードした画像でも検証できますか？',
        answer: [
          '部分的にはできます。JW宣言と追跡レイヤーには、スクリーンショット、SNS圧縮、二次保存向けの冗長があります。よくある流れは、保護→スクリーンショット→投稿→再ダウンロード→検証です。',
          '多くの場合は帰属が読めますが、毎回ではありません。Verify は JW、DWT、LSB、アンカーごとに信頼度を出します。争いになるなら、一度も拡散していない書き出しを残してください。',
        ],
        relatedLinks: [{ to: '/verify', label: 'Verifyページを開く' }],
      },
      {
        id: 'how-to-verify',
        question: '画像にJingweiの透かしデータがあるか、どう確認しますか？',
        answer: [
          'jwprotect.com/verify を開き、対象画像を上げます。ログイン不要です。JW宣言、DWT、LSB、EXIF/IPTC、C2PA を調べ、レイヤーごとに検出と信頼度を出します。',
          '検出なしは、処理されなかった証明ではありません。検出ありは、精卫で保護された、または関連メタデータがある、という補助になります。PNGの静止画を上げてください。ホロカードの動画フレームは使わないでください。',
        ],
        relatedLinks: [{ to: '/verify', label: 'Verifyへ' }],
      },
      {
        id: 'source-inspection',
        question: '「AI Inspect Assist」は、その絵がAI作かどうか判定できますか？',
        answer: [
          '最終判定は出しません。AI Inspect Assist は成分表です。AIツールのメタデータ、カメラEXIF、C2PA などがあるかを示し、判断はあなたがします。',
          'SNS経由のファイルやスクリーンショットでは、これらの痕跡が落ちることが多いです。「見つからない」は「人間が描いた」ではありません。',
        ],
        relatedLinks: [{ to: '/inspect', label: 'AI Inspect Assist（ベータ）' }],
      },
    ],
  },
  {
    id: 'usage',
    title: '使い方と設定',
    items: [
      {
        id: 'quick-credit',
        question: 'クイック署名とは何ですか？日常投稿ではどう使いますか？',
        answer: [
          'クイック署名は保護ページの初期値です。作者名を入れると、検証可能な不可視JW宣言を書き、画面に合わせて薄い文字か軽い変位署名を選びます。ロゴは薄い印を1つだけ。日常投稿はおよそ30秒。登録不要です。',
          'クイック署名と手動はスライダーを共有しません。レイヤーを自分で切り替え、ロゴ位置を決め、全面位移・エンボス・顔ロックを重ねるなら手動へ。検証は今ダウンロードしたPNGを上げてください。',
        ],
        relatedLinks: [
          { to: '/protect', label: '保護ページを開く' },
          { to: '/blog/quick-credit-mode', label: 'クイック署名の使い方' },
        ],
      },
      {
        id: 'holo-card',
        question: 'ホロカードとは何ですか？動画で検証できますか？',
        answer: [
          'ホロカードは保護後の静止画を反射する箔カードにし、およそ6秒のMP4として書き出します。虹色や粒子は反射帯の中だけに出ます。',
          'クリップでは検証しないでください。PNGを上げてください。サイト上の見本にホバーすれば、書き出さなくても箔面をプレビューできます。',
        ],
        relatedLinks: [
          { to: '/protect', label: '保護してホロカードをダウンロード' },
          { to: '/blog/jingwei-holo-card', label: 'ホロカードの説明' },
        ],
      },
      {
        id: 'watermark-font',
        question: '透かしのフォントは変更できますか？',
        answer: [
          'いま使えるのはオープンライセンスのフォントだけです。別ファミリーへの切り替えはまだありません。サイズ、位置、可視レイヤーのスタイルは変えられます。フォントが増えたら、保護ページと本FAQで知らせます。',
        ],
      },
      {
        id: 'jw-declaration',
        question: 'JW宣言とは何ですか？必須ですか？',
        answer: [
          'JW（Jingwei Protocol）は、創作タイプ（オリジナル / AI協作）、使用制限（無許可のAI学習やAI編集の禁止など）、作者名を機械可読で画像に書き、任意で見えるバッジを出せます。',
          'JWがCCマーカーのように、プラットフォームが読める公開シグナルになることを目指しています。業界の合意が必要で、必須ではありません。不可視レイヤーを残したいなら PNG で書き出してください。',
        ],
        relatedLinks: [{ to: '/protocol', label: 'JW宣言全文を読む' }],
      },
      {
        id: 'delivery-feature',
        question: '「Commission Delivery（納品配信）」とは何ですか？',
        answer: [
          '完成稿を上げて閲覧パスワードを設定し、暗号化された納品パッケージを作ります。依頼者は本サイトでパッケージを開き、パスワードを入れ、マウスかタッチを押し続けて初めて絵が徐々に見えます。離すと散ります。',
          '閲覧者の識別を示す、ゆっくり動く透かしも重なります。スクリーンショットで高解像度の完成稿をそのまま持って行きにくくします。スマホでもタッチできます。複雑な操作はパソコンの方が楽です。',
        ],
        relatedLinks: [{ to: '/delivery', label: 'Commission Delivery' }],
      },
      {
        id: 'sample-images-license',
        question: 'サイトやリポジトリの猫・犬・マトリクス見本を、自分の絵として使ってよいですか？',
        answer: [
          '使えません。見本は保護効果の説明用です。コードは MIT、見本画像の著作権は原作者と精卫に残ります。表紙、素材、学習データ、二次創作の下絵にしてはいけません。',
          '別名保存は技術的に止められません。MIT だから写真を商用で持っていける、という主張を認可が止めます。保護のテストは自分の作品で行ってください。',
        ],
        relatedLinks: [
          { to: '/guide/watermark-matrix', label: '実測マトリクスを見る' },
          { to: '/protect', label: '自分のファイルを保護' },
        ],
      },
    ],
  },
  {
    id: 'roadmap',
    title: '製品ロードマップ',
    items: [
      {
        id: 'open-source-and-app',
        question: 'Jingweiはオープンソースですか？モバイルアプリは出ますか？',
        answer: [
          '製品サイトのリポジトリは、まだ公開していません。Protect と Verify が安定したら、自前ホストできるオープンソースパッケージ（Docker優先）を出す計画です。コミュニティ、寄付、納品配信は製品サイトに残します。',
          'モバイルアプリは操作の作り直しとストア審査が要ります。いま計画はありません。ウェブ版を先に固めます。',
        ],
      },
    ],
  },
]

export const FAQ_ALL_ITEMS: FaqItem[] = FAQ_CATEGORIES.flatMap(c => c.items)

export function buildFaqJsonLd(): Record<string, unknown> {
  return {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    url: FAQ_CANONICAL,
    dateModified: FAQ_DATE_MODIFIED,
    mainEntity: FAQ_ALL_ITEMS.map(item => ({
      '@type': 'Question',
      name: item.question,
      acceptedAnswer: {
        '@type': 'Answer',
        text: faqPlainAnswer(item.answer),
      },
    })),
  }
}

export const FAQ_CTA = {
  title: 'まだ疑問がありますか？',
  body: `フィードバックページでメッセージを残すか、${CONTACT_EMAIL} までご連絡ください。保護はProtect、検証はVerifyからどうぞ。`,
  links: [
    { to: '/protect', label: '保護を始める' },
    { to: '/verify', label: 'ウォーターマークを検証' },
    { to: '/about', label: '作者の手記を読む' },
    { to: '/protocol', label: 'JW宣言を読む' },
    { to: '/feedback?from=faq', label: 'フィードバックを送る' },
  ] as const,
}

export const FAQ_CANONICAL = `${SITE_URL}/faq`
