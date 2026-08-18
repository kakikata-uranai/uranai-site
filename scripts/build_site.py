"""
書き方占いサイト - 静的サイトビルドスクリプト

articles/*.md（note_generator.pyで生成した記事）を読み込み、
docs/ 配下に静的HTMLサイトを出力する。
外部ライブラリ不要（Python標準ライブラリのみ）。

使い方:
    python scripts/build_site.py
"""

import html
import json
import os
import re
import shutil
from datetime import datetime
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTICLES_DIR = os.path.join(ROOT, "articles")
DATA_DIR = os.path.join(ROOT, "data")
ASSETS_DIR = os.path.join(ROOT, "assets")
OUT_DIR = os.path.join(ROOT, "docs")

SITE_NAME = "書き方占い"
SITE_TAGLINE = "文字のクセから、隠れた性格と運気を読み解く"
SITE_URL = "https://kakikata-uranai.github.io/uranai-site/"

NUM_MAP = {"①": "1", "②": "2", "③": "3", "④": "4", "⑤": "5"}

ALL_SEIZA = [
    "牡羊座", "牡牛座", "双子座", "蟹座", "獅子座", "乙女座",
    "天秤座", "蠍座", "射手座", "山羊座", "水瓶座", "魚座",
]
SEIZA_EMOJI = {
    "牡羊座": "♈", "牡牛座": "♉", "双子座": "♊", "蟹座": "♋",
    "獅子座": "♌", "乙女座": "♍", "天秤座": "♎", "蠍座": "♏",
    "射手座": "♐", "山羊座": "♑", "水瓶座": "♒", "魚座": "♓",
}


# ==============================
# Markdown（限定構文）→ HTML
# ==============================
def inline_md(text):
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    return text.replace("\n", "<br>")


def paragraphs_html(block):
    """空行区切りの本文をpタグ群に変換（### 小見出しがあればh3として扱う）"""
    # 「### 見出し」行の前後に空行がなくても独立した段落として扱う
    block = re.sub(r"[ \t]*\n(### [^\n]+)\n[ \t]*", r"\n\n\1\n\n", block)
    parts = [p.strip() for p in block.strip().split("\n\n") if p.strip()]
    out = []
    for p in parts:
        m = re.match(r"^### (.+)$", p)
        if m:
            out.append(f"<h3>{inline_md(m.group(1))}</h3>")
        else:
            out.append(f"<p>{inline_md(p)}</p>")
    return "\n".join(out)


def parse_article(md_text):
    """記事markdownをセクション辞書に分解する"""
    # イントロ見出し（付いている場合）を除去
    md_text = md_text.replace("## 書き方占いとは\n", "", 1).strip()

    sections = {}
    # 主要セクションの境界で分割
    markers = [
        ("intro", None, "## 今月の文字パーツ解説"),
        ("free_part", "## 今月の文字パーツ解説", "--- ここから先は有料です ---"),
        ("personality", "## 性格診断", "## 全12星座アドバイス"),
        ("seiza", "## 全12星座アドバイス", "## 相性"),
        ("compat", "## 相性", "## もっと詳しく占いたい方へ"),
        ("affiliate_cta", "## もっと詳しく占いたい方へ", "## 今すぐおみくじを引く"),
        ("omikuji_cta", "## 今すぐおみくじを引く", None),
    ]

    for key, start, end in markers:
        if start is None:
            s_idx = 0
        else:
            s_idx = md_text.find(start)
            if s_idx == -1:
                sections[key] = ""
                continue
            s_idx += len(start)
        if end is None:
            e_idx = len(md_text)
        else:
            e_idx = md_text.find(end, s_idx)
            if e_idx == -1:
                e_idx = len(md_text)
        sections[key] = md_text[s_idx:e_idx].strip()

    return sections


def seiza_cards_html(seiza_block):
    """### 星座名 ... を星座ごとのカードに変換"""
    cards = []
    chunks = re.split(r"^### (.+)$", seiza_block, flags=re.MULTILINE)[1:]
    for i in range(0, len(chunks) - 1, 2):
        name = chunks[i].strip()
        body = chunks[i + 1].strip()
        emoji = SEIZA_EMOJI.get(name, "☆")
        cards.append(
            f'<div class="seiza-card"><h3>{emoji} {html.escape(name)}</h3>'
            f'{paragraphs_html(body)}</div>'
        )
    return "\n".join(cards)


