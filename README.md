# GitHub Trending 中文周报

这个仓库会用 GitHub Actions 在每周一北京时间 10:30 自动抓取 GitHub Trending Weekly，生成中文网页，发布到 GitHub Pages，并把完整项目列表和公开页面链接发送到飞书机器人。

## 需要配置

1. 在 GitHub 创建一个新仓库，并把本目录内容推送上去。
2. 在仓库的 `Settings -> Pages` 中，选择 `GitHub Actions` 作为发布来源。
3. 在仓库的 `Settings -> Secrets and variables -> Actions` 中添加 Secret：
   - `FEISHU_BOT_WEBHOOK`：你的飞书机器人 webhook。
4. 进入 `Actions` 页面，手动运行一次 `Weekly GitHub Trending Report`，确认能生成 Pages 并发送飞书消息。

## 运行结果

- GitHub Pages 首页：每次自动更新为最新一期周报。
- 历史文件：`github-trending-weekly-YYYY-MM-DD.html` 会保留在本次 Pages 构建产物中。
- 飞书消息：会展示全部入选项目，不只展示 Top 3，并附上公开页面链接。

## 时间说明

GitHub Actions 的定时任务使用 UTC 时间，所以工作流里写的是 `30 2 * * 1`，对应北京时间每周一 10:30。
