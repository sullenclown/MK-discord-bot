import os
import sys
import requests
from bs4 import BeautifulSoup

CATALOG_URL = os.getenv("CATALOG_URL")
TARGET_PRODUCTS = [
    {"name": "Item A", "url": os.getenv("ITEM_A_URL")},
    {"name": "Item B", "url": os.getenv("ITEM_B_URL")},
    {"name": "Item C", "url": os.getenv("ITEM_C_URL")},
    {"name": "Item D", "url": os.getenv("ITEM_D_URL")},
]

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


def check_item_stock_on_catalog(soup, item_url):
    """針對帶有 SOLD OUT 圖片遮罩的總覽頁卡片進行深度比對"""
    if not item_url:
        return "❌ Secret Missing", False

    # 提取網址尾端編號 (例如 11a1040c1)
    url_path = item_url.rstrip("/").split("/")[-1]

    # 1. 尋找指向該商品的連結 <a>
    product_link = soup.find("a", href=lambda x: x and url_path in x)
    if not product_link:
        return "❌ Item Not Found", False

    # 2. 向上層尋找包覆「圖片 + 品名 + 價格」的最完整卡片容器
    # 優先尋找 <li>，若無則向上找 3 層 parent 以保證覆蓋圖片區塊
    card = product_link.find_parent("li")
    if not card:
        card = product_link.parent.parent.parent

    # 3. 抓取卡片內部所有文字與完整 HTML Code (小寫)
    card_text = card.get_text().lower()
    card_html = str(card).lower()

    # 4. 嚴格比對缺貨特徵（只要出現 sold out 相關關鍵字即判定缺貨）
    is_sold_out = (
        "sold out" in card_text
        or "soldout" in card_text
        or "out of stock" in card_text
        or "sold-out" in card_html
        or "soldout" in card_html
        or "out-of-stock" in card_html
    )

    if is_sold_out:
        return "❌ Out of Stock", False
    else:
        return f"✅ **IN STOCK** - [Direct Link]({item_url})", True


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

    print("Starting catalog precision check...")
    for product in TARGET_PRODUCTS:
        status, is_in_stock = check_item_stock_on_catalog(soup, product["url"])
        results.append(f"• **{product['name']}**: {status}")
        if is_in_stock:
            has_any_stock = True

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
