# PL Project Status

## 目录结构
- `D:\Claude记忆\PL\` — 项目根目录（git repo）
- `index.html` — 网站主文件（已完成，待完善）
- `crawler.py` — 爬虫脚本（带断点续爬）
- `data\` — 爬取的数据
  - `teams.json` — 20队信息（含球员阵容）
  - `players_details.json` — 球员详细数据
  - `summary.json` — 联赛概览
  - `_checkpoint.json` — 爬虫进度检查点
  - `squad_*.json` — 各队阵容缓存
- `data\` 目录在 .gitignore 中

## 状态
- [x] 项目结构搭建
- [x] GitHub仓库创建: https://github.com/StephonStyle/PL
- [x] GitHub Pages 已启用: https://stephonstyle.github.io/PL/
- [x] 爬虫脚本编写（带断点续爬）
- [ ] 数据爬取（检查 data/_checkpoint.json 查看进度）
- [x] 网站框架完成（dark theme, mobile-first, 钻取导航）
- [ ] 网站完善（数据展示优化）
- [ ] 部署到 GitHub Pages

## 继续工作时
1. 检查 `data/_checkpoint.json` 看爬虫进度
2. 如果没跑完: `cd D:\Claude记忆\PL && python crawler.py` 继续
3. 数据完成后: 检查 index.html 数据展示是否正确
4. 部署: `git add . && git commit && git push origin main`
