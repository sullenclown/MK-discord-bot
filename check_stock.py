import os
import sys
import requests
from bs4 import BeautifulSoup

# 從 GitHub Secrets 讀取 4 個商品的網址（程式碼中 100% 找不到任何網址與品牌痕跡）
TARGET_PRODUCTS = [
    {"name": "Item A", "url": os.getenv("ITEM_A_URL")},
    {"name": "Item B", "url": os.getenv("ITEM_B_URL")},
    {"name": "Item C", "url": os.getenv("ITEM_C_URL")},
    {"name": "Item D", "url": os.getenv("ITEM_D_URL")},
]

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


def get_stock_status(product):
    """檢查單一項目的頁面庫存狀態"""
    if not product["url"]:
        return "❌ Secret Missing"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        response = requests.get(product["url"], headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        return f"❌ Request Failed ({e})"

    soup = BeautifulSoup(response.text, "html.parser")
    page_text = soup.get_text().lower()

    # 搜尋 class 包含 "add" 的購物車按鈕
    cart_button = soup.find("button", class_=lambda x: x and "add" in x.lower())

    # 檢查頁面是否包含缺貨關鍵字（包含 unavailable，確保覆蓋率 100%）
    is_out_of_stock = (
        "out of stock" in page_text
        or "sold out" in page_text
        or "unavailable" in page_text
    )

    # 判定邏輯：必須「無缺貨關鍵字」且「找到購物車按鈕」
    if (not is_out_of_stock) and (cart_button is not None):
        return "✅ **IN STOCK** - [Direct Link](" + product["url"] + ")"
    else:
        return "❌ Out of Stock"


def main():
    if not DISCORD_WEBHOOK_URL:
        print("Error: DISCORD_WEBHOOK_URL environment variable is missing.")
        sys.exit(1)

    # 判斷觸發來源：手動點擊 (workflow_dispatch) vs 自動排程
    is_manual_trigger = os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch"

    results = []
    has_any_stock = False

    print("Starting status check...")
    for product in TARGET_PRODUCTS:
        status = get_stock_status(product)
        results.append(f"• **{product['name']}**: {status}")
        if "IN STOCK" in status:
            has_any_stock = True

    # 發送條件：1. 任意商品補貨 2. 手動觸發查詢
    if has_any_stock or is_manual_trigger:
        content = (
            "@everyone 🔔 **Item Availability Alert!**"
            if has_any_stock
            else "🔍 **【Manual Status Report】**"
        )

        embed = {
            "title": "📊 Status Overview Report",
            "description": "\n".join(results),
            "color": 3066993 if has_any_stock else 3447003,  # 補貨綠色，查詢藍色
        }

        payload = {
            "username": "Status Bot",
            "content": content,
            "embeds": [embed],
        }

        try:
            res = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
            res.raise_for_status()
            print("Discord notification delivered successfully.")
        except Exception as e:
            print(f"Failed to deliver Discord notification: {e}")
    else:
        print("All items currently out of stock. Notification skipped.")


if __name__ == "__main__":
    main()
