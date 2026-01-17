# 📺 IPTV 自动更新系统（Auto Update IPTV）

一个完全自动化、零维护的 IPTV 系统。
每天自动清洗直播源、测速、过滤、分类，并自动提交更新到 GitHub。
适用于电视、手机、平板、电脑等所有 IPTV 播放器。## 🚀 功能特点

- 每日自动更新（GitHub Actions 定时任务）
- 自动测速（过滤响应时间 > 2000ms 的慢源）
- 自动过滤失效源（仅保留 HTTP 200）
- 自动过滤购物台（momo、东森购物等）
- 自动生成干净的 m3u 文件
- 自动提交到 GitHub，无需人工操作
- 分类清晰：港澳台、海外、电影、无购物、综合## 📂 文件说明

| 文件名 | 内容说明 |
|-------|----------|
| live.m3u | 综合直播源（自动清洗 + 自动测速） |
| hk.m3u | 港澳台频道 |
| tw.m3u | 台湾频道 |
| oversea.m3u | 海外频道 |
| movie.m3u | 电影频道 |
| no-shopping.m3u | 无购物台版本 |
| update.py | 自动清洗 + 自动测速脚本 |
| .github/workflows/update.yml | GitHub Actions 自动更新配置 |## 📥 使用方法（导入到 IPTV 播放器）

将任意 .m3u 文件链接复制到你的 IPTV 播放器即可：

### 电视
- TiviMate
- OTT Navigator
- IPTV Smarters

### 手机
- Televizo
- iPlayTV
- Smarters Player

### 电脑
- VLC
- PotPlayer
- Kodi## 🔄 自动更新机制

系统每天会自动执行：

1. 扫描所有 .m3u 文件
2. 提取频道 URL
3. 测试是否可用（HTTP 200）
4. 测速（过滤 > 2000ms）
5. 过滤购物台
6. 生成干净的 m3u
7. 自动提交到 GitHub

无需任何人工操作，所有设备会自动同步最新频道。## 🛠 技术说明

- Python 自动脚本：update.py
- GitHub Actions 定时任务：update.yml
- 自动提交权限：permissions: contents: write
- 响应时间阈值：2000ms
- 超时保护：3 秒## ❤️ 致谢

本项目由 Hanbing 构建，使用 GitHub Actions 实现全自动 IPTV 更新系统。