# ==============================
# 共通レイアウト
# ==============================
def page(title, description, body_html, depth=0, og_image=None, rel_path=""):
    base = "../" * depth
    # OGP・canonicalは絶対URLでなければSNSや検索エンジンが解釈できない
    og_url = SITE_URL + rel_path
    og_img = SITE_URL + (og_image or "assets/images/og-image.jpg")
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<link rel="canonical" href="{html.escape(og_url, quote=True)}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:image" content="{html.escape(og_img, quote=True)}">
<meta property="og:url" content="{html.escape(og_url, quote=True)}">
<meta property="og:type" content="{'article' if depth == 2 else 'website'}">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:locale" content="ja_JP">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/png" sizes="32x32" href="{base}assets/images/favicon-32.png">
<link rel="apple-touch-icon" sizes="180x180" href="{base}assets/images/favicon-180.png">
<link rel="stylesheet" href="{base}assets/style.css">
</head>
<body>
<header class="site-header">
  <a href="{base}index.html" class="logo">
    <img src="{base}assets/images/logo.jpg" alt="" class="logo-mark" width="44" height="44">
    <span>{SITE_NAME}</span>
  </a>
  <p class="tagline">{SITE_TAGLINE}</p>
</header>
<main>
{body_html}
</main>
<footer class="site-footer">
  <nav>
    <a href="{base}index.html">トップ</a>
    <a href="{base}about.html">このサイトについて</a>
    <a href="{base}privacy.html">プライバシーポリシー・免責事項</a>
  </nav>
  <p>&copy; {SITE_NAME}</p>
</footer>
</body>
</html>
"""


# ==============================
# ページ生成
# ==============================
def has_image(kanji):
    return os.path.exists(os.path.join(ASSETS_DIR, "images", f"uranai_{kanji}.png"))


def kanji_title(kanji, meta):
    """見出し用の名称。漢字は「愛」の書き方占い、Graphologyは 筆跡全体の書き方占い"""
    if meta.get("category") == "graphology":
        return f"{kanji}の書き方占い"
    return f"「{kanji}」の書き方占い"


def is_configured(entry):
    """リンクが実際に設定されているか（未設定・プレースホルダは出力しない）"""
    url = (entry or {}).get("url", "").strip()
    return bool(url) and "example.com" not in url


def ad_anchor(entry, label=None, cls="cta-button"):
    """広告リンクのaタグ。rel は sponsored + nofollow、別タブで開く"""
    text = label or entry.get("button_label") or entry.get("advertiser") or "詳しく見る"
    return (f'<a class="{cls}" href="{html.escape(entry["url"], quote=True)}" '
            f'rel="nofollow sponsored noopener" target="_blank">{html.escape(text)}</a>')


def impression_tag(entry):
    """A8の1×1インプレッション計測タグ（生成コードに含まれていた場合のみ）"""
    src = (entry or {}).get("impression", "").strip()
    if not src:
        return ""
    return (f'<img class="a8-impression" border="0" width="1" height="1" '
            f'src="{html.escape(src, quote=True)}" alt="">')


def inline_ad_link(text_html, token, entry):
    """本文中の [AFFILIATE_LINK] 等を、生URLではなくリンク付きの語に置き換える"""
    if not is_configured(entry):
        # 未設定なら「こちらの [LINK] から」のような文が壊れないよう語だけ残す
        return text_html.replace(token, "")
    word = entry.get("advertiser") or "こちら"
    anchor = (f'<a href="{html.escape(entry["url"], quote=True)}" '
              f'rel="nofollow sponsored noopener" target="_blank">{html.escape(word)}</a>')
    return text_html.replace(token, anchor)


def build_article_page(kanji, meta, pattern_num_idx, pattern_meta, links):
    num_label = pattern_meta["num"]
    num_clean = NUM_MAP.get(num_label, str(pattern_num_idx + 1))
    md_path = os.path.join(ARTICLES_DIR, f"note_{kanji}_{num_clean}.md")
    if not os.path.exists(md_path):
        return None

    with open(md_path, encoding="utf-8") as f:
        raw = f.read()

    sec = parse_article(raw)
    ktitle = kanji_title(kanji, meta)
    title = f"{ktitle} {num_label} {pattern_meta['part']}｜{SITE_NAME}"
    description = pattern_meta["core"]

    affiliate = links.get("affiliate", {})
    omikuji = links.get("omikuji", {})
    has_aff = is_configured(affiliate)
    has_omi = is_configured(omikuji)

    # 本文はエスケープしてから、残ったトークンをリンクに差し替える
    affiliate_html = inline_ad_link(paragraphs_html(sec["affiliate_cta"]), "[AFFILIATE_LINK]", affiliate)
    omikuji_html = inline_ad_link(paragraphs_html(sec["omikuji_cta"]), "[OMIKUJI_LINK]", omikuji)

    hero_img = (
        f'<img class="kanji-hero" src="../../assets/images/uranai_{html.escape(kanji)}.png" '
        f'alt="{html.escape(kanji)}の書き方占いイメージ" loading="lazy">'
        if has_image(kanji) else ""
    )

    # ステマ規制（景品表示法）対応：広告を含むページであることを冒頭で明示する
    pr_notice = ('<p class="pr-notice">本ページはプロモーションを含みます</p>'
                 if (has_aff or has_omi) else "")

    mid_ad = f"""
  <div class="ad-banner">
    <p>気になる続きは、以下から本格鑑定もチェックしてみてください。</p>
    {ad_anchor(affiliate)}
  </div>""" if has_aff else ""

    affiliate_section = f"""
  <section class="cta-section">
    <h2>もっと詳しく占いたい方へ</h2>
    {affiliate_html}
    {ad_anchor(affiliate)}
  </section>
