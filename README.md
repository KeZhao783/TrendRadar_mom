# TrendRadar_mom

「TrendRadar · 政策雷达」：通过 GitHub Actions 在每天北京时间 12:00 调用火山方舟生成简报，并推送到飞书群「麦苗世界」。

内容与关键词、信源版式对齐 WorkBuddy 自动化记忆文档（automation-1777780316977/memory.md）。

## 本地运行

```bash
pip install -r requirements.txt
export AI_API_KEY=...
export AI_API_BASE=https://ark.cn-beijing.volces.com/api/v3
export AI_MODEL=DeepSeek-V3.2
python scripts/generate.py

export FEISHU_APP_ID=...
export FEISHU_APP_SECRET=...
export FEISHU_CHAT_ID=...
python scripts/push.py
```

生成结果写入 `content/YYYY-MM-DD.md`（目录已加入 `.gitignore`）。

## GitHub Secrets

在仓库 Settings → Secrets and variables → Actions 中新建：

| Secret | 说明 |
|--------|------|
| FEISHU_APP_ID | 飞书应用 App ID（与 memory 中 Bot 一致：cli_a97c03c7b5389ccd） |
| FEISHU_APP_SECRET | 飞书应用 App Secret（仅填在 Secret，勿写入仓库） |
| FEISHU_CHAT_ID | 目标群 chat_id：oc_7b56fda3687725a06bf3ce9ceaf0e018 |
| AI_API_KEY | 火山方舟 API Key |
| AI_API_BASE | https://ark.cn-beijing.volces.com/api/v3 |
| AI_MODEL | 例如 DeepSeek-V3.2 |

配置完成后，可在 Actions 里手动运行 TrendRadar Mom Daily（workflow_dispatch）做联调。

## 定时说明

工作流使用 UTC cron `0 4 * * *`，对应北京时间当日 12:00。

## 仓库

远程（建议）：https://github.com/KeZhao783/TrendRadar_mom

首次推送示例：

```bash
cd D:\TrendRadar_mom
git init
git add .
git commit -m "feat: init TrendRadar_mom from dad template with policy radar"
git branch -M main
git remote add origin https://github.com/KeZhao783/TrendRadar_mom.git
git push -u origin main
```

## 与 TrendRadar_dad 的关系

本仓库由 TrendRadar_dad 复制而来；scripts/push.py 与依赖与 dad 相同，scripts/generate.py 与定时、飞书目标按 policy 自动化要求单独配置。
