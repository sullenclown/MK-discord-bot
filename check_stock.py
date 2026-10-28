import os
import sys
import requests

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


def send_test_notification():
    if not DISCORD_WEBHOOK_URL:
        print("錯誤：未設定 DISCORD_WEBHOOK_URL 變數")
        sys.exit(1)

    payload = {
        "username": "丸久小山園補貨雷達",
        "content": "@everyone 🍵 **【系統測試】丸久小山園補貨雷達測試通知！**",
        "embeds": [
            {
                "title": "🍵 【測試通知】五十鈴 (Isuzu) 100g 罐裝",
                "description": "這是一則系統測試訊息，確認您的 Discord Webhook 能夠正常接收推播與響鈴提醒！\n\n[點我前往丸久小山園官網](https://www.marukyu-koyamaen.co.jp/english/shop/products/1181040c1)",
                "color": 3066993,  # 翡翠綠
                "footer": {"text": "丸久小山園監控系統 • 測試成功"},
            }
        ],
    }

    res = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    if res.status_code in (200, 204):
        print("✅ 測試訊息發送成功！請檢查您的 Discord 頻道。")
    else:
        print(f"❌ 測試訊息發送失敗，狀態碼: {res.status_code}")


if __name__ == "__main__":
    send_test_notification()
