/**

 * Author's letter — /about SEO page (Japanese bundle)

 */



import { CONTACT_EMAIL, SITE_NAME, SITE_URL } from '../../lib/site'



export const AUTHOR_LETTER_CANONICAL = `${SITE_URL}/about`



export const AUTHOR_LETTER_META_TITLE = `作者の手記 · ${SITE_NAME}が存在する理由 | 芸術のオーラと創作`



export const AUTHOR_LETTER_META_DESCRIPTION =

  'Jingweiが存在する理由についての手記：ヴァルター・ベンヤミンの芸術のオーラ、AI時代の信頼の危機、画像に人間の痕跡を残すこと、一つの石を投げる意味。'



export const AUTHOR_LETTER_DATE_PUBLISHED = '2026-06-01'

export const AUTHOR_LETTER_DATE_MODIFIED = '2026-06-14'



export const AUTHOR_LETTER_INTRO = {

  kicker: '作者の手記',

  title: 'クリエイターへの手紙',

  lead: `ここに辿り着いたすべての方へ。これは製品マニュアルではありません。${SITE_NAME}を作った理由です。`,

  updated: '2026年6月',

}



export const AUTHOR_LETTER_PARAGRAPHS: readonly string[] = [

  '10年前、断片化した情報や映画、写真を当たり前だと思っていた頃、私は一世紀前のベンヤミンを本当には理解していませんでした。彼が述べたこと、すなわち作品が特定の瞬間、特定の場所、オリジナルに属するということ、名付けにくいが確かに存在するオーラについて。作品がほとんど劣化なく無限に複製できるようになったとき、そのオーラはどう薄れていくのか、本当に心配もしていませんでした。',

  'そして私は、AI時代の信頼の危機に頭から突き落とされました。',

  '数え切れない作品が、切り抜き、圧縮、再投稿、アップロードを繰り返し、際限なく広がっていきます。最も不安にさせられたのは、その過程でクリエイターがいかに簡単に消されていくかということです。作品は動き続けますが、作者との結びつきは薄れていきます。最終的には人そのものが剥がされ、呼び出せるスタイルや表面、結果だけが残ります。',

  '複製のコストがほぼゼロになり、情報が限りなく増殖するこの新しい時代において、誰もがあらゆる情報にどれだけ「生きた人間の存在」が残っているかを問い、同時に、実在する特定の人の痕跡を一切持たないまま、より人間らしく見えるものを競い合っています。',

  '絵画はどの時代も最初に衝撃を受けるように感じられ、AI時代も例外ではありません。しかし答えもそこから最初に育つかもしれません。写真が現れたとき、絵画は置き換えられると思われました。機械印刷やインターネットが作品の流通を変えたとき、芸術は無限に複製可能なメディアによって薄められるのではないかと恐れる人もいました。それでも芸術は終わりませんでした。むしろ各衝撃の後、より深い問いに近づいていきます。オーラはどこから来るのか、複製や伝達の形式では置き換えられないものは何か、と。',

  '特に上手く描けない私にとって、今何かを始めようとするたびに自問します。AIが1秒でより正確で、より洗練された画像を生成できるなら、なぜ私はまだ始めるのか。このためらいが最も私を不安にさせます。この信頼の危機で最も恐れるのは、遅く、不完全で、ためらいさえある創作のプロセス自体に、まだ意味があると信じているかどうかです。',

  'かつて私たちが守ろうとしたのが作品のオーラだったなら、今日より難しいのは人のオーラを守ることかもしれません。人のオーラは、ためらい、選択、持続、修正、やり直しに残る痕跡から来るのではないかと思います。結果が一瞬で置き換えられると分かっていても始めようとする衝動から来るのではないか、と。精卫はその文脈の中に現れました。技術を止めるためでも、未来を拒むためでもありません。流通の中を作品が移動するときも、依然としてこの情報を携え続けたいだけです。「これは特定の人間によって作られ、こう扱ってほしい。」その保存が不完全でも、たとえもう一つ、かすかで明確な痕跡を残すだけでも、それは価値があると私は思います。',

  '今日当たり前に見える多くのルールは、少数の人の持続から始まり、やがて皆が共有する言語になったものです。著作権もそうでした。CCマーカーもそうでした。帰属、許可、境界に関するすべての取り組みも同様でした。',

  '精卫は海を埋め尽くせないと分かっていながら、石をくわえ、波に投げ込みます。シーシュポスは岩が再び転がり落ちると分かっていながら、山へ押し上げ続けます。神はバベルの塔を作り、言語と方向を散らしました。それでも世界の異なる隅で、異なる時代に、人々は似たことをし続けます。同じ結果に到達できるからではなく、異なる場所で似た選択をするからです。それが、私にとっては不器用な人間の英雄性です。そして人間の星が輝く瞬間でもあります。',

  'そして精卫は、私の石です。',

]



export const AUTHOR_LETTER_CTA = {

  title: 'あなたも石を投げたいなら',

  links: [

    { to: '/protect', label: '作品を保護する' },

    { to: '/protocol', label: 'JW宣言を読む' },

    { to: '/faq', label: 'よくある質問' },

  ] as const,

  contact: `ご質問は ${CONTACT_EMAIL} まで`,

}



export function buildAuthorLetterJsonLd(): Record<string, unknown> {

  const body = AUTHOR_LETTER_PARAGRAPHS.join('\n\n')

  return {

    '@context': 'https://schema.org',

    '@type': 'Article',

    headline: AUTHOR_LETTER_INTRO.title,

    description: AUTHOR_LETTER_META_DESCRIPTION,

    url: AUTHOR_LETTER_CANONICAL,

    inLanguage: 'ja',

    datePublished: AUTHOR_LETTER_DATE_PUBLISHED,

    dateModified: AUTHOR_LETTER_DATE_MODIFIED,

    author: {

      '@type': 'Organization',

      name: SITE_NAME,

      url: SITE_URL,

    },

    publisher: {

      '@type': 'Organization',

      name: SITE_NAME,

      url: SITE_URL,

    },

    articleBody: body,

    about: [

      'image attribution',

      'creators in the AI era',

      'aura of art',

      'Walter Benjamin',

      'Jingwei Declaration',

      'Creative Commons',

    ],

  }

}

