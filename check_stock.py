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

out_of_stock_text = "this product is currently out of stock and unavailable."
must_login_text = "you must register and login to shop."

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

if USER_COOKIE:
    headers["Cookie"] = USER_COOKIE

# 🔍 步驟 2：直接檢測各商品頁面狀態
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
            
            # 關鍵字檢查
            has_must_login_msg = must_login_text in page_text
            is_out_of_stock = out_of_stock_text in page_text
            has_add_to_cart = "add to cart" in page_text
            
            print(f"[{name}] MustLogin: {has_must_login_msg} | OutOfStockMsg: {is_out_of_stock} | AddToCart: {has_add_to_cart}")
            
            # --- 情況 A：未登入 / Cookie 失效 ---
            if has_must_login_msg:
                if is_out_of_stock:
                    # 未登入但頁面明示缺貨 -> 確定缺貨
                    results.append(f"❌ **{name}** {link_str}: OUT OF STOCK")
                else:
                    # 未登入且非缺貨 -> 提醒 Cookie 失效
                    results.append(f"⚠️ **{name}** {link_str}: Cookie Expired / Not Logged In")
                    has_any_alert = True
            
            # --- 情況 B：已登入狀態 ---
            else:
                if has_add_to_cart:
                    # 已登入且包含 Add to Cart -> 有貨可購買
                    results.append(f"✅ **{name}** {link_str}: **IN STOCK (Taiwan Available)**")
                    has_taiwan_stock = True
                    has_any_alert = True
                else:
                    results.append(f"❌ **{name}** {link_str}: OUT OF STOCK")
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
    color = 3066993    # 綠色：已登入且有貨可買
    title = "🚨 【IN STOCK ALERT】Taiwan Shipping Available"
elif has_any_alert:
    color = 16753920   # 橘色：Cookie 失效提醒
    title = "⚠️ 【SYSTEM NOTICE】Cookie Expired or Action Required"
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
