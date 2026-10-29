import os
import sys
import requests
from bs4 import BeautifulSoup

# 1. 從 Secrets 讀取總覽頁網址與 4 個商品連結
CATALOG_URL = os.getenv("CATALOG_URL")
TARGET_PRODUCTS = [
    {"name": "Item A", "url": os.getenv("ITEM_A_URL")},
    {"name": "Item B", "url": os.getenv("ITEM_B_URL")},
    {"name": "Item C", "url": os.getenv("ITEM_C_URL")},
    {"name": "Item D", "url": os.getenv("ITEM_D_URL")},
]

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


def main():
    if not DISCORD_WEBHOOK_URL or not CATALOG_URL:
        print("Error: Required environment variables (DISCORD_WEBHOOK_URL / CATALOG_URL) are missing.")
        sys.exit(1)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    # 單次請求總覽頁面
    try:
        response = requests.get(CATALOG_URL, headers=headers, timeout=10)
        response.raise_for_status()
        catalog_html = response.text
    except Exception as e:
        print(f"Failed to fetch catalog page: {e}")
        sys.exit(1)

    soup = BeautifulSoup(catalog_html, "html.parser")
    is_manual_trigger = os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch"

    results = []
    has_any_stock = False

    print("Starting catalog status check...")
    for product in TARGET_PRODUCTS:
        item_url = product["url"]
        if not item_url:
            results.append(f"• **{product['name']}**: ❌ Secret Missing")
            continue

        # 提取商品 URL 的尾端編號做卡片定位
        url_path = item_url.rstrip("/").split("/")[-1]
        
        # 尋找包含該網址路徑的商品連結
        product_link = soup.find("a", href=lambda x: x and url_path in x)
        
        if not product_link:
            status = "❌ Item Not Found on Catalog"
        else:
            # 找到卡片外層容器
            card = product_link.find_parent(["div", "li", "article"]) or product_link
            card_text = card.get_text().lower()
            card_html = str(card).lower()

            # 檢查卡片 HTML 或文字中是否含有 sold out 標示
            if "sold out" in card_text or "sold-out" in card_html:
                status = "❌ Out of Stock"
            else:
                status = f"✅ **IN STOCK** - [Direct Link]({item_url})"
                has_any_stock = True

        results.append(f"• **{product['name']}**: {status}")

    # 發送通知條件
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
        print("All catalog items currently out of stock. Notification skipped.")


if __name__ == "__main__":
    main()
