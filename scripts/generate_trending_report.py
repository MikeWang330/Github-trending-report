#!/usr/bin/env python3
import argparse
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path


TRENDING_URL = "https://github.com/trending?since=weekly"
BEIJING = timezone(timedelta(hours=8))
THEMES = [
    ("teal-mist", "#0f766e", "linear-gradient(135deg,#d9f7f2 0%,#f8fbff 45%,#e7f1ff 100%)"),
    ("violet-sage", "#7c3aed", "linear-gradient(135deg,#f1eafe 0%,#f8fbff 42%,#e7f5ef 100%)"),
    ("blue-coral", "#2563eb", "linear-gradient(135deg,#e8f1ff 0%,#fbfdff 44%,#ffece6 100%)"),
    ("forest-gold", "#047857", "linear-gradient(135deg,#e8f7ef 0%,#fbfbf5 48%,#fff1cc 100%)"),
    ("slate-rose", "#be123c", "linear-gradient(135deg,#eef2f7 0%,#fff8fb 44%,#f6eefc 100%)"),
]


@dataclass
class Repo:
    name: str
    author: str
    url: str
    description: str
    language: str
    stars: str
    weekly_stars: int
    what: str
    features: list[str]
    usage: str


def fetch(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 GitHub-Trending-Weekly-Reporter",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def strip_tags(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def extract_int(value: str) -> int:
    match = re.search(r"[\d,]+", value or "")
    return int(match.group(0).replace(",", "")) if match else 0


def parse_trending(page: str, limit: int) -> list[Repo]:
    articles = re.findall(r"<article\b.*?</article>", page, flags=re.S)
    repos: list[Repo] = []
    for article in articles:
        link = re.search(r'<h2[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', article, flags=re.S)
        if not link:
            continue

        href = html.unescape(link.group(1)).strip()
        parts = [part for part in href.strip("/").split("/") if part]
        if len(parts) < 2:
            continue

        author, name = parts[0], parts[1]
        desc_match = re.search(r'<p[^>]*class="[^"]*col-9[^"]*"[^>]*>(.*?)</p>', article, flags=re.S)
        lang_match = re.search(r'<span itemprop="programmingLanguage">([^<]+)</span>', article)
        star_links = re.findall(r'<a[^>]+href="/%s/%s/stargazers"[^>]*>(.*?)</a>' % (re.escape(author), re.escape(name)), article, flags=re.S)
        weekly_match = re.search(r"([\d,]+)\s+stars?\s+this\s+week", strip_tags(article), flags=re.I)

        description = strip_tags(desc_match.group(1)) if desc_match else "暂无公开简介。"
        language = strip_tags(lang_match.group(1)) if lang_match else "未标注"
        stars = strip_tags(star_links[0]) if star_links else "0"
        weekly_stars = extract_int(weekly_match.group(1) if weekly_match else "")
        what, features, usage = explain_project(name, description, language)
        repos.append(
            Repo(
                name=name,
                author=author,
                url=f"https://github.com/{author}/{name}",
                description=description,
                language=language,
                stars=stars,
                weekly_stars=weekly_stars,
                what=what,
                features=features,
                usage=usage,
            )
        )

    repos.sort(key=lambda item: item.weekly_stars, reverse=True)
    return repos[:limit]


def explain_project(name: str, description: str, language: str) -> tuple[str, list[str], str]:
    text = f"{name} {description}".lower()
    rules = [
        (("agent", "mcp", "llm", "ai", "gpt", "model"), "AI 工具", "帮助把大模型接入具体工作流，减少重复操作。", ["连接模型、工具和业务系统", "让 AI 根据上下文完成更具体的任务", "适合改造成内部助手或自动化流程"], "适合研发、运营、客服、数据团队，把查资料、整理信息、生成结果这类重复任务交给 AI 辅助完成。"),
        (("pdf", "document", "doc"), "文档工具", "帮助更高效地处理文档、PDF 或办公资料。", ["提供常见文档处理能力", "适合批量处理和内部部署", "降低依赖外部网站上传文件的风险"], "适合行政、法务、财务、运营等经常处理文件的人，用来合并、转换、整理或自动化文档流程。"),
        (("chat", "message", "messaging"), "沟通工具", "提供聊天、消息或团队沟通相关能力。", ["支持消息收发和会话管理", "关注隐私、安全或跨平台体验", "可作为团队沟通工具的参考"], "适合对隐私、安全或自部署有要求的团队，用来搭建更可控的沟通方案。"),
        (("design", "ui", "figma", "prototype", "component"), "设计协作工具", "帮助团队更清楚地设计、复用和交付界面。", ["沉淀设计规范和组件规则", "方便产品、设计和研发对齐", "可用于快速制作原型或页面"], "适合产品、设计和前端团队，在做新页面或新产品前统一风格、减少返工。"),
        (("crawler", "scraper", "monitor", "stock", "data"), "数据工具", "帮助自动收集、整理和观察公开数据。", ["自动抓取或监控信息源", "把分散数据整理成可分析内容", "适合做看板、提醒或研究材料"], "适合市场、运营、研究、风控团队，用来追踪热点、竞品、舆情或业务指标。"),
        (("voice", "audio", "speech"), "语音工具", "帮助应用处理语音、音频或语音交互。", ["提供语音输入输出相关能力", "可接入语音助手或音频处理流程", "适合做原型验证"], "适合做语音客服、会议记录、口语练习、播客处理等场景的团队参考。"),
        (("browser", "web", "page", "site", "website"), "网页工具", "帮助创建、理解、测试或自动操作网页。", ["围绕网页生成、分析或操作提供能力", "适合前端原型和自动化测试", "能减少重复网页操作"], "适合产品经理、前端开发、测试同学，用来快速做页面原型、检查网页或自动执行流程。"),
        (("security", "cyber", "vulnerability"), "安全工具", "帮助团队更系统地发现、分析或处理安全问题。", ["提供安全检查或分析流程", "帮助整理风险线索和处置建议", "适合接入安全团队工作流"], "适合安全工程师、运维和研发团队，用来辅助排查风险、整理日志和形成处置清单。"),
    ]
    for keys, category, summary, features, usage in rules:
        if any(key in text for key in keys):
            return f"{name} 是一个偏{category}的开源项目，{summary}", features, usage

    features = [
        "提供一组可直接复用的开源能力",
        "适合开发者根据自己的业务继续改造",
        "可以作为同类项目选型或学习参考",
    ]
    usage = "适合开发者或技术团队先用它快速验证想法，再按自己的业务需求做定制。"
    if language and language != "未标注":
        features[0] = f"主要使用 {language} 构建，方便相同技术栈团队上手"
    return f"{name} 是一个近期热度较高的开源项目，可以帮助开发者更快搭建或改进相关工具。", features, usage


def choose_theme(output_dir: Path) -> tuple[str, str, str]:
    state_path = output_dir / "theme-history.json"
    recent: list[str] = []
    if state_path.exists():
        try:
            recent = [item["theme"] for item in json.loads(state_path.read_text(encoding="utf-8")).get("recentThemes", [])[-3:]]
        except (json.JSONDecodeError, KeyError, TypeError):
            recent = []

    theme = next((item for item in THEMES if item[0] not in recent), THEMES[0])
    today = datetime.now(BEIJING).strftime("%Y-%m-%d")
    history = [{"date": today, "theme": theme[0]}]
    if state_path.exists():
        try:
            old = json.loads(state_path.read_text(encoding="utf-8")).get("recentThemes", [])
            history = (old + history)[-3:]
        except json.JSONDecodeError:
            pass
    state_path.write_text(json.dumps({"recentThemes": history}, ensure_ascii=False, indent=2), encoding="utf-8")
    return theme


def render_html(repos: list[Repo], generated_at: str, theme: tuple[str, str, str]) -> str:
    _, accent, background = theme
    cards = "\n".join(render_card(repo) for repo in repos)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GitHub Trending 中文周报</title>
  <style>
    :root {{ --ink:#172033; --muted:#647084; --line:rgba(23,32,51,.12); --panel:rgba(255,255,255,.9); --accent:{accent}; --soft:color-mix(in srgb, {accent} 12%, transparent); }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",Arial,sans-serif; background:{background}; letter-spacing:0; }}
    .page {{ width:min(1120px,calc(100% - 32px)); margin:0 auto; padding:44px 0 36px; }}
    header {{ display:flex; justify-content:space-between; align-items:flex-end; gap:24px; margin-bottom:22px; padding-bottom:18px; border-bottom:1px solid var(--line); }}
    h1 {{ margin:0 0 10px; font-size:clamp(28px,4vw,44px); line-height:1.1; }}
    .meta, footer {{ color:var(--muted); font-size:14px; line-height:1.8; }}
    .count {{ min-width:210px; padding:16px 18px; border:1px solid var(--line); border-radius:8px; background:var(--panel); box-shadow:0 18px 48px rgba(23,32,51,.08); }}
    .count strong {{ display:block; font-size:30px; }}
    .grid {{ display:grid; gap:15px; }}
    .card {{ border:1px solid var(--line); border-radius:8px; background:var(--panel); box-shadow:0 16px 48px rgba(23,32,51,.07); }}
    .inner {{ padding:21px; }}
    .top {{ display:flex; justify-content:space-between; gap:16px; align-items:flex-start; }}
    a {{ color:var(--ink); text-decoration:none; }}
    a:hover {{ color:var(--accent); }}
    .name {{ font-size:22px; font-weight:760; overflow-wrap:anywhere; }}
    .author {{ margin-top:5px; color:var(--muted); font-size:13px; }}
    .stats {{ display:flex; justify-content:flex-end; gap:8px; flex-wrap:wrap; flex:0 0 auto; }}
    .pill {{ display:inline-flex; align-items:center; min-height:28px; padding:6px 10px; border-radius:999px; background:var(--soft); color:var(--accent); font-size:13px; font-weight:650; white-space:nowrap; }}
    .pill.gray {{ background:rgba(23,32,51,.06); color:#344057; }}
    p {{ margin:14px 0 0; color:#2d374b; line-height:1.75; font-size:15px; }}
    .label {{ margin-top:14px; color:#243047; font-size:14px; font-weight:740; }}
    ul {{ margin:7px 0 0; padding-left:20px; color:#354157; line-height:1.7; font-size:14px; }}
    footer {{ margin-top:24px; padding-top:18px; border-top:1px solid var(--line); }}
    footer a {{ color:var(--accent); }}
    @media (max-width:720px){{ header,.top{{display:block}}.count{{margin-top:16px}}.stats{{justify-content:flex-start;margin-top:12px}}.inner{{padding:18px}}.page{{width:min(100% - 22px,1120px);padding-top:28px}} }}
  </style>
</head>
<body>
  <main class="page">
    <header>
      <div>
        <h1>GitHub Trending 中文周报</h1>
        <p class="meta">数据抓取时间：{html.escape(generated_at)}<br>范围：GitHub Trending Weekly，不限定领域，按本周新增 Star 降序整理。</p>
      </div>
      <div class="count"><strong>{len(repos)}</strong><span class="meta">个热门项目</span></div>
    </header>
    <section class="grid">
{cards}
    </section>
    <footer>数据来源：<a href="{TRENDING_URL}">GitHub Trending Weekly</a>。说明由脚本根据项目名称、简介、语言和关键词生成，用于快速了解项目价值；具体能力以项目仓库为准。</footer>
  </main>
</body>
</html>
"""


def render_card(repo: Repo) -> str:
    features = "".join(f"<li>{html.escape(item)}</li>" for item in repo.features)
    return f"""      <article class="card"><div class="inner"><div class="top"><div><a class="name" href="{html.escape(repo.url)}">{html.escape(repo.name)}</a><div class="author">{html.escape(repo.author)}</div></div><div class="stats"><span class="pill">{html.escape(repo.language)}</span><span class="pill gray">{html.escape(repo.stars)} Stars</span><span class="pill">+{repo.weekly_stars:,}</span></div></div><p>{html.escape(repo.what)}</p><div class="label">核心功能</div><ul>{features}</ul><p><strong>可以怎么用：</strong>{html.escape(repo.usage)}</p></div></article>"""


def build_feishu_text(summary: dict, public_url: str | None) -> str:
    lines = [
        "GitHub Trending 中文周报",
        f"抓取时间：{summary['generated_at']}",
        f"项目数量：{len(summary['repos'])} 个",
    ]
    if public_url:
        lines.append(f"公开页面：{public_url}")
    lines.append("")
    for index, repo in enumerate(summary["repos"], start=1):
        lines.extend(
            [
                f"{index}. {repo['name']}（+{repo['weekly_stars']:,}）",
                repo["url"],
                f"是什么：{repo['what']}",
                f"可以怎么用：{repo['usage']}",
                "",
            ]
        )
    lines.append(f"数据来源：{TRENDING_URL}")
    return "\n".join(lines)


def send_feishu(text: str) -> None:
    webhook = os.getenv("FEISHU_BOT_WEBHOOK") or os.getenv("LARK_BOT_WEBHOOK")
    if not webhook:
        print("未配置 FEISHU_BOT_WEBHOOK 或 LARK_BOT_WEBHOOK，跳过飞书发送。")
        return
    body = json.dumps({"msg_type": "text", "content": {"text": text}}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(webhook, data=body, method="POST", headers={"Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = resp.read().decode("utf-8", errors="replace")
    print(f"飞书发送结果：{result}")


def generate(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(BEIJING).strftime("%Y-%m-%d %H:%M:%S +08:00")
    today = datetime.now(BEIJING).strftime("%Y-%m-%d")
    page = fetch(TRENDING_URL)
    repos = parse_trending(page, args.limit)
    if not repos:
        raise RuntimeError("未能从 GitHub Trending 解析到项目。")

    theme = choose_theme(output_dir)
    html_text = render_html(repos, generated_at, theme)
    html_path = output_dir / f"github-trending-weekly-{today}.html"
    index_path = output_dir / "index.html"
    html_path.write_text(html_text, encoding="utf-8")
    index_path.write_text(html_text, encoding="utf-8")

    summary = {
        "generated_at": generated_at,
        "source": TRENDING_URL,
        "html_file": html_path.name,
        "repos": [asdict(repo) for repo in repos],
    }
    Path(args.summary_file).parent.mkdir(parents=True, exist_ok=True)
    Path(args.summary_file).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已生成 {index_path} 和 {html_path}，共 {len(repos)} 个项目。")


def send_only(args: argparse.Namespace) -> None:
    summary = json.loads(Path(args.summary_file).read_text(encoding="utf-8"))
    text = build_feishu_text(summary, args.public_url)
    send_feishu(text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="site")
    parser.add_argument("--summary-file", default="site/report-summary.json")
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--send-only", action="store_true")
    parser.add_argument("--public-url")
    args = parser.parse_args()
    try:
        if args.send_only:
            send_only(args)
        else:
            generate(args)
        return 0
    except (urllib.error.URLError, TimeoutError, RuntimeError, OSError) as exc:
        print(f"运行失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