""" if has_aff else ""

    omikuji_section = f"""
  <section class="cta-section">
    <h2>今すぐおみくじを引く</h2>
    {omikuji_html}
    {ad_anchor(omikuji, cls="cta-button cta-secondary")}
  </section>
""" if has_omi else ""

    body = f"""
<article class="kakikuse-article">
  <nav class="breadcrumb"><a href="../../index.html">トップ</a> &gt; <a href="../index.html">{html.escape(ktitle)}</a> &gt; {html.escape(num_label)}</nav>
  {pr_notice}
  <h1>{html.escape(ktitle)} {html.escape(num_label)}<br>{html.escape(pattern_meta['part'])}</h1>
  <p class="lead">{html.escape(pattern_meta['type'])}／{html.escape(pattern_meta['core'])}</p>

  {hero_img}

  <section class="intro">{paragraphs_html(sec['intro'])}</section>

  <section class="free-part">
    <h2>今月の文字パーツ解説</h2>
    {paragraphs_html(sec['free_part'])}
  </section>
{mid_ad}

  <section class="personality">
    <h2>性格診断</h2>
    {paragraphs_html(sec['personality'])}
  </section>

  <section class="seiza-section">
    <h2>全12星座アドバイス</h2>
    <div class="seiza-grid">
      {seiza_cards_html(sec['seiza'])}
    </div>
  </section>

  <section class="compat">
    <h2>相性</h2>
    {paragraphs_html(sec['compat'])}
  </section>

{affiliate_section}{omikuji_section}
</article>{impression_tag(affiliate)}{impression_tag(omikuji)}
"""
    return page(title, description, body, depth=2,
                rel_path=f"{quote(kanji)}/{num_clean}/")


def build_kanji_index(kanji, meta, available_patterns):
    theme = meta["theme"]
    ktitle = kanji_title(kanji, meta)
    cards = []
    for idx, p in enumerate(meta["patterns"]):
        if idx not in available_patterns:
            continue
        num_clean = NUM_MAP.get(p["num"], str(idx + 1))
        cards.append(f"""
