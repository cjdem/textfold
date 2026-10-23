"""The download page, from one template and one table of words.

dist/: index.html (English) and zh.html (Chinese), each with its own head for search engines and AI answers (title,
description, canonical, hreflang, Open Graph, and JSON-LD for the app and its questions), robots.txt, sitemap.xml,
llms.txt and assets/, with the app's own fonts (Inter and Source Serif 4, served from the site: no visitor's browser
asks a font service for anything; monospace is the system's, as in the app). preview.html is the two pages in one, for
a look before anything goes up, with what search engines and AI read shown at the bottom.

    python site/build.py                           the pages"""
import datetime
import html
import json
import pathlib
import re
import shutil

from strings import DL, FAQ, FILES, LANGS_NATIVE, REPO, S, SITE, TYPED, VERSION

HERE = pathlib.Path(__file__).parent
OUT = HERE / "dist"
FONT_DIR = HERE.parent / "textfold" / "web" / "vendor" / "fonts"   # the app's, with their licences
IX = {"en": 0, "zh": 1}
PAGE = {"en": SITE, "zh": SITE + "zh.html"}
HTML_LANG = {"en": "en", "zh": "zh-CN"}
LOCALE = {"en": "en_US", "zh": "zh_CN"}
UI_LANGS = ["en", "zh-CN"]
# the preview's only: an artifact may load fonts from Google Fonts alone, so it takes the same two faces from there
FONTS = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600&display=swap"
esc = html.escape


def s(key, lang):
    return S[key][IX[lang]]


def plain(text):
    return html.unescape(re.sub(r"<[^>]+>", "", text))


def cta(lang):
    """The first button: the Windows app is the only download."""
    return {
        "win": {"href": DL + FILES["win"], "t": s("cta_win", lang), "s": s("cta_win_sub", lang)},
    }


def body(lang, preview=False):
    other = "zh" if lang == "en" else "en"
    extra = {
        "home": "#" if preview else ("./" if lang == "en" else "zh.html"),
        "repo": REPO,
        "readme": REPO + ("#readme" if lang == "en" else "/blob/main/README.zh-CN.md"),
        "lang_href": "#" if preview else ("zh.html" if lang == "en" else "./"),
        "lang_other_code": HTML_LANG[other],
        "dl_win_url": DL + FILES["win"],
        "typer_json": esc(json.dumps({"prefix": s("typer_prefix", lang), "phrases": TYPED[lang]}, ensure_ascii=False), quote=True),
        "faq": "".join(f"<div><h3>{s(q, lang)}</h3><p>{s(a, lang)}</p></div>" for q, a in FAQ),
    }

    def fill(m):
        k = m.group(1)
        return extra[k] if k in extra else s(k, lang)
    out = re.sub(r"\{\{(\w+)\}\}", fill, (HERE / "template.html").read_text(encoding="utf-8"))
    if preview and lang == "zh":   # (both pages in one: the Chinese one's anchors are its own)
        out = re.sub(r'id="(\w+)"', r'id="zh-\1"', out)
        out = re.sub(r'href="#(\w+)"', r'href="#zh-\1"', out)
    conf = f'<script type="application/json" class="cta-conf">{json.dumps(cta(lang), ensure_ascii=False)}</script>'
    return f'<div data-root lang="{HTML_LANG[lang]}"{" hidden" if preview and lang == "zh" else ""}>\n{out}{conf}\n</div>'


