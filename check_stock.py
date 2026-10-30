import os
import datetime
import requests
from bs4 import BeautifulSoup

# 1. 讀取 Secrets 與環境變數
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
USER_COOKIE = os.getenv("USER_COOKIE", "")
TRIGGER_SOURCE = os.getenv("TRIGGER_SOURCE", "Unknown Source")

ITEMS = [
    {"name": "Item A", "url": os.getenv("ITEM_A_URL")},
    {"name": "Item I", "url": os.getenv("ITEM_I_URL")},
    {"name": "Item C", "url": os.getenv("ITEM_C_URL")},
    {"name": "Item Y", "url": os.getenv("ITEM_Y_URL")},
    {"name": "Item W", "url": os.getenv("ITEM_W_URL")},
]

if not WEBHOOK_URL:
    print("❌ Error: DISCORD_WEBHOOK_URL is missing!")
    exit(1)

results = []
has_any_alert = False
has_taiwan_stock = False

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

if USER_COOKIE:
    headers["Cookie"] = USER_COOKIE

for item in ITEMS:
    url = item["url"]
    name = item["name"]
    
    if not url:
        results.append(f"❓ **{name}**: Secret URL Missing")
        continue

    link_str = f"([Direct Link]({url}))" if url else ""

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            page_text = resp.text.lower()
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 🔍 步驟 1：檢測是否成功處於「登入狀態」
            # 登入後頁面通常會出現 logout / my account / my-account 等字眼
            is_logged_in = any(k in page_text for k in ["logout", "log out", "my account", "my-account"])
            
            # 🔍 步驟 2：精準尋找 Add to Cart 按鈕（避免抓到純文字或腳本）
            # 尋找是否有 class 或文字包含 add to cart 的按鈕
            cart_elements = soup.select(".single_add_to_cart_button, button.single_add_to_cart_button, input[name='add-to-cart']")
            has_add_to_cart = len(cart_elements) > 0 or ("add to cart" in page_text and "out of stock" not in page_text)
            
            # 🔍 步驟 3：檢查運費選單是否有 Taiwan
            has_taiwan_option = "taiwan" in page_text
            
            # 印出 Log 方便在 GitHub Actions Console 中核對
            print(f"[{name}] LoggedIn: {is_logged_in} | AddToCart: {has_add_to_cart} | TaiwanOpt: {has_taiwan_option}")
            
            if not is_logged_in and USER_COOKIE:
                # 代表 Cookie 已經失效了
                results.append(f"⚠️ **{name}** {link_str}: Cookie Expired (Not Logged In)")
            elif has_add_to_cart:
                has_any_alert = True
                if has_taiwan_option:
                    results.append(f"✅ **{name}** {link_str}: **IN STOCK (Taiwan Available)**")
                    has_taiwan_stock = True
                else:
                    results.append(f"⚠️ **{name}** {link_str}: **IN STOCK (Cannot Ship to Taiwan)**")
            else:
                results.append(f"❌ **{name}** {link_str}: OUT OF STOCK")
        else:
            results.append(f"⚠️ **{name}** {link_str}: HTTP {resp.status_code}")
    except Exception as e:
        results.append(f"⚠️ **{name}** {link_str}: Request Failed ({e})")

# 3. 組合 Discord Embed 卡片
now_utc = datetime.datetime.now(datetime.timezone.utc)
taipei_tz = datetime.timezone(datetime.timedelta(hours=8))
now_taipei = now_utc.astimezone(taipei_tz).strftime("%Y-%m-%d %H:%M:%S")

if has_taiwan_stock:
    color = 3066993    # 綠色
    title = "🚨 【IN STOCK ALERT】Taiwan Shipping Available"
elif has_any_alert:
    color = 16753920   # 橘色
    title = "⚠️ 【STOCK NOTICE】In Stock (No Taiwan Shipping)"
else:
    color = 10038562   # 灰色/紅色
    title = "🔍 【Status Report】Inventory Monitor"

embed = {
    "title": title,
    "description": "\n".join(results),
    "color": color,
    "fields": [
        {"name": "Trigger Source", "value": f"`{TRIGGER_SOURCE}`", "inline": True},
        {"name": "Check Time", "value": f"`{now_taipei} (UTC+8)`", "inline": True}
    ],
    "footer": {"text": f"Stock Monitor | Triggered via {TRIGGER_SOURCE}"}
}

payload = {
    "username": "Stock Monitor Bot",
    "embeds": [embed],
    "content": "@everyone 🔔 有商品補貨且可寄台灣囉！" if has_taiwan_stock else ""
}

response = requests.post(WEBHOOK_URL, json=payload)
