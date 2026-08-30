(function () {
  var STORAGE_KEY = 'jingwei-locale'
  var TRADITIONAL_ZH = { TW: 1, HK: 1, MO: 1 }
  var SIMPLIFIED_ZH_TZ = { 'Asia/Shanghai': 1, 'Asia/Chongqing': 1, 'Asia/Urumqi': 1, 'Asia/Harbin': 1 }
  var TRADITIONAL_ZH_TZ = { 'Asia/Taipei': 1, 'Asia/Hong_Kong': 1, 'Asia/Macau': 1 }

  var COPY = {
    'zh-Hans': {
      htmlLang: 'zh-CN',
      homeTitle: '免费防AI洗图水印工具 · 精卫 Jingwei',
      homeDescription:
        '免费在线 · 防 AI 洗图盗图 · 无需注册。发稿前约 30 秒：可见防盗层 + 隐形 JW 声明，让 AI 洗图更难、盗图更亏。',
      shellTag: '精卫 Jingwei · jwprotect.com',
      shellHeading: '免费防AI洗图水印工具 · 精卫 Jingwei',
      shellBody:
        '免费在线 · 防 AI 洗图盗图 · 无需注册。发稿前约 30 秒：可见防盗层 + 隐形 JW 声明，让 AI 洗图更难、盗图更亏。',
      nav: {
        protect: '开始保护作品',
        verify: '验证水印',
        protocol: '阅读 JW 声明',
        faq: '常见问题',
        community: '精卫之海',
        delivery: '约稿交付',
        privacy: '隐私政策',
        terms: '用户服务与免责声明',
      },
      noscriptHeading: '免费防AI洗图水印工具 · 精卫 Jingwei',
      noscriptBody:
        '免费在线 · 防 AI 洗图盗图 · 无需注册。发稿前约 30 秒：可见防盗层 + 隐形 JW 声明，让 AI 洗图更难、盗图更亏。',
      notFound: {
        title: '页面未找到 · 精卫 Jingwei',
        heading: '找不到这个页面',
        body: '链接可能已失效，或地址输入有误。你可以返回首页继续保护或验证作品。',
        home: '返回首页',
        protect: '保护作品',
        verify: '验证水印',
        faq: '常见问题',
      },
    },
    'zh-Hant': {
      htmlLang: 'zh-Hant',
      homeTitle: '免費防AI洗圖浮水印工具 · 精衛 Jingwei',
      homeDescription:
        '免費線上 · 防 AI 洗圖盜圖 · 無需註冊。發稿前約 30 秒：可見防盜層 + 隱形 JW 聲明，讓 AI 洗圖更難、盜圖更虧。',
      shellTag: '精衛 Jingwei · jwprotect.com',
      shellHeading: '免費防AI洗圖浮水印工具 · 精衛 Jingwei',
      shellBody:
        '免費線上 · 防 AI 洗圖盜圖 · 無需註冊。發稿前約 30 秒：可見防盜層 + 隱形 JW 聲明，讓 AI 洗圖更難、盜圖更虧。',
      nav: {
        protect: '開始保護作品',
        verify: '驗證浮水印',
        protocol: '閱讀 JW 聲明',
        faq: '常見問題',
        community: '精衛之海',
        delivery: '約稿交付',
        privacy: '隱私政策',
        terms: '用戶服務與免責聲明',
      },
      noscriptHeading: '免費防AI洗圖浮水印工具 · 精衛 Jingwei',
      noscriptBody:
        '免費線上 · 防 AI 洗圖盜圖 · 無需註冊。發稿前約 30 秒：可見防盜層 + 隱形 JW 聲明，讓 AI 洗圖更難、盜圖更虧。',
      notFound: {
        title: '頁面未找到 · 精衛 Jingwei',
        heading: '找不到這個頁面',
        body: '連結可能已失效，或地址輸入有誤。你可以返回首頁繼續保護或驗證作品。',
        home: '返回首頁',
        protect: '保護作品',
        verify: '驗證浮水印',
        faq: '常見問題',
      },
    },
    en: {
      htmlLang: 'en',
      homeTitle: 'Free anti-AI wash-out watermark tool · Jingwei',
      homeDescription:
        'Free online · Anti-AI wash-out · No signup required. Protect in ~30 seconds: visible anti-theft layers + invisible JW claims, harder to wash out, harder to steal.',
      shellTag: 'Jingwei · jwprotect.com',
      shellHeading: 'Free anti-AI wash-out watermark tool · Jingwei',
      shellBody:
        'Free online · Anti-AI wash-out · No signup required. Protect in ~30 seconds: visible anti-theft layers + invisible JW claims, harder to wash out, harder to steal.',
      nav: {
        protect: 'Protect your work',
        verify: 'Verify watermark',
        protocol: 'Read JW declaration',
        faq: 'FAQ',
        community: 'Jingwei Sea',
        delivery: 'Commission delivery',
        privacy: 'Privacy policy',
        terms: 'Terms & disclaimer',
      },
      noscriptHeading: 'Free anti-AI wash-out watermark tool · Jingwei',
      noscriptBody:
        'Free online · Anti-AI wash-out · No signup required. Protect in ~30 seconds: visible anti-theft layers + invisible JW claims, harder to wash out, harder to steal.',
      notFound: {
        title: 'Page not found · Jingwei',
        heading: 'Page not found',
        body: 'The link may be broken or the address mistyped. Return home to protect or verify your work.',
        home: 'Home',
        protect: 'Protect work',
        verify: 'Verify watermark',
        faq: 'FAQ',
      },
    },
    ja: {
      htmlLang: 'ja',
      homeTitle: '無料 AI洗い落とし透かしツール · 精衛 Jingwei',
      homeDescription:
        '無料オンライン · AI洗い落とし対策 · 登録不要。約30秒で保護：可視レイヤー + 不可視 JW 宣言、洗い落としを難しく、盗用の損失を大きく。',
      shellTag: '精衛 Jingwei · jwprotect.com',
      shellHeading: '無料 AI洗い落とし透かしツール · 精衛 Jingwei',
      shellBody:
        '無料オンライン · AI洗い落とし対策 · 登録不要。約30秒で保護：可視レイヤー + 不可視 JW 宣言、洗い落としを難しく、盗用の損失を大きく。',
      nav: {
        protect: '作品を保護',
        verify: '透かしを検証',
        protocol: 'JW宣言を読む',
        faq: 'よくある質問',
        community: '精衛の海',
        delivery: '納品保護',
        privacy: 'プライバシーポリシー',
        terms: '利用規約・免責事項',
      },
      noscriptHeading: '無料 AI洗い落とし透かしツール · 精衛 Jingwei',
      noscriptBody:
        '無料オンライン · AI洗い落とし対策 · 登録不要。約30秒で保護：可視レイヤー + 不可視 JW 宣言、洗い落としを難しく、盗用の損失を大きく。',
      notFound: {
        title: 'ページが見つかりません · 精衛 Jingwei',
        heading: 'ページが見つかりません',
        body: 'リンクが無効か、住所の入力に誤りがある可能性があります。ホームに戻って保護または検証を続けてください。',
        home: 'ホーム',
        protect: '作品を保護',
        verify: '透かしを検証',
        faq: 'よくある質問',
      },
    },
  }

  function localeFromGenericZh() {
    try {
      var tz = Intl.DateTimeFormat().resolvedOptions().timeZone
      if (TRADITIONAL_ZH_TZ[tz]) return 'zh-Hant'
      if (SIMPLIFIED_ZH_TZ[tz]) return 'zh-Hans'
    } catch (e) { /* ignore */ }
    return 'zh-Hans'
  }

  function localeFromLanguageTag(tag) {
    var lower = String(tag || '').trim().replace(/_/g, '-').toLowerCase()
    if (!lower) return null
    if (lower === 'zh-cn' || lower === 'zh-hans' || lower.indexOf('zh-cn') === 0) return 'zh-Hans'
    if (
      lower === 'zh-tw' || lower === 'zh-hk' || lower === 'zh-mo' || lower === 'zh-hant'
      || lower.indexOf('zh-tw') === 0 || lower.indexOf('zh-hk') === 0 || lower.indexOf('zh-mo') === 0
    ) {
      return 'zh-Hant'
    }
    if (lower === 'zh' || lower.indexOf('zh-') === 0) return localeFromGenericZh()
    if (lower.indexOf('en') === 0) return 'en'
    if (lower === 'ja' || lower.indexOf('ja-') === 0) return 'ja'
    return null
  }

  function localeFromUrl() {
    try {
      var params = new URLSearchParams(window.location.search)
      var lang = params.get('lang')
      if (lang === 'zh-Hans' || lang === 'zh-Hant' || lang === 'en' || lang === 'ja') return lang
    } catch (e) { /* ignore */ }
    return null
  }

  function detectShellLocale() {
    var fromUrl = localeFromUrl()
    if (fromUrl) return fromUrl
    try {
      var saved = localStorage.getItem(STORAGE_KEY)
      if (saved === 'zh-Hans' || saved === 'zh-Hant' || saved === 'en' || saved === 'ja') return saved
    } catch (e) { /* ignore */ }
    var langs = (navigator.languages && navigator.languages.length)
      ? navigator.languages
      : [navigator.language]
    for (var i = 0; i < langs.length; i++) {
      var hit = localeFromLanguageTag(langs[i])
      if (hit) return hit
    }
    return 'en'
  }

  function setMeta(attr, name, value) {
    var el = document.querySelector('meta[' + attr + '="' + name + '"]')
    if (el) el.setAttribute('content', value)
  }

  function applyHomeShell(locale) {
    var c = COPY[locale] || COPY.en
    document.documentElement.lang = c.htmlLang
    document.title = c.homeTitle
    setMeta('name', 'description', c.homeDescription)
    setMeta('property', 'og:title', c.homeTitle)
    setMeta('property', 'og:description', c.homeDescription)
    setMeta('name', 'twitter:title', c.homeTitle)
    setMeta('name', 'twitter:description', c.homeDescription)

    var shell = document.getElementById('static-shell')
    if (shell) {
      var p = shell.querySelector('header p')
      if (p) p.textContent = c.shellTag
      var h1 = shell.querySelector('h1')
      if (h1) h1.textContent = c.shellHeading
      var paragraphs = shell.querySelectorAll('p')
      if (paragraphs.length >= 2) paragraphs[1].textContent = c.shellBody
      var links = shell.querySelectorAll('nav a')
      var order = ['protect', 'verify', 'protocol', 'faq', 'community', 'delivery', 'privacy', 'terms']
      for (var i = 0; i < links.length && i < order.length; i++) {
        links[i].textContent = c.nav[order[i]]
      }
    }

    var noscript = document.querySelector('noscript')
    if (noscript) {
      noscript.innerHTML =
        '<div style="max-width:40rem;margin:2rem auto;padding:0 1.25rem;font-family:system-ui,sans-serif;line-height:1.75;color:#333">'
        + '<h1 style="font-size:1.5rem;margin-bottom:0.75rem">' + c.noscriptHeading + '</h1>'
        + '<p>' + c.noscriptBody + '</p>'
        + '<p><a href="/protect">' + c.nav.protect + '</a> · <a href="/verify">' + c.nav.verify
        + '</a> · <a href="/protocol">' + c.nav.protocol + '</a> · <a href="/faq">' + c.nav.faq + '</a></p>'
        + '</div>'
    }
  }

  function applyNotFound(locale) {
    var c = COPY[locale] || COPY.en
    var nf = c.notFound
    document.documentElement.lang = c.htmlLang
    document.title = nf.title
    var h1 = document.getElementById('nf-heading')
    var body = document.getElementById('nf-body')
    if (h1) h1.textContent = nf.heading
    if (body) body.textContent = nf.body
    var links = {
      'nf-home': nf.home,
      'nf-protect': nf.protect,
      'nf-verify': nf.verify,
      'nf-faq': nf.faq,
    }
    Object.keys(links).forEach(function (id) {
      var el = document.getElementById(id)
      if (el) el.textContent = links[id]
    })
  }

  var locale = detectShellLocale()
  if (document.getElementById('static-shell')) {
    applyHomeShell(locale)
  }
  if (document.getElementById('nf-heading')) {
    applyNotFound(locale)
  }

  window.jingweiShellLocale = { detectShellLocale: detectShellLocale, applyHomeShell: applyHomeShell, applyNotFound: applyNotFound }
})()