def app_ld(lang):
    return {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": "TextFold",
        "alternateName": "PaperFold",
        "description": s("description", lang),
        "url": PAGE[lang],
        "applicationCategory": "EducationalApplication",
        "applicationSubCategory": "Reader for research papers and project material",
        "operatingSystem": "Windows 10 or 11 (64-bit)",
        "softwareVersion": VERSION,
        "downloadUrl": [DL + FILES["win"]],
        "installUrl": PAGE[lang] + "#download",
        "releaseNotes": REPO + "/releases/latest",
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "isAccessibleForFree": True,
        "license": "https://www.apache.org/licenses/LICENSE-2.0",
        "inLanguage": UI_LANGS,
        "featureList": ["Five levels per paragraph, from a map of the sections to every word", "Reads beside the original PDF",
                        "Answers about what you read, citing its paragraphs", "Notes that stay as you zoom out", "English and Simplified Chinese"],
        "keywords": "research papers, project material, reading, students, PDF reader, sources, Magpie, API provider, Zotero",
        "author": {"@type": "Person", "name": "cjdem", "url": "https://github.com/cjdem"},
        "contributor": {"@type": "Person", "name": "Xia Chen"},
        "sameAs": [REPO],
    }


def faq_ld(lang):
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "inLanguage": HTML_LANG[lang],
        "mainEntity": [{"@type": "Question", "name": plain(s(q, lang)),
                        "acceptedAnswer": {"@type": "Answer", "text": plain(s(a, lang))}} for q, a in FAQ],
    }


def head(lang):
    t, d, u = esc(s("title", lang)), esc(s("description", lang)), PAGE[lang]
    other = "zh" if lang == "en" else "en"
    ld = lambda o: json.dumps(o, ensure_ascii=False, indent=2).replace("</", "<\\/")
    return f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{t}</title>
<meta name="description" content="{d}">
<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="canonical" href="{u}">
<link rel="alternate" hreflang="en" href="{PAGE['en']}">
<link rel="alternate" hreflang="zh-CN" href="{PAGE['zh']}">
<link rel="alternate" hreflang="x-default" href="{PAGE['en']}">
<link rel="icon" type="image/svg+xml" href="assets/logo.svg">
<meta name="theme-color" content="#FAF9F7" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#1B1915" media="(prefers-color-scheme: dark)">
<meta property="og:type" content="website">
<meta property="og:site_name" content="TextFold">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:url" content="{u}">
<meta property="og:locale" content="{LOCALE[lang]}">
<meta property="og:locale:alternate" content="{LOCALE[other]}">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{t}">
<meta name="twitter:description" content="{d}">
<link rel="preload" href="assets/fonts/inter-normal-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="assets/fonts/sourceserif4-normal-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="assets/fonts/fonts.css">
<script type="application/ld+json">
{ld(app_ld(lang))}
</script>
<script type="application/ld+json">
{ld(faq_ld(lang))}
</script>"""


def llms():
    return f"""# TextFold

> TextFold is a reader for research papers and project material: it folds a paper, a web page or a document into five levels, from a one-screen map of its sections to every word. Every line a model writes points back to the sentences it rests on, and the two finest levels are the author's own words, so what is read can always be checked against what was written. Free and open source (Apache License 2.0). It runs on the reader's computer: an app for Windows, or a Python package on Windows. Formerly PaperFold.

> This is an unofficial fork of Xia Chen's TextFold, maintained by cjdem; not affiliated with or endorsed by the original author. See [NOTICE]({REPO}/blob/main/NOTICE) for attribution and changes.

TextFold keeps the whole text and lets each reader take it at the level of detail they need.

## What it does

- Five levels per paragraph. Full and Brief keep the author's own words; Key, Takeaway and Topic are written by a model, each line anchored to the author's sentences it rests on.
- Reads arXiv, PubMed Central, bioRxiv, medRxiv, DOIs whose full text is open in Europe PMC, Wikipedia, GitHub READMEs, any web page, PDF, Word (DOCX), PowerPoint (PPTX), Excel (XLSX), EPUB, HTML, CSV, pictures, Markdown, text, and a Zotero 7 library. Every PDF and picture is parsed by MinerU's Cloud API; the file leaves the computer for conversion.
- Uses a model the reader already has: a running local Magpie gateway, free models through OpenRouter's one-click authorisation, or an API key (OpenRouter, Anthropic, OpenAI, DeepSeek, Google AI Studio, Z.ai GLM / 智谱 GLM, GLM Coding Plan, Kimi Code, Moonshot, MiniMax, Ollama, Magpie, any OpenAI-compatible endpoint).
- Two languages, translated sentence by sentence: {LANGS_NATIVE}.
- The library stays on the reader's computer, and there is no account.
- Systems: Windows 10 and 11 (64-bit); the Python package needs Python 3.9 or newer. Current version: {VERSION}.

