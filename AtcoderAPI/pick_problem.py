#!/usr/bin/env python3
"""
AtCoder Problems の公開APIを使い、config.json で指定したレベル(問題番号: A/B/C...)のうち
まだACしていない問題をランダムに1問選んで、通知用の文字列を標準出力に出力する。

設定は config.json から読み込む。以下の環境変数でも上書き可能
(GitHub Actions の secrets 経由でユーザーIDを渡したい場合などに使用):
  - ATCODER_USER_ID : config.json の atcoder_user_id を上書き
  - LEVELS           : カンマ区切りで config.json の levels を上書き (例: "A,B")

提出履歴はすべて取得すると件数が多いユーザーでは時間がかかるため、
data/ac_cache.json に「どこまで取得したか(last_epoch_second)」と
「これまでにACした問題ID一覧」をキャッシュし、次回以降は差分だけ取得する。
"""
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request

BASE = "https://kenkoooo.com/atcoder"
PROBLEMS_URL = f"{BASE}/resources/problems.json"
SUBMISSIONS_URL = f"{BASE}/atcoder-api/v3/user/submissions"

CONFIG_PATH = os.environ.get("CONFIG_PATH", "config.json")
CACHE_PATH = os.environ.get("CACHE_PATH", "data/ac_cache.json")

# AtCoder Problems API のマナーとして、連続アクセス時は1秒以上あける
REQUEST_INTERVAL_SEC = 2.0


def fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "daily-atcoder-notifier/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.URLError as e:
        print(f"[ERROR] failed to fetch {url}: {e}", file=sys.stderr)
        sys.exit(1)


def load_config(path: str) -> dict:
    if not os.path.exists(path):
        print(f"[ERROR] config file not found: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        config = json.load(f)

    if os.environ.get("ATCODER_USER_ID"):
        config["atcoder_user_id"] = os.environ["ATCODER_USER_ID"]
    if os.environ.get("LEVELS"):
        config["levels"] = [x.strip().upper() for x in os.environ["LEVELS"].split(",") if x.strip()]

    if not config.get("atcoder_user_id"):
        print(
            "[ERROR] atcoder_user_id が config.json に設定されていません "
            "(または環境変数 ATCODER_USER_ID を設定してください)。",
            file=sys.stderr,
        )
        sys.exit(1)

    config.setdefault("levels", ["A"])
    config["levels"] = [lv.upper() for lv in config["levels"]]
    config.setdefault("exclude_contest_prefixes", [])
    return config


def load_cache(path: str, user_id: str) -> dict:
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            cache = json.load(f)
        if cache.get("user_id") == user_id:
            return cache
    return {"user_id": user_id, "last_epoch_second": 0, "ac_problem_ids": []}


def save_cache(path: str, cache: dict):
    dirname = os.path.dirname(path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def update_ac_set(user_id: str, cache: dict) -> set:
    """提出履歴を差分取得し、ACした問題IDの集合を返す。cache はその場で更新される。"""
    ac_ids = set(cache["ac_problem_ids"])
    from_second = cache["last_epoch_second"]

    while True:
        url = f"{SUBMISSIONS_URL}?user={user_id}&from_second={from_second}"
        submissions = fetch_json(url)
        if not submissions:
            break
        for sub in submissions:
            if sub.get("result") == "AC":
                ac_ids.add(sub["problem_id"])
            from_second = max(from_second, sub["epoch_second"] + 1)
        if len(submissions) < 500:
            break
        time.sleep(REQUEST_INTERVAL_SEC)

    cache["ac_problem_ids"] = sorted(ac_ids)
    cache["last_epoch_second"] = from_second
    return ac_ids


def pick_unsolved_problem(problems: list, ac_ids: set, levels: list, exclude_prefixes: list):
    candidates = [
        p
        for p in problems
        if p["problem_index"].upper() in levels
        and p["id"] not in ac_ids
        and not any(p["contest_id"].startswith(pref) for pref in exclude_prefixes)
    ]
    if not candidates:
        return None
    return random.choice(candidates)


def format_message(problem: dict) -> str:
    url = f"https://atcoder.jp/contests/{problem['contest_id']}/tasks/{problem['id']}"
    return f"【今日の1問（Level {problem['problem_index']}）】{problem['title']}\n{url}"


def main():
    config = load_config(CONFIG_PATH)
    user_id = config["atcoder_user_id"]
    levels = config["levels"]
    exclude_prefixes = config.get("exclude_contest_prefixes", [])

    problems = fetch_json(PROBLEMS_URL)
    time.sleep(REQUEST_INTERVAL_SEC)

    cache = load_cache(CACHE_PATH, user_id)
    ac_ids = update_ac_set(user_id, cache)
    save_cache(CACHE_PATH, cache)

    problem = pick_unsolved_problem(problems, ac_ids, levels, exclude_prefixes)

    if problem is None:
        message = f"Level {'/'.join(levels)} の問題は全てAC済みです！おめでとうございます 🎉"
    else:
        message = format_message(problem)

    print(message)

    # GitHub Actions の後続ステップで参照できるよう、GITHUB_OUTPUT にも書き出す
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write("message<<EOF\n")
            f.write(message + "\n")
            f.write("EOF\n")


if __name__ == "__main__":
    main()
