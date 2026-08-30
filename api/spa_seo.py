"""Crawler-visible SPA SEO: canonical URLs and locale-specific home/route meta."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any, Final
LocaleId = str

_SUPPORTED_LOCALES: Final[frozenset[str]] = frozenset({"zh-Hans", "zh-Hant", "en", "ja"})

_TRADITIONAL_ZH_REGIONS: Final[frozenset[str]] = frozenset({"tw", "hk", "mo"})


@dataclass(frozen=True)
class LocaleSeoCopy:
    """Home-page SEO strings shown to crawlers before client JS runs."""

    locale_id: LocaleId
    html_lang: str
    home_title: str
    home_description: str
    shell_heading: str
    shell_body: str


LOCALE_SEO_COPY: Final[dict[LocaleId, LocaleSeoCopy]] = {
    "zh-Hans": LocaleSeoCopy(
        locale_id="zh-Hans",
        html_lang="zh-CN",
        home_title="免费防AI洗图水印工具 · 精卫 Jingwei",
        home_description=(
            "免费在线 · 防 AI 洗图盗图 · 无需注册。发稿前约 30 秒：可见防盗层 + 隐形 JW 声明，"
            "让 AI 洗图更难、盗图更亏。"
        ),
        shell_heading="免费防AI洗图水印工具 · 精卫 Jingwei",
        shell_body=(
            "免费在线 · 防 AI 洗图盗图 · 无需注册。发稿前约 30 秒：可见防盗层 + 隐形 JW 声明，"
            "让 AI 洗图更难、盗图更亏。"
        ),
    ),
    "zh-Hant": LocaleSeoCopy(
        locale_id="zh-Hant",
        html_lang="zh-Hant",
        home_title="免費防AI洗圖浮水印工具 · 精衛 Jingwei",
        home_description=(
            "免費線上 · 防 AI 洗圖盜圖 · 無需註冊。發稿前約 30 秒：可見防盜層 + 隱形 JW 聲明，"
            "讓 AI 洗圖更難、盜圖更虧。"
        ),
        shell_heading="免費防AI洗圖浮水印工具 · 精衛 Jingwei",
        shell_body=(
            "免費線上 · 防 AI 洗圖盜圖 · 無需註冊。發稿前約 30 秒：可見防盜層 + 隱形 JW 聲明，"
            "讓 AI 洗圖更難、盜圖更虧。"
        ),
    ),
    "en": LocaleSeoCopy(
        locale_id="en",
        html_lang="en",
        home_title="Free anti-AI wash-out watermark tool · Jingwei",
        home_description=(
            "Free online · Anti-AI wash-out · No signup required. Protect in ~30 seconds: "
            "visible anti-theft layers + invisible JW claims, harder to wash out, harder to steal."
        ),
        shell_heading="Free anti-AI wash-out watermark tool · Jingwei",
        shell_body=(
            "Free online · Anti-AI wash-out · No signup required. Protect in ~30 seconds: "
            "visible anti-theft layers + invisible JW claims, harder to wash out, harder to steal."
        ),
    ),
    "ja": LocaleSeoCopy(
        locale_id="ja",
        html_lang="ja",
        home_title="無料 AI洗い落とし透かしツール · 精衛 Jingwei",
        home_description=(
            "無料オンライン · AI洗い落とし対策 · 登録不要。約30秒で保護：可視レイヤー + 不可視 JW 宣言、"
            "洗い落としを難しく、盗用の損失を大きく。"
        ),
        shell_heading="無料 AI洗い落とし透かしツール · 精衛 Jingwei",
        shell_body=(
            "無料オンライン · AI洗い落とし対策 · 登録不要。約30秒で保護：可視レイヤー + 不可視 JW 宣言、"
            "洗い落としを難しく、盗用の損失を大きく。"
        ),
    ),
}

_HTML_LANG_RE = re.compile(r"(<html\s+lang=\")[^\"]*(\")", re.IGNORECASE)
_TITLE_RE = re.compile(r"(<title>)[^<]*(</title>)", re.IGNORECASE)
_META_DESC_RE = re.compile(
    r'(<meta\s+name="description"\s+content=")[^"]*(")',
    re.IGNORECASE,
)
_OG_TITLE_RE = re.compile(
    r'(<meta\s+property="og:title"\s+content=")[^"]*(")',
    re.IGNORECASE,
)
_OG_DESC_RE = re.compile(
    r'(<meta\s+property="og:description"\s+content=")[^"]*(")',
    re.IGNORECASE,
)
_TW_TITLE_RE = re.compile(
    r'(<meta\s+name="twitter:title"\s+content=")[^"]*(")',
    re.IGNORECASE,
)
_TW_DESC_RE = re.compile(
    r'(<meta\s+name="twitter:description"\s+content=")[^"]*(")',
    re.IGNORECASE,
)
_SHELL_H1_RE = re.compile(
    r'(<main id="static-shell">\s*<article>\s*<header>\s*<p>)[^<]*(</p>\s*</header>\s*<h1>)[^<]*(</h1>)',
    re.IGNORECASE | re.DOTALL,
)
_SHELL_P_RE = re.compile(
    r"(<main id=\"static-shell\">.*?<h1>[^<]*</h1>\s*<p>\s*)[\s\S]*?(\s*</p>)",
    re.IGNORECASE,
)
_NOSCRIPT_H1_RE = re.compile(
    r'(<noscript>.*?<h1[^>]*>)[^<]*(</h1>)',
    re.IGNORECASE | re.DOTALL,
)
_NOSCRIPT_P_RE = re.compile(
    r"(<noscript>.*?<h1[^>]*>[^<]*</h1>\s*<p>)[^<]*(</p>)",
    re.IGNORECASE | re.DOTALL,
)


def _locale_from_language_tag(tag: str) -> LocaleId | None:
    lower = tag.strip().replace("_", "-").lower()
    if not lower:
        return None
    if lower in {"zh-cn", "zh-hans"} or lower.startswith("zh-cn"):
        return "zh-Hans"
    if lower in {"zh-tw", "zh-hk", "zh-mo", "zh-hant"} or lower.startswith(("zh-tw", "zh-hk", "zh-mo")):
        return "zh-Hant"
    if lower == "zh" or lower.startswith("zh-"):
        region = lower.split("-", 1)[1] if "-" in lower else ""
        if region in _TRADITIONAL_ZH_REGIONS:
            return "zh-Hant"
        return "zh-Hans"
    if lower == "ja" or lower.startswith("ja-"):
        return "ja"
    if lower == "en" or lower.startswith("en-"):
        return "en"
    return None


def resolve_locale(lang_query: str | None, accept_language: str | None) -> LocaleId:
    """Pick locale from ?lang= first, then Accept-Language, default zh-Hans."""
    if lang_query and lang_query in _SUPPORTED_LOCALES:
        return lang_query

    if accept_language:
        for part in accept_language.split(","):
            token = part.split(";", 1)[0].strip()
            hit = _locale_from_language_tag(token)
            if hit:
                return hit

    return "zh-Hans"


def inject_locale_meta(html: str, locale: LocaleId) -> str:
    """Replace home meta and static shell copy for the given locale."""
    copy = LOCALE_SEO_COPY.get(locale) or LOCALE_SEO_COPY["zh-Hans"]
    out = html
    out = _HTML_LANG_RE.sub(rf"\1{copy.html_lang}\2", out, count=1)
    out = _TITLE_RE.sub(rf"\1{copy.home_title}\2", out, count=1)
    out = _META_DESC_RE.sub(rf"\1{copy.home_description}\2", out, count=1)
    out = _OG_TITLE_RE.sub(rf"\1{copy.home_title}\2", out, count=1)
    out = _OG_DESC_RE.sub(rf"\1{copy.home_description}\2", out, count=1)
    out = _TW_TITLE_RE.sub(rf"\1{copy.home_title}\2", out, count=1)
    out = _TW_DESC_RE.sub(rf"\1{copy.home_description}\2", out, count=1)

    shell_tag = "精卫 Jingwei · jwprotect.com"
    if copy.locale_id == "zh-Hant":
        shell_tag = "精衛 Jingwei · jwprotect.com"
    elif copy.locale_id == "en":
        shell_tag = "Jingwei · jwprotect.com"
    elif copy.locale_id == "ja":
        shell_tag = "精衛 Jingwei · jwprotect.com"

    out = _SHELL_H1_RE.sub(
        rf"\1{shell_tag}\2{copy.shell_heading}\3",
        out,
        count=1,
    )
    out = _SHELL_P_RE.sub(rf"\1{copy.shell_body}\2", out, count=1)
    out = _NOSCRIPT_H1_RE.sub(rf"\1{copy.shell_heading}\2", out, count=1)
    out = _NOSCRIPT_P_RE.sub(rf"\1{copy.shell_body}\2", out, count=1)
    out = inject_hreflang_links(out, "")
    return out


_META_ROBOTS_RE = re.compile(
    r'(<meta\s+name="robots"\s+content=")[^"]*(")',
    re.IGNORECASE,
)
_ROUTE_JSONLD_RE = re.compile(
    r'\s*<script type="application/ld\+json" id="route-json-ld">[\s\S]*?</script>',
    re.IGNORECASE,
)
# Match only the <article>…</article> inside #static-shell. Do NOT require
# </article> to be immediately followed by </main> — index.html places a
# <footer> between them, which previously made the regex never match.
_SHELL_ARTICLE_RE = re.compile(
    r'(<main id="static-shell">\s*<article>)[\s\S]*?(</article>)',
    re.IGNORECASE,
)
_HREFLANG_BLOCK_RE = re.compile(
    r'(?:<link\s+rel="alternate"\s+hreflang="[^"]*"\s+href="[^"]*"\s*/?>\s*)+',
    re.IGNORECASE,
)
_OG_URL_RE = re.compile(
    r'(<meta\s+property="og:url"\s+content=")[^"]*(")',
    re.IGNORECASE,
)

SITE_ORIGIN: Final[str] = "https://jwprotect.com"

# hreflang codes — keep in sync with sitemap.xml and frontend/src/lib/i18nSeo.ts
HREFLANG_BY_LOCALE: Final[dict[LocaleId, str]] = {
    "zh-Hans": "zh-Hans",
    "zh-Hant": "zh-Hant",
    "en": "en",
    "ja": "ja",
}


def _escape_meta(value: str) -> str:
    return escape(value, quote=True)


def _upsert_meta_robots(html: str, robots: str) -> str:
    content = _escape_meta(robots)
    if _META_ROBOTS_RE.search(html):
        return _META_ROBOTS_RE.sub(rf"\1{content}\2", html, count=1)
    return html.replace(
        '<meta name="viewport"',
        f'<meta name="robots" content="{content}" />\n    <meta name="viewport"',
        1,
    )


def _canonical_for_path(path: str) -> str:
    normalized = path.strip("/")
    if not normalized:
        return f"{SITE_ORIGIN}/"
    return f"{SITE_ORIGIN}/{normalized}"


def _locale_page_url(path: str, locale: LocaleId) -> str:
    base = _canonical_for_path(path)
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}lang={locale}"


def inject_hreflang_links(html: str, path: str) -> str:
    """Replace or insert crawler-visible hreflang alternates for this route."""
    links = []
    for locale, code in HREFLANG_BY_LOCALE.items():
        links.append(
            f'<link rel="alternate" hreflang="{code}" href="{_locale_page_url(path, locale)}" />'
        )
    links.append(
        f'<link rel="alternate" hreflang="x-default" href="{_canonical_for_path(path)}" />'
    )
    block = "\n    ".join(links) + "\n    "

    if _HREFLANG_BLOCK_RE.search(html):
        return _HREFLANG_BLOCK_RE.sub(block, html, count=1)

    # Insert after canonical when present, else before </head>
    canonical_re = re.compile(
        r'(<link\s+rel="canonical"\s+href="[^"]*"\s*/?>)',
        re.IGNORECASE,
    )
    if canonical_re.search(html):
        return canonical_re.sub(rf"\1\n    {block.rstrip()}", html, count=1)
    return html.replace("</head>", f"    {block}</head>", 1)


def _inject_route_static_shell(html: str, heading: str, paragraphs: list[str]) -> str:
    """Replace visually hidden static-shell copy for crawlers (does not affect React UI)."""
    clean_heading = heading.strip()
    clean_paragraphs = [p.strip() for p in paragraphs if isinstance(p, str) and p.strip()]
    if not clean_heading and not clean_paragraphs:
        return html

    body_parts = [f"<h1>{escape(clean_heading)}</h1>"] if clean_heading else []
    body_parts.extend(f"<p>{escape(p)}</p>" for p in clean_paragraphs)
    article = (
        "<header><p>精卫 Jingwei · jwprotect.com</p></header>"
        + "".join(body_parts)
    )
    updated, count = _SHELL_ARTICLE_RE.subn(rf"\1{article}\2", html, count=1)
    return updated if count else html


def _inject_route_json_ld(html: str, seo_dir: Path, json_ld_file: str) -> str:
    path = seo_dir / json_ld_file
    if not path.is_file():
        return html
    payload = path.read_text(encoding="utf-8").strip()
    script = f'\n    <script type="application/ld+json" id="route-json-ld">\n{payload}\n    </script>'
    cleaned = _ROUTE_JSONLD_RE.sub("", html, count=1)
    return cleaned.replace("</head>", f"{script}\n  </head>", 1)


def inject_route_seo(html: str, path: str, locale: LocaleId, seo_dir: Path) -> str:
    """Replace title/description/robots and inject route JSON-LD for known SPA routes."""
    routes_file = seo_dir / "routes.json"
    if not routes_file.is_file():
        return html

    bundle = json.loads(routes_file.read_text(encoding="utf-8"))
    route_map: dict[str, Any] = bundle.get("routes", {})
    route_entry = route_map.get(path.strip("/"))
    if not route_entry:
        return html

    meta = route_entry.get(locale) or route_entry.get("zh-Hans")
    if not meta:
        return html

    title = str(meta.get("title", "")).strip()
    description = str(meta.get("description", "")).strip()
    if not title:
        return html

    out = html
    out = _HTML_LANG_RE.sub(
        rf'\1{LOCALE_SEO_COPY.get(locale, LOCALE_SEO_COPY["zh-Hans"]).html_lang}\2',
        out,
        count=1,
    )
    out = _TITLE_RE.sub(rf"\1{escape(title)}\2", out, count=1)
    if description:
        desc = _escape_meta(description)
        out = _META_DESC_RE.sub(rf"\1{desc}\2", out, count=1)
        out = _OG_DESC_RE.sub(rf"\1{desc}\2", out, count=1)
        out = _TW_DESC_RE.sub(rf"\1{desc}\2", out, count=1)
    out = _OG_TITLE_RE.sub(rf"\1{_escape_meta(title)}\2", out, count=1)
    out = _TW_TITLE_RE.sub(rf"\1{_escape_meta(title)}\2", out, count=1)

    robots = meta.get("robots")
    if isinstance(robots, str) and robots.strip():
        out = _upsert_meta_robots(out, robots.strip())

    json_ld_file = meta.get("jsonLdFile")
    if isinstance(json_ld_file, str) and json_ld_file.strip():
        out = _inject_route_json_ld(out, seo_dir, json_ld_file.strip())

    # Always replace homepage static-shell so subpages never keep the home H1.
    shell_heading = meta.get("shellHeading")
    shell_paragraphs = meta.get("shellParagraphs")
    paragraphs: list[str]
    if isinstance(shell_paragraphs, list):
        paragraphs = [str(p) for p in shell_paragraphs if isinstance(p, str) and str(p).strip()]
    else:
        paragraphs = []
    if not paragraphs and description:
        paragraphs = [description]
    heading = (
        shell_heading.strip()
        if isinstance(shell_heading, str) and shell_heading.strip()
        else title
    )
    out = _inject_route_static_shell(out, heading, paragraphs)

    # Keep og:url aligned with the route canonical (not always homepage).
    route_canonical = _canonical_for_path(path)
    out = _OG_URL_RE.sub(rf"\1{_escape_meta(route_canonical)}\2", out, count=1)
    out = inject_hreflang_links(out, path)

    return out