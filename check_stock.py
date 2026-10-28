import os
import sys
import requests
from bs4 import BeautifulSoup

TARGET_PRODUCTS = [
    {
        "name": "青嵐 (Aoarashi)",
        "url": "https://www.marukyu-koyamaen.co.jp/english/shop/products/11a1040c1",
    },
    {
        "name": "又玄 (Yugen)",
        "url": "https://www.marukyu-koyamaen.co.jp/english/shop/products/1171020c1",
    },
    {
        "name": "五十鈴 (Isuzu)",
        "url": "https://www.marukyu-koyamaen.co.jp/english/shop/products/1191040c1",
    },
    {
        "name": "千木の白 (Chigi no Shiro)",
        "url": "https://www.marukyu-koyamaen.co.jp/english/shop/products/1181040c1",
    },
]

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


def get_stock_status(product):
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

    cart_button = soup.find("button", class_=lambda x: x and "add" in x.lower())
    is_out_of_stock = "out of stock" in page_text or "sold out" in page_text

    if (not is_out_of_stock) and (cart_button is not None):
        return "✅ **有現貨！** [點我購買](" + product["url"] + ")"
    else:
        return "❌ 缺貨中 (Out of Stock)"


def main():
    if not DISCORD_WEBHOOK_URL:
        print("錯誤：未設定 DISCORD_WEBHOOK_URL 變數")
        sys.exit(1)

    # 判斷觸發來源：如果是手動按按鈕觸發 (workflow_dispatch)
    is_manual_trigger = os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch"

    results = []
    has_any_stock = False

    print("開始執行全品項庫存檢查...")
    for product in TARGET_PRODUCTS:
        status = get_stock_status(product)
        results.append(f"• **{product['name']}**: {status}")
        if "有現貨" in status:
            has_any_stock = True

    # 發送條件：
    # 1. 只要有任何商品補貨 (自動定時發送)
    # 2. 或者是由你手動點選按鈕觸發 (無論有無現貨都回報總覽)
    if has_any_stock or is_manual_trigger:
        content = (
            "@everyone 🍵 **丸久小山園補貨囉！**"
            if has_any_stock
            else "🔍 **【手動庫存查詢結果】**"
        )

        embed = {
            "title": "🍵 丸久小山園 庫存狀態總覽",
            "description": "\n".join(results),
            "color": 3066993 if has_any_stock else 3447003,  # 有貨綠色，無貨藍色
        }

        payload = {
            "username": "丸久小山園補貨雷達",
            "content": content,
            "embeds": [embed],
        }

        requests.post(DISCORD_WEBHOOK_URL, json=payload)
        print("已發送狀態至 Discord 頻道！")
    else:
        print("目前全品項均無庫存，未發送通知。")


if __name__ == "__main__":
    main()
