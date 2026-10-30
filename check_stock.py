import os
import datetime
import requests
from bs4 import BeautifulSoup

# 1. 讀取 Secrets 與環境變數
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
USER_COOKIE = os.getenv("USER_COOKIE", "")
TRIGGER_SOURCE = os.getenv("TRIGGER_SOURCE", "Unknown Source")

# 5 個品項設定（環境變數）
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

# 2. 爬蟲核心判定邏輯（改為正向比對 "add to cart"）
results = []
has_any_alert = False      # 是否有任何商品有貨（觸發卡片）
has_taiwan_stock = False   # 是否有商品有貨且可寄台灣（觸發卡片 + @everyone）

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
            
            # 正向判定 1：檢查頁面中是否有 "add to cart" 按鈕（代表至少有一個規格有貨）
            has_add_to_cart = "add to cart" in page_text
            
            # 判定 2：檢查運費選單中是否有 "taiwan" 選項
            has_taiwan_option = "taiwan" in page_text
            
            if has_add_to_cart:
                has_any_alert = True
                
                # 有貨 + 可寄送台灣
                if has_taiwan_option:
                    results.append(f"✅ **{name}** {link_str}: **IN STOCK (Taiwan Available)**")
                    has_taiwan_stock = True
                # 有貨 + 無法寄送台灣
                else:
                    results.append(f"⚠️ **{name}** {link_str}: **IN STOCK (Cannot Ship to Taiwan)**")
            else:
                # 頁面完全沒有 Add to Cart 按鈕，判定為全數缺貨
                results.append(f"❌ **{name}** {link_str}: OUT OF STOCK")
        else:
            results.append(f"⚠️ **{name}** {link_str}: HTTP {resp.status_code}")
    except Exception as e:
        results.append(f"⚠️ **{name}** {link_str}: Request Failed")

# 3. 組合 Discord Embed 卡片（去識別化）
now_utc = datetime.datetime.now(datetime.timezone.utc)
taipei_tz = datetime.timezone(datetime.timedelta(hours=8))
now_taipei = now_utc.astimezone(taipei_tz).strftime("%Y-%m-%d %H:%M:%S")

# 設定卡片顏色與標題
if has_taiwan_stock:
    color = 3066993    # 綠色：完美符合（有貨且可寄台灣）
    title = "🚨 【IN STOCK ALERT】Taiwan Shipping Available"
elif has_any_alert:
    color = 16753920   # 橘色：有貨但無法寄台灣
    title = "⚠️ 【STOCK NOTICE】In Stock (No Taiwan Shipping)"
else:
    color = 10038562   # 灰色/紅色：全數缺貨
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
    "embeds": [embed]
}

# 只有在「有貨且可寄送台灣」時才發送 @everyone 標記與鈴鐺 EMOJI
payload["content"] = "@everyone 🔔 有商品補貨且可寄台灣囉！" if has_taiwan_stock else ""

response = requests.post(WEBHOOK_URL, json=payload)
if response.status_code in [200, 204]:
    print("✅ Discord notification sent successfully!")
else:
    print(f"❌ Failed to send Discord notification: {response.status_code}")