## Download

- [TextFold for Windows, 64-bit (installer)]({DL}{FILES['win']})
- [The Python package from this fork, for Windows]({REPO}): `python3 -m pip install git+{REPO}`, then `python3 -m textfold serve`, then open http://localhost:3017

## Docs

- [README]({REPO}/blob/main/README.md): what it reads, connecting a model, the reader's keys, saving a page, Zotero
- [The TextFold format]({REPO}/blob/main/docs/format.md): a folded document as JSON
- [Release notes]({REPO}/releases)

## Optional

- [This page in Chinese]({PAGE['zh']})
"""


def sitemap():
    day = datetime.date.today().isoformat()
    alt = "".join(f'\n    <xhtml:link rel="alternate" hreflang="{h}" href="{PAGE[k]}"/>' for k, h in (("en", "en"), ("zh", "zh-CN")))
    urls = "".join(f"\n  <url>\n    <loc>{PAGE[k]}</loc>\n    <lastmod>{day}</lastmod>{alt}\n  </url>" for k in ("en", "zh"))
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">{urls}\n</urlset>\n'


ROBOTS = f"User-agent: *\nAllow: /\n\nSitemap: {SITE}sitemap.xml\n"


def page(lang, css, js, mjs):
    return (f'<!doctype html>\n<html lang="{HTML_LANG[lang]}">\n<head>\n{head(lang)}\n<style>\n{css}</style>\n</head>\n<body>\n'
            f'{body(lang)}\n<script>\n{js}</script>\n<script type="module">\n{mjs}</script>\n</body>\n</html>\n')


def inlined(mjs):
    """The preview's own copy of ascii.js, with ascii.rest's three files in it: a preview page may not load files beside it
    as scripts, so each file becomes a block of its own, returning what it exported."""
    vendor = HERE / "assets" / "vendor" / "ascii.rest" / "dist"

    def block(path, names):
        src = (vendor / path).read_text(encoding="utf-8")
        src = re.sub(r"^export default function (\w+)", r"function \1", src, flags=re.M)
        src = re.sub(r"^export (const|function) ", r"\1 ", src, flags=re.M)
        return f"(() => {{\n{src}\nreturn {{ {names} }};\n}})()"
    head = (f"const {{ mount }} = {block('mount.js', 'mount')};\n"
            f"const typewriter = {block('pieces/typewriter.js', 'meta, default: typewriter')};\n")
    body = re.sub(r"^import .*?;\n", "", mjs, flags=re.M)
    return head + body


def preview(css, js, mjs):
    mjs = inlined(mjs)
    shown = esc(head("en"))
    panel = f"""
