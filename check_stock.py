import os
import sys
import requests
from bs4 import BeautifulSoup

# 1. 從環境變數 (GitHub Secrets) 讀取 4 個商品的網址，程式碼中 100% 不留任何網址痕跡
TARGET_PRODUCTS = [
    {"name": "Item A", "url": os.getenv("ITEM_A_URL")},
    {"name": "Item B", "url": os.getenv("ITEM_B_URL")},
    {"name": "Item C", "url": os.getenv("ITEM_C_URL")},
    {"name": "Item D", "url": os.getenv("ITEM_D_URL")},
]

# 2. 從環境變數讀取 Discord Webhook 網址
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


def get_stock_status(product):
    """檢查單一項目的庫存狀態"""
    # 若該 Secrets 網址未設定或讀取失敗，進行防錯回報
    if not product["url"]:
        return "❌ 網址未設定 (Secret Missing)"

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
        return f"❌ 抓取失敗 ({e})"

    soup = BeautifulSoup(response.text, "html.parser")
    page_text = soup.get_text().lower()

    # 尋找 class 包含 "add" 的購物車按鈕
    cart_button = soup.find("button", class_=lambda x: x and "add" in x.lower())
    
    # 檢查頁面是否包含缺貨關鍵字
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
        print("錯誤：未設定 DISCORD_WEBHOOK_URL 環境變數")
        sys.exit(1)

    # 判斷觸發來源：如果是手動按按鈕觸發 (workflow_dispatch)
    is_manual_trigger = os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch"

    results = []
    has_any_stock = False

    print("開始執行項目狀態檢查...")
    for product in TARGET_PRODUCTS:
        status = get_stock_status(product)
        results.append(f"• **{product['name']}**: {status}")
        if "IN STOCK" in status:
            has_any_stock = True

    # 發送條件：
    # 1. 只要有任何商品補貨 (自動定時發送)
    # 2. 或者是由手動點選按鈕觸發 (無論有無現貨都回報總覽卡片)
    if has_any_stock or is_manual_trigger:
        content = (
            "@everyone 🔔 **Item Availability Alert!**"
            if has_any_stock
            else "🔍 **【Manual Status Report】**"
        )

        embed = {
            "title": "📊 Status Overview Report",
            "description": "\n".join(results),
            "color": 3066993 if has_any_stock else 3447003,  # 有貨綠色 (3066993)，無貨藍色 (3447003)
        }

        payload = {
            "username": "Status Bot",  # 去識別化的發送者名稱
            "content": content,
            "embeds": [embed],
        }

        try:
            res = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
            res.raise_for_status()
            print("已成功發送狀態至 Discord 頻道！")
        except Exception as e:
            print(f"發送至 Discord 失敗: {e}")
    else:
        print("目前全品項均無庫存，未發送通知。")


if __name__ == "__main__":
    main()
