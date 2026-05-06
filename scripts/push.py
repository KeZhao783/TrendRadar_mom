#!/usr/bin/env python3
"""Read today's digest markdown and send to Feishu group chat as text."""

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


def _require(name: str) -> str:
    v = os.environ.get(name, "").strip()
    if not v:
        print(f"Missing env: {name}", file=sys.stderr)
        sys.exit(1)
    return v


def _today_shanghai() -> str:
    return datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")


def tenant_access_token(app_id: str, app_secret: str) -> str:
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    r = requests.post(
        url,
        json={"app_id": app_id, "app_secret": app_secret},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if data.get("code") != 0:
        print(json.dumps(data, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    return str(data["tenant_access_token"])


def send_text(token: str, chat_id: str, text: str) -> None:
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    params = {"receive_id_type": "chat_id"}
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    payload = {
        "receive_id": chat_id,
        "msg_type": "text",
        "content": json.dumps({"text": text}, ensure_ascii=False),
    }
    r = requests.post(url, params=params, headers=headers, json=payload, timeout=30)
    if not r.ok:
        print(r.text, file=sys.stderr)
        r.raise_for_status()
    data = r.json()
    if data.get("code") != 0:
        print(json.dumps(data, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


def main() -> None:
    app_id = _require("FEISHU_APP_ID")
    app_secret = _require("FEISHU_APP_SECRET")
    chat_id = _require("FEISHU_CHAT_ID")

    day = _today_shanghai()
    path = CONTENT_DIR / f"{day}.md"
    if not path.is_file():
        print(f"Missing file: {path}", file=sys.stderr)
        sys.exit(1)

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        print("Empty content", file=sys.stderr)
        sys.exit(1)

    # Feishu text messages are safest under ~20k; truncate with notice if needed.
    max_len = 18000
    if len(text) > max_len:
        text = text[: max_len - 50] + "\n\n…（正文过长已截断）"

    tok = tenant_access_token(app_id, app_secret)
    send_text(tok, chat_id, text)
    print("Feishu message sent OK")


if __name__ == "__main__":
    main()
