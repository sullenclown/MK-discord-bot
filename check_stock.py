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

# 通用 Header（不帶 Cookie，像一般訪客）
guest_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# 會員 Header（帶有 Cookie）
auth_headers = guest_headers.copy()
if USER_COOKIE:
    auth_headers["Cookie"] = USER_COOKIE

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
        # 第一次請求：先用「訪客身分」存取商品頁（不消耗/暴露 Cookie 頻率）
        resp = requests.get(url, headers=guest_headers, timeout=10)
        
        if resp.status_code == 200:
            page_text = resp.text.lower()
            is_out_of_stock = out_of_stock_text in page_text
            
            if is_out_of_stock:
                # 全數缺貨：直接判定缺貨，完全不攜帶 Cookie 做二次請求
                print(f"[{name}] Status: OUT OF STOCK (Checked via Guest Mode)")
                results.append(f"❌ **{name}** {link_str}: OUT OF STOCK")
            
            else:
                # 【偵測到有貨！】第二次請求：帶入 USER_COOKIE 驗證登入與 Taiwan 運送權限
                print(f"[{name}] Status: IN STOCK DETECTED! Fetching with Cookie...")
                auth_resp = requests.get(url, headers=auth_headers, timeout=10)
                
                if auth_resp.status_code == 200:
                    auth_page_text = auth_resp.text.lower()
                    has_must_login_msg = must_login_text in auth_page_text
                    
                    if has_must_login_msg:
                        # 【有貨但未登入/Cookie失效】
                        results.append(f"⚠️ **{name}** {link_str}: **IN STOCK (Login Required / Update Cookie)**")
                        has_any_alert = True
                    else:
                        # 【有貨且已登入】檢查運費選單是否有 TAIWAN
                        has_taiwan_option = "taiwan" in auth_page_text
                        has_any_alert = True
                        
                        if has_taiwan_option:
                            results.append(f"✅ **{name}** {link_str}: **IN STOCK (Taiwan Available)**")
                            has_taiwan_stock = True
                        else:
                            results.append(f"⚠️ **{name}** {link_str}: **IN STOCK (Cannot Ship to Taiwan)**")
                else:
                    results.append(f"⚠️ **{name}** {link_str}: Auth Request HTTP {auth_resp.status_code}")
        else:
            results.append(f"⚠️ **{name}** {link_str}: HTTP {resp.status_code}")
    except Exception as e:
        results.append(f"⚠️ **{name}** {link_str}: Request Failed")

# 3. 組合 Discord Embed 卡片
now_utc = datetime.datetime.now(datetime.timezone.utc)
taipei_tz = datetime.timezone(datetime.timedelta(hours=8))
now_taipei = now_utc.astimezone(taipei_tz).strftime("%Y-%m-%d %H:%M:%S")

if has_taiwan_stock:
    color = 3066993    # 綠色
    title = "🚨 【IN STOCK ALERT】Taiwan Shipping Available"
elif has_any_alert:
    color = 16753920   # 橘色
    title = "⚠️ 【SYSTEM NOTICE】In Stock Alert / Action Required"
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
if response.status_code in [200, 204]:
    print("✅ Discord notification sent successfully!")
else:
    print(f"❌ Failed to send Discord notification: {response.status_code}")