<section class="seo wrap" aria-label="预览专用">
  <h2>预览专用：搜索引擎和 AI 读到的内容</h2>
  <p>这一块不上线。上线的是两页，<code>index.html</code>（英文，默认）和 <code>zh.html</code>（中文），外加 <code>robots.txt</code>、<code>sitemap.xml</code>、<code>llms.txt</code>。上面右上角的“中文”在这里直接切换，上线后是两个网址。</p>
  <ul class="checks">
    <li><b>标题和描述：</b>每页一套，说清楚它是什么、在哪些系统上跑。英文：“{esc(s('title', 'en'))}”；中文：“{esc(s('title', 'zh'))}”。</li>
    <li><b>canonical 和 hreflang：</b>两种语言互相指向，英文是默认，搜索引擎不会当成重复页面。</li>
    <li><b>分享卡片：</b>Open Graph 和 Twitter 卡片，链接贴到社交网站时显示标题和描述；旧的 1200×630 首屏图印着 Mac 下载，已随官网压缩移除。</li>
    <li><b>结构化数据：</b><code>SoftwareApplication</code> 写明名字、原名、系统、版本、下载地址、免费、许可证、作者和关键词；<code>FAQPage</code> 收了页面上那四个问答。</li>
    <li><b>定位：</b>首屏、<code>llms.txt</code>、问答和结构化数据都围绕论文和项目材料的阅读器；<code>llms.txt</code> 只列能力、系统和下载，不再有单独的 Agent 接口介绍。</li>
    <li><b>下载地址不随版本变：</b>都指向 <code>releases/latest/download/…</code>；安装包的文件名已经去掉版本号，发新版不用改网页。</li>
  </ul>
  <details open><summary>英文页的 &lt;head&gt;</summary><pre>{shown}</pre></details>
  <details><summary>llms.txt</summary><pre>{esc(llms())}</pre></details>
  <details><summary>robots.txt 和 sitemap.xml</summary><pre>{esc(ROBOTS)}\n{esc(sitemap())}</pre></details>
</section>"""
    switch = """
document.addEventListener('click', (e) => {
  const a = e.target.closest('[data-lang-switch]');
  if (!a) return;
  e.preventDefault();
  document.querySelectorAll('[data-root]').forEach((r) => { r.hidden = !r.hidden; });
  const shown = document.querySelector('[data-root]:not([hidden])');
  document.documentElement.lang = shown.lang;
  scrollTo({ top: 0 });
});
"""
    pcss = """
.seo { margin-top: 64px; padding-block: 28px 8px; border-top: 2px dashed var(--warm); }
.seo h2 { color: var(--warm); }
.seo .checks { padding-left: 20px; color: var(--ink-2); max-width: 80ch; }
.seo .checks li { margin: 6px 0; }
.seo details { margin: 14px 0; border: 1px solid var(--line); border-radius: 12px; background: var(--card); }
.seo summary { cursor: pointer; padding: 12px 16px; font-weight: 650; }
.seo pre { margin: 0; padding: 0 16px 16px; overflow-x: auto; font-size: 12px; line-height: 1.55; color: var(--ink-2); white-space: pre; }
"""
    return (f'<title>TextFold Website</title>\n<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            f'<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n<link rel="stylesheet" href="{FONTS}">\n'
            f'<style>\n{css}{pcss}</style>\n{body("en", True)}\n{body("zh", True)}\n{panel}\n<script>\n{js}{switch}</script>\n<script type="module">\n{mjs}</script>\n')


if __name__ == "__main__":
    css = (HERE / "style.css").read_text(encoding="utf-8")
    js = (HERE / "page.js").read_text(encoding="utf-8")
    mjs = (HERE / "ascii.js").read_text(encoding="utf-8")
    shutil.rmtree(OUT, ignore_errors=True)
    shutil.copytree(HERE / "assets", OUT / "assets")
    shutil.copytree(FONT_DIR, OUT / "assets" / "fonts")
    (OUT / "index.html").write_text(page("en", css, js, mjs), encoding="utf-8")
    (OUT / "zh.html").write_text(page("zh", css, js, mjs), encoding="utf-8")
    (OUT / "robots.txt").write_text(ROBOTS, encoding="utf-8")
    (OUT / "sitemap.xml").write_text(sitemap(), encoding="utf-8")
    (OUT / "llms.txt").write_text(llms(), encoding="utf-8")
    (HERE / "preview.html").write_text(preview(css, js, mjs), encoding="utf-8")
    left = [m for f in ("index.html", "zh.html") for m in re.findall(r"\{\{\w+\}\}", (OUT / f).read_text(encoding="utf-8"))]
    print("built:", sorted(p.name for p in OUT.iterdir()), "| unfilled:", left)