<a class="pattern-card" href="{num_clean}/index.html">
  <h3>{html.escape(p['num'])} {html.escape(p['part'])}</h3>
  <p class="type">{html.escape(p['type'])}</p>
  <p>{html.escape(p['core'])}</p>
</a>""")

    hero_img = (
        f'<img src="../assets/images/uranai_{html.escape(kanji)}.png" alt="{html.escape(kanji)}の書き方占い" class="kanji-hero">'
        if has_image(kanji) else ""
    )
    if meta.get("category") == "graphology":
        intro = (f"{html.escape(kanji)}の特徴には、代表的な{len(cards)}つのパターンがあります。"
                 "欧米の筆跡診断（グラフォロジー）の視点から、気になるパターンを選んで詳しい診断を見てみましょう。")
    else:
        intro = (f"「{html.escape(kanji)}」という文字の書き方には、代表的な{len(cards)}つのクセがあります。"
                 "気になるパターンを選んで、詳しい診断を見てみましょう。")

    body = f"""
<nav class="breadcrumb"><a href="../index.html">トップ</a> &gt; {html.escape(ktitle)}</nav>
<section class="kanji-hero-section">
  {hero_img}
  <h1>{html.escape(ktitle)}</h1>
  <p class="lead">テーマ：{html.escape(theme)}</p>
  <p>{intro}</p>
</section>
<section class="pattern-grid">
  {''.join(cards)}
</section>
"""
    return page(f"{ktitle}｜{SITE_NAME}", f"{ktitle}でわかる{theme}診断。書き方パターンから深層心理を読み解きます。", body, depth=1, rel_path=f"{quote(kanji)}/")


def build_home(kakikuse_data, available):
    cards = []
    for kanji, meta in kakikuse_data.items():
        if not available.get(kanji):
            continue
        if has_image(kanji):
            visual = f'<img src="assets/images/uranai_{html.escape(kanji)}.png" alt="{html.escape(kanji)}の書き方占い" loading="lazy">'
        else:
            visual = '<div class="kanji-card-placeholder">✒</div>'
        label = kanji if meta.get("category") != "graphology" else kanji
        cards.append(f"""
<a class="kanji-card" href="{html.escape(kanji)}/index.html">
  {visual}
  <h2>{html.escape(label)}</h2>
  <p>{html.escape(meta['theme'])}</p>
</a>""")

    body = f"""
<section class="hero">
  <h1>あなたの「文字」に、隠れた本音が滲んでいます</h1>
  <p class="lead">普段何気なく書いている文字のクセから、恋愛運・金運・深層心理を読み解く書き方占い。気になる文字を選んでください。</p>
</section>
<section class="kanji-grid">
  {''.join(cards)}
</section>
<section class="about-blurb">
  <h2>書き方占いとは</h2>
  <p>手が紡ぐ文字には、無意識のサインが刻まれていると言われます。書き方占いは、日常で書く漢字のクセから、恋愛傾向や金運、深層心理を読み解く占いコンテンツです。気になる文字をタップして、あなたの書き方をチェックしてみてください。</p>
</section>
"""
    return page(f"{SITE_NAME}｜{SITE_TAGLINE}", SITE_TAGLINE, body, depth=0, rel_path="")


OWNER_NAME = "書き方占い師　星詠"
OWNER_MAIL = "kakikata.uranai@gmail.com"


def build_static_pages():
    about_body = f"""
<article class="static-page">
<h1>このサイトについて</h1>
<p>「書き方占い」は、日常で書く漢字の書き方のクセをもとに、恋愛運・金運・性格傾向をエンターテインメントとして紹介するサイトです。</p>
<p>コンテンツは筆跡心理学（グラフォロジー）的な視点と占星術の要素を組み合わせて構成していますが、科学的な性格診断や運勢を保証するものではありません。娯楽としてお楽しみください。</p>

<h2>運営者情報</h2>
<dl class="owner-info">
  <dt>運営者</dt><dd>{html.escape(OWNER_NAME)}</dd>
  <dt>サイト名</dt><dd>{SITE_NAME}</dd>
  <dt>連絡先</dt><dd><a href="mailto:{html.escape(OWNER_MAIL, quote=True)}">{html.escape(OWNER_MAIL)}</a></dd>
  <dt>運営内容</dt><dd>書き方（筆跡）をテーマとした占いコンテンツの制作・公開</dd>
