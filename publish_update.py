#!/usr/bin/env python3
"""把本地 data/dashboard.json 同步到 GitHub 仓库。

只使用 repo 权限，不需要 workflow 权限；适合本机定时任务。
"""
from __future__ import annotations

import base64
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "dashboard.json"
OWNER = "Evoliu07"
REPO = "dfh-public-radar"
PATH = "data/dashboard.json"
API = "https://api.github.com"
CST = timezone(timedelta(hours=8))


def get_token() -> str:
    result = subprocess.run(
        ["git", "credential-osxkeychain", "get"],
        input="protocol=https\nhost=github.com\n\n",
        text=True,
        capture_output=True,
    )
    for line in result.stdout.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1]
    return ""


def main() -> None:
    token = get_token()
    if not token:
        print("NO_GITHUB_TOKEN")
        sys.exit(1)

    local = DATA.read_bytes()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    url = f"{API}/repos/{OWNER}/{REPO}/contents/{PATH}"
    current = requests.get(url, headers=headers, timeout=60)
    if current.status_code == 200:
        info = current.json()
        remote = base64.b64decode(info["content"])
        if remote == local:
            print("NO_CHANGE")
            return
        sha = info["sha"]
    elif current.status_code == 404:
        sha = None
    else:
        print("GET_FAILED", current.status_code, current.text[:300])
        sys.exit(1)

    payload = {
        "message": f"chore: 更新公开数据 {datetime.now(CST):%Y-%m-%d %H:%M}",
        "content": base64.b64encode(local).decode("ascii"),
        "branch": "main",
    }
    if sha:
        payload["sha"] = sha

    result = requests.put(url, headers=headers, json=payload, timeout=60)
    if result.status_code not in (200, 201):
        print("PUT_FAILED", result.status_code, result.text[:500])
        sys.exit(1)
    data = result.json()
    print("UPDATED", data.get("commit", {}).get("html_url", ""))


if __name__ == "__main__":
    main()
