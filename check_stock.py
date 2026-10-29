import os
import sys
import requests
from bs4 import BeautifulSoup

# 從 GitHub Secrets 讀取 4 個商品的網址（程式碼中 100% 隱形）
TARGET_PRODUCTS = [
    {"name": "Item A", "url": os.getenv("ITEM_A_URL")},
    {"name": "Item B", "url": os.getenv("ITEM_B_URL")},
    {"name": "Item C", "url": os.getenv("ITEM_C_URL")},
    {"name": "Item D", "url": os.getenv("ITEM_D_URL")},
]

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


def get_stock_status(product):
    """檢查單一項目的購物車按鈕狀態（針對多規格頁面優化）"""
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

    # 1. 尋找購買表單內的提交按鈕或帶有 add/cart/buy 關鍵字的按鈕
    cart_button = soup.find(
        "button",
        class_=lambda x: x and any(k in x.lower() for k in ["add", "cart", "buy", "submit"])
    )
    
    # 若依 Class 找不到，退回尋找標準表單提交按鈕
    if not cart_button:
        cart_button = soup.find("button", attrs={"type": "submit"})

    # 2. 如果頁面上連購物車按鈕都沒有，判定為缺貨
    if cart_button is None:
        return "❌ Out of Stock"

    # 3. 取得按鈕文字與停用狀態
    button_text = cart_button.get_text().strip().lower()
    is_disabled = (
        cart_button.has_attr("disabled")
        or "disabled" in cart_button.get("class", [])
        or cart_button.get("aria-disabled") == "true"
    )

    # 4. 判定邏輯：只要按鈕文字含有 'add' 且按鈕「未被停用 (Not Disabled)」，即視為可購買！
    if "add" in button_text and not is_disabled:
        return "✅ **IN STOCK** - [Direct Link](" + product["url"] + ")"
    else:
        return "❌ Out of Stock"


def main():
    if not DISCORD_WEBHOOK_URL:
        print("Error: DISCORD_WEBHOOK_URL environment variable is missing.")
        sys.exit(1)

    is_manual_trigger = os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch"

    results = []
    has_any_stock = False

    print("Starting status check...")
    for product in TARGET_PRODUCTS:
        status = get_stock_status(product)
        results.append(f"• **{product['name']}**: {status}")
        if "IN STOCK" in status:
            has_any_stock = True

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
