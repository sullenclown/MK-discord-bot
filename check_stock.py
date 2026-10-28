import os
import sys
import requests
from bs4 import BeautifulSoup

# 您要監控的丸久小山園英文版官網商品清單
TARGET_PRODUCTS = [
    {
        "name": "五十鈴 (Isuzu)",
        "url": "https://www.marukyu-koyamaen.co.jp/english/shop/products/1181040c1",  # 請確認五十鈴正確網址
    },
    {
        "name": "又玄 (Yugen)",
        "url": "https://www.marukyu-koyamaen.co.jp/english/shop/products/1171020c1",
    },
    {
        "name": "青嵐 (Aoarashi)",
        "url": "https://www.marukyu-koyamaen.co.jp/english/shop/products/1191040c1",
    },
]

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


def check_product_stock(product):
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
        print(f"[{product['name']}] 網頁抓取失敗: {e}")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    page_text = soup.get_text().lower()

    # 英文版庫存判斷邏輯：
    # 1. 尋找 Add to Cart 按鈕
    cart_button = soup.find("button", class_=lambda x: x and "add" in x.lower())
    
    # 2. 檢查頁面中是否含有 Out of Stock 或 Sold Out
    is_out_of_stock = "out of stock" in page_text or "sold out" in page_text

    # 綜合判斷：只要沒有寫缺貨，且存在購物按鈕即代表有貨
    is_in_stock = (not is_out_of_stock) and (cart_button is not None)

    if is_in_stock:
        payload = {
            "username": "丸久小山園補貨雷達",
            "content": "@everyone 🍵 **丸久小山園補貨囉！**",  # 補貨時自動 @everyone 響鈴
            "embeds": [
                {
                    "title": f"【補貨通知】{product['name']}",
                    "description": f"檢測到商品已開放購買，請速前往搶購！\n[點我前往商品頁面]({product['url']})",
                    "color": 3066993,  # 翡翠綠
                }
            ],
        }
        res = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        if res.status_code in (200, 204):
            print(f"[{product['name']}] 成功發送 Discord 補貨通知！")
        else:
            print(f"[{product['name']}] Discord 發送失敗: {res.status_code}")
    else:
        print(f"[{product['name']}] 目前仍無庫存 (Out of Stock)...")


def main():
    if not DISCORD_WEBHOOK_URL:
        print("錯誤：未設定 DISCORD_WEBHOOK_URL 變數")
        sys.exit(1)

    print("開始執行全品項庫存