</dl>
<p>ご意見・ご指摘、掲載内容に関するお問い合わせは上記のメールアドレスまでご連絡ください。
順次確認しておりますが、内容によっては返信までお時間をいただく場合があります。</p>
</article>
"""
    privacy_body = f"""
<article class="static-page">
<h1>プライバシーポリシー・免責事項</h1>
<h2>免責事項</h2>
<p>当サイトのコンテンツは占い・エンターテインメントを目的として提供しています。記載内容の正確性・完全性を保証するものではなく、当サイトの情報を利用したことによって生じたいかなる損害についても、運営者は責任を負いかねます。</p>
<p>当サイトは医療・心理・法律・投資等の専門的助言を目的としたものではありません。重要な意思決定に際しては、専門家にご相談ください。</p>
<h2>広告・アフィリエイトについて</h2>
<p>当サイトは、A8.netをはじめとするアフィリエイトプログラムに参加しており、紹介する商品・サービスのリンクには広告が含まれます。広告を掲載しているページには、その旨を明示しています。</p>
<p>これらのリンクを経由して申し込み・購入が行われた場合、当サイトは広告主から成果報酬を受け取ることがあります。商品・サービスの提供は各広告主が行うものであり、当サイトはその内容・品質について責任を負いません。</p>
<h2>個人情報の取り扱い</h2>
<p>当サイトはお問い合わせフォーム等を設置しておらず、訪問者から個人情報を直接収集することはありません。アクセス解析のためにアクセスログ等の情報が記録される場合があります。</p>
<p>広告配信事業者が、利用者の興味に応じた広告を表示するためにCookieを使用する場合があります。Cookieの利用はブラウザの設定により無効にすることができます。</p>
<h2>著作権について</h2>
<p>当サイトに掲載している文章・画像等の著作権は運営者に帰属します。無断での転載・複製はご遠慮ください。</p>
<h2>連絡先</h2>
<p>{html.escape(OWNER_NAME)}　<a href="mailto:{html.escape(OWNER_MAIL, quote=True)}">{html.escape(OWNER_MAIL)}</a></p>
</article>
"""
    return about_body, privacy_body


CSS = """
:root {
  --bg: #120c1e;
  --bg-card: #1d1530;
  --accent: #c9a4ff;
  --accent-strong: #a56eff;
  --text: #f1ecff;
  --text-muted: #b7a9d6;
  --border: #3a2d55;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: "Hiragino Mincho ProN", "Yu Mincho", serif;
  background: radial-gradient(circle at top, #1c1330 0%, #0c0817 70%);
  color: var(--text);
  line-height: 1.9;
}
a { color: var(--accent); }
.site-header {
  text-align: center;
  padding: 2.5rem 1rem 1.5rem;
  border-bottom: 1px solid var(--border);
}
.site-header .logo {
  font-size: 1.8rem;
  font-weight: bold;
  text-decoration: none;
  color: var(--text);
  letter-spacing: 0.1em;
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
}
.logo-mark {
  width: 44px; height: 44px;
  border-radius: 50%;
  border: 1px solid var(--border);
}
.site-header .tagline {
  color: var(--text-muted);
  margin-top: 0.5rem;
  font-size: 0.95rem;
}
main {
  max-width: 760px;
  margin: 0 auto;
  padding: 1.5rem 1.2rem 4rem;
}
.hero { text-align: center; margin-bottom: 2.5rem; }
.hero h1 { font-size: 1.6rem; }
.lead { color: var(--text-muted); }
.kanji-grid, .pattern-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 1rem;
  margin: 2rem 0;
}
.kanji-card, .pattern-card {
  display: block;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1rem;
  text-decoration: none;
  color: var(--text);
  text-align: center;
  transition: border-color 0.2s;
}
.kanji-card:hover, .pattern-card:hover { border-color: var(--accent); }
.kanji-card img { width: 100%; border-radius: 8px; margin-bottom: 0.5rem; }
.kanji-card-placeholder {
  aspect-ratio: 1 / 1;
  display: flex; align-items: center; justify-content: center;
  font-size: 3rem; color: var(--accent);
  background: linear-gradient(135deg, #2a1c47, #1a1230);
  border-radius: 8px; margin-bottom: 0.5rem;
}
.kanji-card h2 { margin: 0.3rem 0; font-size: 1.4rem; }
.pattern-card h3 { margin-top: 0; color: var(--accent); }
.pattern-card .type { color: var(--text-muted); font-size: 0.9rem; }
.about-blurb { margin-top: 3rem; border-top: 1px solid var(--border); padding-top: 1.5rem; }
.breadcrumb { font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1rem; }
.pr-notice {
  font-size: 0.78rem;
  color: var(--text-muted);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 0.35rem 0.7rem;
  display: inline-block;
  margin: 0 0 1rem;
}
.a8-impression { position: absolute; width: 1px; height: 1px; opacity: 0; }
.breadcrumb a { color: var(--text-muted); }
.kanji-hero-section { text-align: center; }
.kanji-hero { max-width: 220px; width: 100%; border-radius: 12px; margin: 1rem auto; display: block; }
.kakikuse-article h1 { font-size: 1.5rem; line-height: 1.5; }
.kakikuse-article .lead { margin-bottom: 1.5rem; }
.kakikuse-article section { margin: 2.2rem 0; }
.kakikuse-article h2 {
  font-size: 1.2rem;
  border-left: 4px solid var(--accent-strong);
  padding-left: 0.6rem;
  margin-bottom: 1rem;
}
.seiza-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
}
.seiza-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1rem;
}
.seiza-card h3 { margin-top: 0; color: var(--accent); font-size: 1rem; }
.ad-banner {
  background: linear-gradient(135deg, #2a1c47, #1a1230);
  border: 1px solid var(--accent-strong);
  border-radius: 12px;
  padding: 1.4rem;
  text-align: center;
  margin: 2rem 0;
}
.cta-section {
  background: var(--bg-card);
  border-radius: 12px;
  padding: 1.4rem;
  text-align: center;
}
.cta-button {
  display: inline-block;
  margin-top: 0.8rem;
  padding: 0.8rem 1.8rem;
  background: var(--accent-strong);
  color: #0c0817;
  text-decoration: none;
  border-radius: 999px;
  font-weight: bold;
  letter-spacing: 0.05em;
}
.cta-button.cta-secondary { background: transparent; border: 1px solid var(--accent); color: var(--accent); }
.static-page h1 { font-size: 1.5rem; }
.static-page h2 { font-size: 1.15rem; margin-top: 1.8rem; }
.owner-info {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.2rem 1.4rem;
  margin: 1rem 0;
}
.owner-info dt {
  color: var(--accent);
  font-size: 0.85rem;
  margin-top: 0.8rem;
}
.owner-info dt:first-child { margin-top: 0; }
.owner-info dd { margin: 0.2rem 0 0; }
.site-footer {
  text-align: center;
  padding: 2rem 1rem;
  border-top: 1px solid var(--border);
  color: var(--text-muted);
  font-size: 0.85rem;
}
.site-footer nav a { margin: 0 0.6rem; color: var(--text-muted); }
"""


def write_sitemap(rel_urls):
    """検索エンジンに全ページを伝える sitemap.xml"""
    today = datetime.now().strftime("%Y-%m-%d")
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for rel in rel_urls:
        priority = "1.0" if rel == "" else ("0.8" if rel.count("/") <= 1 else "0.6")
        lines.append("  <url>")
        lines.append(f"    <loc>{html.escape(SITE_URL + rel)}</loc>")
        lines.append(f"    <lastmod>{today}</lastmod>")
        lines.append(f"    <priority>{priority}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    with open(os.path.join(OUT_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def write_robots():
    """クロールを許可し、sitemapの場所を伝える"""
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        f"Sitemap: {SITE_URL}sitemap.xml\n"
    )
    with open(os.path.join(OUT_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(content)


def main():
    if os.path.exists(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    os.makedirs(OUT_DIR)
    os.makedirs(os.path.join(OUT_DIR, "assets", "images"))

    with open(os.path.join(DATA_DIR, "kakikuse.json"), encoding="utf-8") as f:
        kakikuse_data = json.load(f)
    with open(os.path.join(DATA_DIR, "links.json"), encoding="utf-8") as f:
        links = json.load(f)

    # 静的アセット
    with open(os.path.join(OUT_DIR, "assets", "style.css"), "w", encoding="utf-8") as f:
        f.write(CSS)
    for img in os.listdir(os.path.join(ASSETS_DIR, "images")):
        shutil.copy(
            os.path.join(ASSETS_DIR, "images", img),
            os.path.join(OUT_DIR, "assets", "images", img),
        )

    # .nojekyll（GitHub Pagesがアンダースコア始まりのファイルを無視しないように）
    open(os.path.join(OUT_DIR, ".nojekyll"), "w").close()

    # static/ の中身はそのままサイト直下へ（Search Consoleの所有権確認ファイル等）
    static_dir = os.path.join(ROOT, "static")
    if os.path.isdir(static_dir):
        for name in os.listdir(static_dir):
            src = os.path.join(static_dir, name)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(OUT_DIR, name))

    # 記事が存在するパターンだけをサイトに載せる（未生成分は自動的に非表示）
    available = {}
    for kanji, meta in kakikuse_data.items():
        idxs = []
        for idx, pattern in enumerate(meta["patterns"]):
            num_clean = NUM_MAP.get(pattern["num"], str(idx + 1))
            if os.path.exists(os.path.join(ARTICLES_DIR, f"note_{kanji}_{num_clean}.md")):
                idxs.append(idx)
        available[kanji] = idxs

    # トップページ
    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(build_home(kakikuse_data, available))

    about_body, privacy_body = build_static_pages()
    with open(os.path.join(OUT_DIR, "about.html"), "w", encoding="utf-8") as f:
        f.write(page(f"このサイトについて｜{SITE_NAME}", "書き方占いサイトの運営方針について", about_body, depth=0, rel_path="about.html"))
    with open(os.path.join(OUT_DIR, "privacy.html"), "w", encoding="utf-8") as f:
        f.write(page(f"プライバシーポリシー・免責事項｜{SITE_NAME}", "プライバシーポリシーおよび免責事項", privacy_body, depth=0, rel_path="privacy.html"))

    built = 0
    missing = []
    urls = ["", "about.html", "privacy.html"]
    for kanji, meta in kakikuse_data.items():
        if not available[kanji]:
            missing.extend(f"note_{kanji}_{NUM_MAP.get(p['num'], str(i+1))}.md"
                           for i, p in enumerate(meta["patterns"]))
            continue
        kanji_dir = os.path.join(OUT_DIR, kanji)
        os.makedirs(kanji_dir, exist_ok=True)
        with open(os.path.join(kanji_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(build_kanji_index(kanji, meta, available[kanji]))
        urls.append(f"{quote(kanji)}/")

        for idx, pattern in enumerate(meta["patterns"]):
            num_clean = NUM_MAP.get(pattern["num"], str(idx + 1))
            html_out = build_article_page(kanji, meta, idx, pattern, links)
            if html_out is None:
                missing.append(f"note_{kanji}_{num_clean}.md")
                continue
            pat_dir = os.path.join(kanji_dir, num_clean)
            os.makedirs(pat_dir, exist_ok=True)
            with open(os.path.join(pat_dir, "index.html"), "w", encoding="utf-8") as f:
                f.write(html_out)
            urls.append(f"{quote(kanji)}/{num_clean}/")
            built += 1

    write_sitemap(urls)
    write_robots()

    print(f"ビルド完了: {built}ページ生成 → {OUT_DIR}")
    print(f"sitemap.xml: {len(urls)}件のURLを登録")
    if missing:
        print(f"未生成のためスキップ（{len(missing)}件）: {', '.join(missing)}")


if __name__ == "__main__":
    main()
