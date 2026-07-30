import os
import json
import re
import requests
from bs4 import BeautifulSoup

TARGET_URL = "https://event.jreast.co.jp/prd/?category=01:03&category=01:07&category=01:20&category=01:21&category=01:23&category=01:24&category=01:26&category=01:31&category=01:34&category=01:35&category=01:36&category=01:37&category=01:38&category=01:39&disp_number=80&orderby=2"
DATA_FILE = "known_events.json"

LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")


def build_card_bubble(title, link):
    """1つのイベントカード（バブル）要素を作成"""
    return {
        "type": "bubble",
        "size": "micro",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#008000",  # JR東日本風のグリーン
            "paddingAll": "8px",
            "contents": [
                {
                    "type": "text",
                    "text": "新着イベント",
                    "color": "#FFFFFF",
                    "weight": "bold",
                    "size": "xs",
                }
            ],
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "12px",
            "contents": [
                {
                    "type": "text",
                    "text": title,
                    "weight": "bold",
                    "size": "sm",
                    "wrap": True,
                    "maxLines": 3,
                }
            ],
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "8px",
            "contents": [
                {
                    "type": "button",
                    "action": {
                        "type": "uri",
                        "label": "詳細を見る",
                        "uri": link,
                    },
                    "style": "primary",
                    "color": "#008000",
                    "height": "sm",
                }
            ],
        },
    }


def send_line_flex(new_items):
    """LINEにFlex Message（カード型）で送信"""
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_TOKEN}",
    }

    # 上限10件までカード化（LINE API制限対策）
    bubbles = [build_card_bubble(title, link) for title, link in new_items[:10]]

    # 1件ならBubble単体、複数件ならCarousel（横スクロール）形式
    flex_contents = (
        bubbles[0]
        if len(bubbles) == 1
        else {"type": "carousel", "contents": bubbles}
    )

    payload = {
        "to": LINE_USER_ID,
        "messages": [
            {
                "type": "flex",
                "altText": f"【JR東日本】新着イベントが{len(new_items)}件追加されました",
                "contents": flex_contents,
            }
        ],
    }

    res = requests.post(url, headers=headers, json=payload)
    print(f"LINE API Response: {res.status_code}")


def fetch_events():
    """サイトからイベント一覧（タイトル・URL）を取得"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "ja,en-US;q=0.7,en;q=0.3",
    }
    res = requests.get(TARGET_URL, headers=headers)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "html.parser")
    events = {}

    # 詳細リンク（/activity/detail/ など）を持つaタグを抽出
    for a in soup.find_all("a", href=re.compile(r"/activity/detail/")):
        title = a.get_text(strip=True)
        link = a["href"]

        if not link.startswith("http"):
            link = "https://event.jreast.co.jp" + link

        if title and link:
            events[link] = title

    return events


def main():
    current_events = fetch_events()

    # 過去データの読み込み
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            known_events = json.load(f)
    else:
        known_events = {}

    # 新着判定
    new_items = [
        (title, link)
        for link, title in current_events.items()
        if link not in known_events
    ]

    if new_items:
        print(f"新着イベントを {len(new_items)} 件検出しました。通知を送信します。")
        send_line_flex(new_items)
    else:
        print("新着イベントはありませんでした。")

    # 最新状態を保存
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(current_events, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
