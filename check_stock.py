import os
import sys
import requests
from bs4 import BeautifulSoup

# 設定要監控的多個丸久小山園商品列表 (可自由增減品項)
TARGET_PRODUCTS = [
    {
        "name": "五十鈴 100g 罐裝",
        "url": "https://www.marukyu-koyamaen.co.jp/ec/products/detail/101",  # 替換為實際網址
    },
    {
        "name": "青嵐 100g 罐裝",
        "url": "https://www.marukyu-koyamaen.co.jp/ec/products/detail/102",  # 替換為實際網址
    },
    {
        "name": "又玄 100g 罐裝",
        "url": "https://www.marukyu-koyamaen.co.jp/ec/products/detail/103",  # 替換為實際網址
    },
]

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


def check_product_stock(product):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ja-JP,ja;q=0.9",
    }

    try:
        response = requests.get(product["url"], headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"[{product['name']}] 網頁抓取失敗: {e}")
        return

    soup = BeautifulSoup(response.text, "html.parser")

    # 精準判斷：檢查是否有未禁用的購物車按鈕
    cart_button = soup.find(
        "button",
        attrs={
            "name": lambda x: x and "add-to-cart" in x
            or "cart" in x.lower()
            if x
            else False
        },
    )
    is_in_stock = cart_button and not cart_button.has_attr("disabled")

    if is_in_stock:
        payload = {
            "username": "丸久小山園補貨雷達",
            "embeds": [
                {
                    "title": f"🍵 【補貨通知】{product['name']}",
                    "description": f"檢測到商品已開放購買，請速前往搶購！\n[點我前往商品頁面]({product['url']})",
                    "color": 3066993,  # 翡翠綠
                }
            ],
        }
        res = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        if res.status_code == 204:
            print(f"[{product['name']}] 成功發送 Discord 補貨通知！")
        else:
            print(
                f"[{product['name']}] Discord 發送失敗: {res.status_code}, {res.text}"
            )
    else:
        print(f"[{product['name']}] 目前仍無庫存...")


def main():
    if not DISCORD_WEBHOOK_URL:
        print("錯誤：未設定 DISCORD_WEBHOOK_URL 變數")
        sys.exit(1)

    print("開始執行全品項庫存檢查...")
    for product in TARGET_PRODUCTS:
        check_product_stock(product)


if __name__ == "__main__":
    main()
