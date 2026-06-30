# GitHub Trending AI 中文周报

这个项目采用和 `daily_stock_analysis` 类似的运行形态：

- `main.py` 作为统一入口
- `scripts/` 放核心生成逻辑
- `reports/`、`logs/` 作为运行产物目录
- `.github/workflows/weekly-trending.yml` 负责云端定时运行
- GitHub Pages 发布公开网页
- 飞书机器人发送 AI 项目榜单和公开页面链接

周报会从 GitHub Trending Weekly 中筛选 AI 相关项目，提取项目名、作者、Star 数、本周新增 Star、主要语言和仓库 URL，并生成中文解读：

- 一句话概述
- 核心功能
- 适用场景

## GitHub Actions

每周一北京时间 10:30 自动运行，对应 UTC cron：

```yaml
30 2 * * 1
```

也可以在 GitHub Actions 页面手动运行。

## Secrets

推荐使用和 `daily_stock_analysis` 一致的变量名：

- `OPENAI_API_KEY`：OpenAI API Key，用于生成更自然的中文解读
- `FEISHU_WEBHOOK_URL`：飞书机器人 webhook 地址
- `FEISHU_WEBHOOK_SECRET`：飞书签名密钥，可选

可选变量：

- `OPENAI_MODEL`：默认 `gpt-4.1-mini`
- `OPENAI_BASE_URL`：默认 `https://api.openai.com`
- `REPORT_LIMIT`：默认 `7`

为了兼容旧配置，也支持：

- `FEISHU_BOT_WEBHOOK`
- `LARK_BOT_WEBHOOK`

## Pages

仓库 `Settings -> Pages` 中选择 `GitHub Actions` 作为发布来源。运行成功后，公开页面会发布到 GitHub Pages。
