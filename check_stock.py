import os
import datetime
import requests

# 1. 讀取 Secrets 與環境變數（100% 去識別化）
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
ACCOUNT_URL = os.getenv("ACCOUNT_URL")
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

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

if USER_COOKIE:
    headers["Cookie"] = USER_COOKIE

# 🔍 步驟 1：先檢查是否登入 (檢查 ACCOUNT_URL 頁面是否有 log out)
is_logged_in = False
if USER_COOKIE and ACCOUNT_URL:
    try:
        acc_resp = requests.get(ACCOUNT_URL, headers=headers, timeout=10)
        if acc_resp.status_code == 200 and "log out" in acc_resp.text.lower():
            is_logged_in = True
            print("✅ Login Status: LOGGED IN")
        else:
            print("⚠️ Login Status: NOT LOGGED IN / COOKIE EXPIRED")
    except Exception as e:
        print(f"⚠️ Account Check Exception: {e}")

# 🔍 步驟 2：進行商品頁面檢查
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
            
            # --- 情況 A：已登入狀態 ---
            if is_logged_in:
                has_add_to_cart = "add to cart" in page_text
                
                print(f"[{name}] LoggedIn: True | AddToCart: {has_add_to_cart}")
                
                if has_add_to_cart:
                    # 已登入且有 Add to Cart -> 肯定可以寄台灣購買
                    results.append(f"✅ **{name}** {link_str}: **IN STOCK (Taiwan Available)**")
                    has_taiwan_stock = True
                    has_any_alert = True
                else:
                    results.append(f"❌ **{name}** {link_str}: OUT OF STOCK")
            
            # --- 情況 B：未登入狀態 ---
            else:
                is_out_of_stock = out_of_stock_text in page_text
                
                print(f"[{name}] LoggedIn: False | OutOfStockText: {is_out_of_stock}")
                
                if is_out_of_stock:
                    # 未登入但頁面明示缺貨 -> 精準判定缺貨
                    results.append(f"❌ **{name}** {link_str}: OUT OF STOCK")
                else:
                    # 未登入且不是缺貨警語 -> 提示 Cookie 到期無法確認購買 state
                    results.append(f"⚠️ **{name}** {link_str}: Cookie Expired / Not Logged In")
                    has_any_alert = True
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
