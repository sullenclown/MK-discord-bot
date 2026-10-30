import os
import datetime
import requests

# 1. 讀取 Secrets 與環境變數（全數去識別化）
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

# 關鍵字設定
out_of_stock_text = "this product is currently out of stock and unavailable."
must_login_text = "you must register and login to shop."

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

if USER_COOKIE:
    headers["Cookie"] = USER_COOKIE

results = []
has_any_alert = False
has_taiwan_stock = False

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
            
            # 第一步：優先檢查是否「全數缺貨」
            is_out_of_stock = out_of_stock_text in page_text
            
            if is_out_of_stock:
                # 只要有缺貨警語，代表全規格缺貨，完全不需關心登入狀態
                results.append(f"❌ **{name}** {link_str}: OUT OF STOCK")
            
            else:
                # 第二步：無缺貨警語 = 肯定有貨！接著檢查登入狀態
                has_must_login_msg = must_login_text in page_text
                
                if has_must_login_msg:
                    # 【有貨但未登入】
                    results.append(f"⚠️ **{name}** {link_str}: **IN STOCK (Login Required / Update Cookie)**")
                    has_any_alert = True
                
                else:
                    # 【有貨且已登入】檢查選單有無 TAIWAN
                    has_taiwan_option = "taiwan" in page_text
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

# 設定卡片顏色與標題
if has_taiwan_stock:
    color = 3066993    # 綠色：完美符合（有貨且可寄台灣）
    title = "🚨 【IN STOCK ALERT】Taiwan Shipping Available"
elif has_any_alert:
    color = 16753920   # 橘色：有貨但未登入（需手動確認/更新Cookie）或無法寄台灣
    title = "⚠️ 【SYSTEM NOTICE】In Stock Alert / Action Required"
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
    "embeds": [embed],
    "content": "@everyone 🔔 有商品補貨且可寄台灣囉！" if has_taiwan_stock else ""
}

response = requests.post(WEBHOOK_URL, json=payload)
if response.status_code in [200, 204]:
    print("✅ Discord notification sent successfully!")
else:
    print(f"❌ Failed to send Discord notification: {response.status_code}")
