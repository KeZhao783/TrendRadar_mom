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
PUSH_CONFIG_PATH = ROOT / "push-config.json"

# 默认配置：与历史硬编码一致；在 push-config.json 缺失或非法时使用
DEFAULT_KEYWORDS: list[str] = [
    "多规合一",
    "国土空间规划",
    "耕地保护",
    "生态保护红线",
    "永久基本农田",
    "一张图",
    "全域土地综合整治",
    "找矿突破",
    "自然资源资产产权",
    "占补平衡",
    "土地市场",
    "底线思维",
    "空间治理",
    "绿色低碳转型",
    "生态修复",
    "生态产品价值实现",
    "碳达峰碳中和",
    "生态文明",
    "美丽中国",
    "十五五",
    "高质量发展",
    "新质生产力",
    "存量时代",
    "要素保障",
    "城市更新",
    "详细规划",
    "城乡融合",
    "乡村振兴",
    "新型城镇化",
    "人民城市",
    "城市体检",
    "数字化转型",
    "人工智能",
    "国家公园",
    "海洋经济",
    "比利时",
]

DEFAULT_SOURCES: list[str] = [
    "**官方政策**：生态环境部、自然资源部、住房城乡建设部、国家发展和改革委员会、工业和信息化部、中国政府网政策库",
    "**权威媒体**：新华社、人民日报、央视新闻、中国经济时报",
    "**行业数据**：中国政府网数据频道、国家统计局、Wind、同花顺",
]

# 占位符由运行时替换；勿使用 str.format，以免用户 JSON 中含花括号
SYSTEM_PROMPT_TEMPLATE = """你是「TrendRadar · 政策雷达」编辑。依据公开网络信息与权威站点，整理当日政策与行业动态简报。

## 关键词（检索与筛选时优先覆盖下列主题）
以下条目请同等重视并按相关性选编简报（来自用户配置，可合并理解相近概念）：
__KEYWORDS_BLOCK__

## 信源优先级（每条须附最权威 http/https 链接；政府官网优先于权威媒体，其次行业平台；若无合适链接则写「待补充官方链接」并注明机构）
按下列信源类型与机构名称检索并核对链接权威性（来自用户配置）：
__SOURCES_BLOCK__

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


def _normalize_string_list(value: object) -> list[str] | None:
    if not isinstance(value, list):
        return None
    out: list[str] = []
    for x in value:
        s = str(x).strip()
        if s:
            out.append(s)
    return out


def load_push_config(path: Path) -> tuple[list[str], list[str]]:
    """读取 push-config.json。返回 (keywords, sources)；异常或空字段时回退默认。"""
    if not path.is_file():
        print("push-config.json: file missing, using built-in defaults", file=sys.stderr)
        return list(DEFAULT_KEYWORDS), list(DEFAULT_SOURCES)

    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError) as e:
        print(f"push-config.json: read/parse failed ({e!r}), using built-in defaults", file=sys.stderr)
        return list(DEFAULT_KEYWORDS), list(DEFAULT_SOURCES)

    if not isinstance(data, dict):
        print("push-config.json: root must be an object, using built-in defaults", file=sys.stderr)
        return list(DEFAULT_KEYWORDS), list(DEFAULT_SOURCES)

    kw = _normalize_string_list(data.get("keywords"))
    src = _normalize_string_list(data.get("sources"))
    if kw is None or src is None:
        print("push-config.json: keywords/sources must be arrays of strings, using built-in defaults", file=sys.stderr)
        return list(DEFAULT_KEYWORDS), list(DEFAULT_SOURCES)

    if not kw:
        kw = list(DEFAULT_KEYWORDS)
        print("push-config.json: keywords empty after trim, filled from defaults", file=sys.stderr)
    if not src:
        src = list(DEFAULT_SOURCES)
        print("push-config.json: sources empty after trim, filled from defaults", file=sys.stderr)

    return kw, src


def build_keywords_block(keywords: list[str]) -> str:
    return "、".join(keywords)


def build_sources_block(sources: list[str]) -> str:
    return "\n".join(sources)


def build_system_prompt(keywords: list[str], sources: list[str]) -> str:
    kb = build_keywords_block(keywords)
    sb = build_sources_block(sources)
    return (
        SYSTEM_PROMPT_TEMPLATE.replace("__KEYWORDS_BLOCK__", kb).replace("__SOURCES_BLOCK__", sb)
    )


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

    keywords, sources = load_push_config(PUSH_CONFIG_PATH)
    system_prompt = build_system_prompt(keywords, sources)

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
            {"role": "system", "content": system_prompt},
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
