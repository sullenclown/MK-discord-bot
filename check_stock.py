import os
import datetime
import requests
from bs4 import BeautifulSoup

# 1. 讀取 Secrets 與環境變數
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
USER_COOKIE = os.getenv("USER_COOKIE", "")
TRIGGER_SOURCE = os.getenv("TRIGGER_SOURCE", "Unknown Source")

# 5 個品項設定（更新自訂代號與新增 Item W）
ITEMS = [
    {"name": "Item A", "url": os.getenv("ITEM_A_URL")},
    {"name": "Item Y", "url": os.getenv("ITEM_B_URL")},
    {"name": "Item I", "url": os.getenv("ITEM_C_URL")},
    {"name": "Item C", "url": os.getenv("ITEM_D_URL")},
    {"name": "Item W", "url": os.getenv("ITEM_W_URL")},
]

if not WEBHOOK_URL:
    print("❌ Error: DISCORD_WEBHOOK_URL is missing!")
    exit(1)

# 2. 爬蟲核心判定邏輯
out_of_stock_text = "this product is currently out of stock and unavailable."
results = []
has_any_alert = False      # 是否有任何商品有貨（觸發卡片通知）
has_taiwan_stock = False   # 是否有商品有貨且可寄台灣（觸發 @everyone）

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
            
            # 判斷 1：是否缺貨
            is_out_of_stock = out_of_stock_text in page_text
            
            # 判斷 2：下拉選單是否包含 Taiwan 選項
            has_taiwan_option = "taiwan" in page_text
            
            if is_out_of_stock:
                results.append(f"❌ **{name}** {link_str}: OUT OF STOCK")
            else:
                # 只要有貨就觸發卡片發送通知
                has_any_alert = True
                
                if has_taiwan_option:
                    results.append(f"✅ **{name}** {link_str}: **IN STOCK (Taiwan Available)**")
                    has_taiwan_stock = True
                else:
                    results.append(f"⚠️ **{name}** {link_str}: **IN STOCK (Cannot Ship to Taiwan)**")
        else:
            results.append(f"⚠️ **{name}** {link_str}: HTTP {resp.status_code}")
    except Exception as e:
        results.append(f"⚠️ **{name}** {link_str}: Request Failed")

# 3. 組合 Discord Embed 卡片
now_utc = datetime.datetime.now(datetime.timezone.utc)
taipei_tz = datetime.timezone(datetime.timedelta(hours=8))
now_taipei = now_utc.astimezone(taipei_tz).strftime("%Y-%m-%d %H:%M:%S")

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

# 只有在「有貨且可寄送台灣」時才帶入 @everyone
payload["content"] = "@everyone 有商品補貨且可寄台灣囉！" if has_taiwan_stock else ""

response = requests.post(WEBHOOK_URL, json=payload)
if response.status_code in [200, 204]:
    print("✅ Discord notification sent successfully!")
else:
    print(f"❌ Failed to send Discord notification: {response.status_code}")
