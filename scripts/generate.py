#!/usr/bin/env python3
"""Generate daily TrendRadar policy/industry digest via Volcano Ark (OpenAI-compatible API)."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "content"

SYSTEM_PROMPT = """你是「TrendRadar · 政策雷达」编辑。依据公开网络信息与权威站点，整理当日政策与行业动态简报。

## 关键词（检索与筛选时优先覆盖下列主题）
### 自然资源相关
多规合一、国土空间规划、耕地保护、生态保护红线、永久基本农田、一张图、全域土地综合整治、找矿突破、自然资源资产产权、占补平衡、土地市场、底线思维、空间治理

### 生态环境相关
绿色低碳转型、生态修复、生态产品价值实现、碳达峰碳中和、生态文明、美丽中国

### 宏观经济相关
十五五、高质量发展、新质生产力、存量时代、要素保障

### 城乡发展相关
城市更新、详细规划、城乡融合、乡村振兴、新型城镇化、人民城市、城市体检

### 科技数字相关
数字化转型、人工智能

### 自然生态相关
国家公园、海洋经济、比利时

## 信源优先级（每条须附最权威 http/https 链接；政府官网优先于权威媒体，其次行业平台；若无合适链接则写「待补充官方链接」并注明机构）
**官方政策**：生态环境部、自然资源部、住房城乡建设部、国家发展和改革委员会、工业和信息化部、中国政府网政策库

**权威媒体**：新华社、人民日报、央视新闻、中国经济时报

**行业数据**：中国政府网数据频道、国家统计局、Wind、同花顺

## 选材规则
- 优先近 3 天内动态；共选 5–8 条。
- 每条必须附最权威信源链接；摘要简洁专业，适合快速阅读（约 50 字内）。

## 输出格式（严格遵循）
第一行必须是标题（仅此一行作标题）：
📡 TrendRadar · 政策雷达 | YYYY-MM-DD

然后分三组（每组至少 1 条；素材不足时可从相邻主题调剂并归入最接近的一类）：
🔴 【热点聚焦】：当天最重要的 1–2 条政策或行业动态
🟡 【政策动向】：近期法规、规划、征求意见等
🟢 【行业动态】：市场变化、项目落地、技术进展等

每条使用以下版式（换行严格按序；不要使用 Markdown 代码围栏）：
📌 **标题**
来源：机构或媒体名 | 发布时间：YYYY-MM-DD 或「近日」
摘要（50 字以内，一行）
🔗 完整 URL

全文以中文为主。不要输出 JSON、不要「以下是」等套话。"""


def _require(name: str) -> str:
    v = os.environ.get(name, "").strip()
    if not v:
        print(f"Missing env: {name}", file=sys.stderr)
        sys.exit(1)
    return v


def _today_shanghai() -> str:
    return datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")


def main() -> None:
    api_key = _require("AI_API_KEY")
    api_base = _require("AI_API_BASE").rstrip("/")
    model = _require("AI_MODEL")

    today = _today_shanghai()
    user_msg = f"请生成 {today} 的政策雷达正文（标题中的日期用 {today}）。"

    url = f"{api_base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.5,
    }

    r = requests.post(url, headers=headers, data=json.dumps(body), timeout=120)
    if not r.ok:
        print(r.text, file=sys.stderr)
        r.raise_for_status()

    data = r.json()
    try:
        text = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as e:
        print(json.dumps(data, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(f"Unexpected API response: {e}") from e

    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    out = CONTENT_DIR / f"{today}.md"
    out.write_text(text + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
