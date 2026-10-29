import os
import sys
import requests
from bs4 import BeautifulSoup

# 從 GitHub Secrets 讀取 4 個商品的獨立頁面網址
TARGET_PRODUCTS = [
    {"name": "Item A", "url": os.getenv("ITEM_A_URL")},
    {"name": "Item B", "url": os.getenv("ITEM_B_URL")},
    {"name": "Item C", "url": os.getenv("ITEM_C_URL")},
    {"name": "Item D", "url": os.getenv("ITEM_D_URL")},
]

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# 官網標準的缺貨提示字串（轉小寫）
OUT_OF_STOCK_TEXT = "this product is currently out of stock and unavailable."


def check_product_page_stock(product_url):
    """檢查商品獨立頁面是否包含明確的缺貨警語"""
    if not product_url:
        return "❌ Secret Missing", False

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        response = requests.get(product_url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        return f"❌ Request Failed ({e})", False

    soup = BeautifulSoup(response.text, "html.parser")
    page_text = soup.get_text().lower()

    # 反向判定邏輯：只要頁面『完全沒有』出現這段缺貨警語，即代表有貨！
    if OUT_OF_STOCK_TEXT not in page_text:
        return f"✅ **IN STOCK** - [Direct Link]({product_url})", True
    else:
        return "❌ Out of Stock", False


def main():
    if not DISCORD_WEBHOOK_URL:
        print("Error: DISCORD_WEBHOOK_URL environment variable is missing.")
        sys.exit(1)

    is_manual_trigger = os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch"

    results = []
    has_any_stock = False

    print("Starting inverted text precision check...")
    for product in TARGET_PRODUCTS:
        status, is_in_stock = check_product_page_stock(product["url"])
        results.append(f"• **{product['name']}**: {status}")
        if is_in_stock:
            has_any_stock = True

    # 發送通知條件：有貨發送通知，或手動點擊觸發查詢
    if has_any_stock or is_manual_trigger:
        content = (
            "@everyone 🔔 **Item Availability Alert!**"
            if has_any_stock
            else "🔍 **【Manual Status Report】**"
        )

        embed = {
            "title": "📊 Status Overview Report",
            "description": "\n".join(results),
            "color": 3066993 if has_any_stock else 3447003,
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
