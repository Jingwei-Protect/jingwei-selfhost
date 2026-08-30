import { SITE_URL } from '../../../lib/site'
import type { BlogIndexCopy, BlogPost } from '../types'

const G = '/showcase/guide'
const L_PROTECTED = '精卫で保護後'
const L_AI = 'AI 修復試行後'

export const BLOG_CANONICAL = `${SITE_URL}/blog`

export const BLOG_INDEX: BlogIndexCopy = {
  canonical: BLOG_CANONICAL,
  metaTitle: 'ブログ · AI 洗い落としと帰属保護 | 精卫',
  metaDescription:
    '旧式透かしがなぜ効かないか。可視レイヤーの選び方。イラスト・デザイン・写真向けの説明と実測マトリクス。',
  title: 'ブログ',
  lead: 'クイック署名の使い方、ホロカードのダウンロード、可視レイヤー案内と実測マトリクス。',
}

const C = '/showcase/credit'
const H = '/showcase/holo'

export const BLOG_POSTS: BlogPost[] = [
  {
    slug: 'quick-credit-mode',
    datePublished: '2026-08-29',
    dateModified: '2026-08-29',
    metaTitle: 'クイック署名とは？30秒で検証可能な透かし | 精卫ブログ',
    metaDescription:
      '精卫のデフォルト「クイック署名」：作者名を入れると検証可能なJW宣言を書き込み、画面に合わせて薄い印を自動選択。約30秒、登録不要。',
    intro: {
      kicker: '使い方',
      title: 'クイック署名とは？30秒で作品に検証可能な身分証を書く',
      lead:
        'クイック署名は精卫 Jingwei（jwprotect.com）のデフォルト保護モードです。作者名を入れると、検証可能な不可視JW宣言を書き込み、画面に合わせて薄い可視印を自動で選びます。日常投稿は約30秒、登録不要、処理後にファイルは削除されます。',
      updated: '2026年8月',
    },
    heroMedia: {
      kind: 'compare',
      protectedSrc: `${C}/credit-dog-before.png?v=upload1`,
      aiRestoredSrc: `${C}/credit-dog-after.png?v=upload1`,
      protectedAlt: '透かし前の子犬イラスト',
      aiRestoredAlt: 'クイック署名の変位文字を入れた子犬',
      protectedLabel: '原図',
      aiRestoredLabel: 'クイック署名 · 変位文字',
      caption: 'テクスチャのある画面は軽い変位署名。全図ではほぼ同じに見えます（変わる画素は約1%）。下の顔アップで、Jingwei が面の中央にあります。',
    },
    paragraphs: [
      '「無料で透かし」「AIに透かしを消されない方法」で検索しても、詰まるのは理論より手順の多さです。クイック署名はその近道：先に身分証を書き、絵は投稿できる清潔さに保ちます。',
    ],
    sections: [
      {
        heading: 'クイック署名とは何ですか？',
        paragraphs: [
          'クイック署名は保護ページのデフォルトです。作者名を入れると精卫宣言（JW）がオンになり、名前・創作タイプ・利用制限を機械可読で画像に書き込みます。同時にごく薄い可視印を足し、「保護済み」と分かるようにしつつ、角ロゴのようにAIが独立物体として切り取りやすい形にはしません。',
        ],
      },
      {
        heading: '手動調整との違いは？',
        paragraphs: [
          'クイック署名と手動調整はスライダーを共有しません。「手動のつまみを隠しただけ」ではありません。',
          'クイック署名：名前を入れるとJWを書きます。可視印は固定の薄い配方で、画面に合わせて薄い文字か軽い変位（自分で指定も可）。ロゴは薄い印を1つだけ。全面変位、エンボス、ぼかし帯、顔ロックのスイッチはなく、ロゴの位置や濃さも自分では決めません。目的は約30秒で投稿でき、絵を汚しすぎないことです。',
          '手動調整：レイヤーのオンオフもスライダーも自分で決めます。ロゴを指定の角へ、変位を全面に、エンボスや顔ロックを実測マトリクスに合わせて重ねるなら手動です。クイック署名で見る薄い文字／変位は、手動ページの強度スライダーではありません。',
        ],
      },
      {
        heading: '使い方は？3ステップ',
        paragraphs: [
          '保護ページを開き、クイック署名のまま PNG / JPEG / WebP をアップロードします（iPhoneは先にJPG書き出し）。作者名を入れ、任意で画面署名やロゴを追加。「保護を開始」してPNGを保存。約30秒。AIモデルは使いません。サーバーは処理後に削除します。',
        ],
      },
      {
        heading: '変位文字の例：テクスチャのある子犬',
        paragraphs: [
          '「自動」は毛並みや花びらをテクスチャと見て、軽い変位署名（フォント約7%、ずれ3px、薄い影＝実験のc024）になりやすいです。文字は貼り付けた色面ではなく、元画素を少し押してJingweiの形にします。赤枠が、この見本で印が乗った位置です。',
        ],
        media: [
          {
            kind: 'compare',
            protectedSrc: `${C}/credit-dog-face-before.png?v=upload1`,
            aiRestoredSrc: `${C}/credit-dog-face-after.png?v=upload1`,
            protectedAlt: '原図の顔アップ。毛並みはまだ押されていない',
            aiRestoredAlt: 'c024の顔アップ。毛並みがJingweiの形に押されている',
            protectedLabel: '原図 · 顔アップ',
            aiRestoredLabel: 'c024 · 顔アップ',
            caption: '実験で使った子犬の署名はこれです。青い花の上の印ではなく、顔の画素を少し押してJingweiにしています。',
          },
          {
            kind: 'single',
            src: `${C}/credit-dog-where.png?v=upload1`,
            alt: '子犬の変位文字位置図：顔の中央のJingweiを赤枠で示す',
            caption: '位置図：赤枠が顔の中央の印です。',
          },
        ],
      },
      {
        heading: '薄い文字の例：平坦な猫',
        paragraphs: [
          'ベタ塗りや大きな色面は別ルートです。ごく薄い全面の点／文字に加え、中央に点状の署名。これは保護ページの本物の薄い文字配方の出力で、手動のコントラストスライダーではありません。',
        ],
        media: [
          {
            kind: 'compare',
            protectedSrc: `${C}/credit-cat-before.png?v=siga1`,
            aiRestoredSrc: `${C}/credit-cat-after.png?v=siga1`,
            protectedAlt: '猫イラスト原図',
            aiRestoredAlt: '本物の薄い文字を入れた猫',
            protectedLabel: '原図（平坦なイラスト）',
            aiRestoredLabel: '薄い文字のあと',
            caption: '遠くからは元絵のまま。薄い印は全面にあり、猫とサメの主体を奪いません。',
          },
          {
            kind: 'compare',
            protectedSrc: `${C}/credit-cat-zoom-before.png?v=siga1`,
            aiRestoredSrc: `${C}/credit-cat-zoom-after.png?v=siga1`,
            protectedAlt: '原図の顔アップ。薄い文字なし',
            aiRestoredAlt: '保護後の顔アップ。細かい十字と点が見える',
            protectedLabel: '原図 · 顔アップ',
            aiRestoredLabel: '保護後 · 顔アップ',
            caption: '本物の薄い配方です。拡大すると小さな十字と点が見え、大きな文字シートではありません。',
          },
          {
            kind: 'single',
            src: `${C}/credit-cat-where.png?v=siga1`,
            alt: '猫の位置図：顔の中央の点状Jingweiを赤枠で示す',
            caption: '位置図：赤枠が点状サイン。枠の外にはさらに薄い全面の点があります。',
          },
        ],
      },
      {
        heading: '保護したあと、どう検証しますか？',
        paragraphs: [
          '今ダウンロードしたPNGを検証ページに上げます。ログイン不要。JW、周波数域、LSB、メタデータ、追跡アンカーを層ごとに報告します。「未検出」は未処理の証明ではありません。「検出」は精卫が触った補助証拠です。紛争時は再圧縮していない書き出しを残してください。',
        ],
      },
      {
        heading: 'クイック署名だけで止めてはいけないのはどんな時？',
        paragraphs: [
          '狙い撃ちの除去、顔入れ替え、部分再描画のコストを上げたいなら、手動調整に切り替えて全面変位、エンボス、ぼかし帯、顔ロックを足し、実測マトリクスで選んでください。クイック署名は「検証できて、絵を汚しすぎない」が優先で、最強の洗い落とし耐性ではありません。',
          '可能ならPNGで書き出してください。JPEGは不可視層を弱めることがあります。透明チャンネルをJPEGにしないでください。',
        ],
      },
    ],
    relatedLinks: [
      { to: '/protect', label: '保護ページでクイック署名を試す' },
      { to: '/verify', label: '今保存したファイルを検証' },
      { to: '/blog/jingwei-holo-card', label: 'ホロカードとは？' },
      { to: '/blog/how-to-use-jingwei-visible-layers', label: '可視レイヤーの選び方' },
    ],
  },
  {
    slug: 'jingwei-holo-card',
    datePublished: '2026-08-29',
    dateModified: '2026-08-29',
    metaTitle: 'ホロカードとは？箔面クリップのダウンロード | 精卫ブログ',
    metaDescription:
      '精卫ホロカードは保護後の静止画を反射する箔カードにし、約6秒のMP4にします。指紋状のモアレは反射帯の中だけに出ます。',
    intro: {
      kicker: '新機能',
      title: 'ホロカードとは？保護後の作品を、光るカードにする',
      lead:
        'ホロカードは精卫の見せ方レイヤーです。保護済みの静止画を傾けると光る箔カードにし、約6秒・8fpsのMP4として書き出します。SNS予告や依頼の見せ方に向きます。iPhoneのライブ写真ではなく、検証に上げるファイルでもありません。',
      updated: '2026年8月',
    },
    heroMedia: {
      kind: 'holo',
      cardSrc: `${H}/home-card.jpg?v=credit-faint-2`,
      videoSrc: `${H}/holo-card-demo.mp4`,
      alt: '精卫ホロカード完成品：ホバーで箔面、下は書き出し動画',
      caption: '上下とも同じ画角：上がホバーできるカード、下が書き出した約6秒のMP4。',
    },
    paragraphs: [
      '保護が終わったら「ホロカードをダウンロード」。ファイル名は元画像に従い、例は `cat_holo.mp4`。相手が見るのは動くカードで、平坦なプレビューJPEGではありません。',
    ],
    sections: [
      {
        heading: 'ホロカードと透かしPNGの違いは？',
        paragraphs: [
          'ホロカードは見せ方であり、新しい透かしアルゴリズムではありません。JWと可視印はすでに静止画に入っています。クリップはその静止画を箔で包むだけ：虹色のスイープ、同方向の細かいモアレ、まばらな細閃。反射していない角度では絵がはっきり見え、箔が画面全体を染めません。',
        ],
      },
      {
        heading: 'ホロカードはどうダウンロードしますか？',
        paragraphs: [
          'クイック署名または手動で保護し、PNGを保存。結果欄の「ホロカードをダウンロード」を押し、録画を待ちます（セルフホスト時はChromeが必要）。約6秒のMP4がWeibo、Xiaohongshu、X、Discord向けにできます。サイト上の見本にホバーするだけでも箔面をプレビューできます。',
        ],
      },
      {
        heading: '箔面には何が乗っていますか？',
        paragraphs: [
          '反射帯の中に3つあります。シアン—金—ピンクのスイープ。同じ向きのサブピクセル格子が干渉して指紋の稜線になる粒。まばらなキラキラ。マスクが粒を帯の中に閉じ込めます。リムはシルバーで、チャコールではありません。上の完成カードと動画を見れば十分で、静止画の分解図はありません。',
        ],
      },
      {
        heading: 'どこに投稿すべきで、何に使ってはいけませんか？',
        paragraphs: [
          '予告、ポートフォリオカード、依頼の見せ方には向きます。唯一の保管には向きません。検証はPNGを上げてください。動画のスクリーンショットは不可です。SNSの再エンコードで箔は柔らかくなります。それは圧縮であり、保護失敗ではありません。',
        ],
      },
    ],
    relatedLinks: [
      { to: '/protect', label: '作品を保護してホロカードをダウンロード' },
      { to: '/blog/quick-credit-mode', label: '先にクイック署名を読む' },
      { to: '/guide/watermark-matrix', label: '各層 vs AI洗い落とし' },
    ],
  },
  {
    slug: 'why-ai-image-theft-is-easy',
    datePublished: '2026-07-05',
    dateModified: '2026-07-06',
    metaTitle: '透かしを AI 洗い落としに耐えさせるには | 精卫ブログ',
    metaDescription:
      '角ロゴが AI に負ける理由。inpainting とは何か。可視＋不可視レイヤーの役割とガイド実測对比。',
    intro: {
      kicker: 'クリエイター向け',
      title: '透かしを AI 洗い落としに耐えさせるには',
      lead: '',
      updated: '2026 年 7 月',
    },
    heroMedia: {
      kind: 'compare',
      protectedSrc: `${G}/disp-repeat-protected.png`,
      aiRestoredSrc: `${G}/disp-repeat-ai-restored.png`,
      protectedAlt: '位移铺满重复、精卫保護後',
      aiRestoredAlt: '位移铺满重复、AI 修復試行後',
      protectedLabel: L_PROTECTED,
      aiRestoredLabel: L_AI,
      caption: '位移 · 铺满重复：AI が署名を消した後も赤枠に塗り残しや色块が残る。',
    },
    paragraphs: [
      '透かしを付けたのに、簡単に消されて持ち去られる。そんな経験は多いはずです。以前は Photoshop で一つ一つ重ね、チャンネルやマスクも覚える必要があり、学習コストは低くありませんでした。今は AI ツールに放り込めば、一言で数秒で消して埋め直せます。',
      '問題は「透かしがあったかどうか」ではなく、透かしが旧来の発想のままかどうかです。貼るだけ、規則正しい、はっきり見える、画面と分離している。AI 洗い落としはその弱点を突きます。',
    ],
    sections: [
      {
        heading: '旧式透かしが効かなくなった理由',
        paragraphs: [
          '規則正しすぎる：角ロゴ、著作権バー、固定位置の小さなマーク。AI は大量の例を見ており、一括検出・一括除去が可能です。',
          'はっきりしすぎて分離している：見せるための透かしは下の絵と離れがち。AI は異物として抜き、空いた部分だけ修復します。',
          '情報量が少ない：数文字や小アイコンは像素情報が少ない。消したあと周囲の纹理・色から埋めると、元々なかったように見えます。',
        ],
      },
      {
        heading: '洗い落としとは、AI が作品を「修復」すること',
        paragraphs: [
          '核心は inpainting：不要な領域をマスクし、周囲から生成。角ロゴ除去、全面タイルの微調整、端切り＋アウトペイントなどが典型です。',
          '上の头图は「铺满重复」位移の実測です。左が保護後、右が AI 修復試行後。赤枠は完全復元ではなく、消しきれない破綻です。',
        ],
      },
      {
        heading: '精卫の二層構え',
        paragraphs: [
          '可視防盗レイヤーは画面を微观改造し、変更を像素構造に溶け込ませます。AI が無理に処理すると歪み・模糊・ノイズが残りやすい。浮雕・模糊条・顔エンボスなどの実測は次の記事とマトリクスへ。',
          '不可視 JW 宣言と周波数透かしは圧縮やスクショ後も検証可能。きれいな盗用が心配なら可視を。帰属証明が心配なら JW と DWT を。',
        ],
        media: [
          {
            kind: 'compare',
            protectedSrc: `${G}/emboss-protected.png`,
            aiRestoredSrc: `${G}/emboss-ai-restored.png`,
            protectedAlt: 'エンボス纹理、保護後',
            aiRestoredAlt: 'エンボス、AI 修復後',
            protectedLabel: L_PROTECTED,
            aiRestoredLabel: L_AI,
            caption: 'エンボス纹理：斜線纹を平坦化すると修復の破綻が残りやすい。',
          },
        ],
      },
    ],
    relatedLinks: [
      { to: '/guide/watermark-matrix', label: '実測マトリクス' },
      { to: '/blog/how-to-use-jingwei-visible-layers', label: '可視レイヤーの選び方' },
      { to: '/protect', label: '作品を保護' },
    ],
  },
  {
    slug: 'how-to-use-jingwei-visible-layers',
    datePublished: '2026-07-05',
    dateModified: '2026-08-28',
    metaTitle: '精卫の使い方：可視レイヤーの選び方 | 精卫ブログ',
    metaDescription:
      '位移・ハーフトーン・エンボス・模糊条・顔エンボス：用法、场景、JW 不可視レイヤーとの叠加。ガイド実測对比。',
    intro: {
      kicker: '使用ガイド',
      title: '精卫の使い方：可視レイヤーの選び方',
      lead:
        '角ロゴだけに頼らないでください。精卫は通常二層：可視で洗い落としを抑え、不可視で帰属を残す。各効果にガイド実測を付けています。',
      updated: '2026 年 7 月',
    },
    heroMedia: {
      kind: 'compare',
      protectedSrc: `${G}/disp-tile-protected.png`,
      aiRestoredSrc: `${G}/disp-tile-ai-restored.png`,
      protectedAlt: '位移集中整词、精卫保護後',
      aiRestoredAlt: '位移集中整词、AI 修復試行後',
      protectedLabel: L_PROTECTED,
      aiRestoredLabel: L_AI,
      caption: '位移 · 集中整词',
    },
    paragraphs: [
      '保護ページでアップロードします。初期値は署名・クイックです。層を自分で組む場合は手動調整に切り替えてください。プレビューで破線枠をドラッグ、「プレビュー生成」、消しゴムで調整、書き出し。約 30 秒、処理後削除。',
    ],
    sections: [
      {
        heading: '位移透かし',
        paragraphs: [
          '署名領域の像素をわずかにずらし、画面に溶け込ませます。集中整词・随机分散・铺满重复の三種。署名は主体の輪郭や縁へ。',
        ],
        media: [
          {
            kind: 'compare',
            protectedSrc: `${G}/disp-tile-protected.png`,
            aiRestoredSrc: `${G}/disp-tile-ai-restored.png`,
            protectedAlt: '位移集中整词',
            aiRestoredAlt: '集中整词、AI 修復後',
            protectedLabel: L_PROTECTED,
            aiRestoredLabel: L_AI,
            caption: '集中整词',
          },
          {
            kind: 'compare',
            protectedSrc: `${G}/disp-scatter-protected.png`,
            aiRestoredSrc: `${G}/disp-scatter-ai-restored.png`,
            protectedAlt: '位移随机分散',
            aiRestoredAlt: '随机分散、AI 修復後',
            protectedLabel: L_PROTECTED,
            aiRestoredLabel: L_AI,
            caption: '随机分散',
          },
        ],
      },
      {
        heading: 'ハーフトーンと ASCII',
        paragraphs: [
          'ハーフトーンは細粒を背景高周波へ。ASCII は文字纹理で全面を覆う。通常視聴では許容範囲、AI 平坦化後は块面や断裂が残りやすい。',
        ],
        media: [
          {
            kind: 'compare',
            protectedSrc: `${G}/halftone-protected.png`,
            aiRestoredSrc: `${G}/halftone-ai-restored.png`,
            protectedAlt: 'ハーフトーン',
            aiRestoredAlt: 'ハーフトーン、AI 修復後',
            protectedLabel: L_PROTECTED,
            aiRestoredLabel: L_AI,
            caption: 'ハーフトーン',
          },
          {
            kind: 'compare',
            protectedSrc: `${G}/moire-protected.png`,
            aiRestoredSrc: `${G}/moire-ai-restored.png`,
            protectedAlt: 'ASCII 可視レイヤー',
            aiRestoredAlt: 'ASCII、AI 修復後',
            protectedLabel: L_PROTECTED,
            aiRestoredLabel: L_AI,
            caption: 'ASCII 文字',
          },
        ],
      },
      {
        heading: 'エンボス纹理',
        paragraphs: [
          '全图に軽い立体斜線纹。极简平涂には不向き。插画・写真・立绘向け。',
        ],
        media: [
          {
            kind: 'compare',
            protectedSrc: `${G}/emboss-protected.png`,
            aiRestoredSrc: `${G}/emboss-ai-restored.png`,
            protectedAlt: 'エンボス',
            aiRestoredAlt: 'エンボス、AI 修復後',
            protectedLabel: L_PROTECTED,
            aiRestoredLabel: L_AI,
            caption: 'エンボス纹理',
          },
        ],
      },
      {
        heading: 'ぼかし帯とぼかし块',
        paragraphs: [
          'ぼかし帯は横方向の半透明帯。納品プレビューや重要情報を隠す用途。下はぼかし帯の実測。',
          'ぼかし块はブラシで塗った色块で、「一条のぼかし帯」とは別レイヤーです。顔エンボスは保護ページの手動調整でプレビューしてください。',
        ],
        media: [
          {
            kind: 'compare',
            protectedSrc: `${G}/ascii-protected.png`,
            aiRestoredSrc: `${G}/ascii-ai-restored.png`,
            protectedAlt: 'ぼかし帯',
            aiRestoredAlt: 'ぼかし帯、AI 修復後',
            protectedLabel: L_PROTECTED,
            aiRestoredLabel: L_AI,
            caption: 'ぼかし帯',
          },
          {
            kind: 'compare',
            protectedSrc: `${G}/dots-protected.png`,
            aiRestoredSrc: `${G}/dots-ai-restored.png`,
            protectedAlt: 'ぼかし块',
            aiRestoredAlt: 'ぼかし块、AI 修復後',
            protectedLabel: L_PROTECTED,
            aiRestoredLabel: L_AI,
            caption: 'ぼかし块',
          },
        ],
      },
      {
        heading: 'どう叠加するか',
        paragraphs: [
          '常用：位移またはハーフトーン + JW + 周波数透かし。低调：不可視 + 追跡アンカー。',
          '完整对比は実測マトリクスへ。第一篇は「なぜ AI 洗い落としが容易か」、本篇は「レイヤーの選び方」。',
        ],
      },
    ],
    relatedLinks: [
      { to: '/guide/watermark-matrix', label: '実測マトリクス' },
      { to: '/protect', label: '保護ページ' },
      { to: '/verify', label: '透かし検証' },
    ],
  },
]

export function getBlogPost(slug: string): BlogPost | undefined {
  const id = BLOG_SLUG_ALIASES[slug] ?? slug
  return BLOG_POSTS.find(p => p.slug === id)
}

export function postCanonical(slug: string): string {
  return `${SITE_URL}/blog/${slug}`
}

export const BLOG_SLUG_ALIASES: Record<string, string> = {
  'how-jingwei-visible-layers-work': 'how-to-use-jingwei-visible-layers',
}
