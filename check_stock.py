import os
import datetime
import requests

# 1. 讀取 Secrets 與環境變數（100% 去識別化，不殘留任何真實網址與品牌資訊）
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
USER_COOKIE = os.getenv("USER_COOKIE", "")
TRIGGER_SOURCE = os.getenv("TRIGGER_SOURCE", "Unknown Source")

# 手動測試專用網址（完全由 Secrets 讀取，若未設定則自動回退至 ITEM_A_URL）
TEST_ITEM_URL = os.getenv("TEST_ITEM_URL") or os.getenv("ITEM_A_URL")

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

# 商品頁面特徵警語關鍵字
out_of_stock_text = "this product is currently out of stock and unavailable."
must_login_text = "you must register and login to shop."

guest_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

auth_headers = guest_headers.copy()
if USER_COOKIE:
    auth_headers["Cookie"] = USER_COOKIE

results = []
has_any_alert = False
has_taiwan_stock = False

# ---------------------------------------------------------
# 🧪 模式 1：手動強制測試模式 (TRIGGER_SOURCE == "Manual_Test")
# ---------------------------------------------------------
if TRIGGER_SOURCE == "Manual_Test":
    print("🧪 [MANUAL TEST MODE ACTIVATED]")
    has_any_alert = True
    
    if not TEST_ITEM_URL:
        results.append("❓ **TEST RESULT**: TEST_ITEM_URL Secret Missing")
    else:
        try:
            print("🔍 Testing active URL with Cookie in manual mode...")
            resp = requests.get(TEST_ITEM_URL, headers=auth_headers, timeout=10)
            
            if resp.status_code == 200:
                page_text = resp.text.lower()
                has_must_login_msg = must_login_text in page_text
                has_taiwan_option = "taiwan" in page_text
                
                print(f"[Manual Test Result] MustLogin: {has_must_login_msg} | TaiwanOption: {has_taiwan_option}")
                
                if has_must_login_msg:
                    results.append("❌ **TEST RESULT**: Cookie Expired / Not Logged In")
                else:
                    results.append("✅ **TEST RESULT**: Cookie Verified & Logged In!")
                    if has_taiwan_option:
                        results.append("🎉 **TAIWAN OPTION**: Found in Shipping Menu!")
                    else:
                        results.append("⚠️ **TAIWAN OPTION**: Not Found in Menu.")
            else:
                results.append(f"⚠️ **TEST RESULT**: HTTP {resp.status_code}")
        except Exception as e:
            results.append(f"⚠️ **TEST RESULT**: Request Failed ({e})")

# ---------------------------------------------------------
# 🛡️ 模式 2：日常正式監控模式 (按需帶入 Cookie，全缺貨時完全不發送 Cookie)
# ---------------------------------------------------------
else:
    for item in ITEMS:
        url = item["url"]
        name = item["name"]
        
        if not url:
            results.append(f"❓ **{name}**: Secret URL Missing")
            continue

        link_str = f"([Direct Link]({url}))" if url else ""

        try:
            # 第一次請求：訪客身分無 Cookie 存取（降低暴露與失效風險）
            resp = requests.get(url, headers=guest_headers, timeout=10)
            
            if resp.status_code == 200:
                page_text = resp.text.lower()
                is_out_of_stock = out_of_stock_text in page_text
                
                if is_out_of_stock:
                    # 全數缺貨：直接判定缺貨，完全不使用 Cookie 做二次連線
                    print(f"[{name}] Status: OUT OF STOCK (Guest Mode)")
                    results.append(f"❌ **{name}** {link_str}: OUT OF STOCK")
                
                else:
                    # 【偵測到有貨！】第二次請求：帶入 USER_COOKIE 驗證登入與 Taiwan 運送選單
                    print(f"[{name}] Status: IN STOCK DETECTED! Fetching with Cookie...")
                    auth_resp = requests.get(url, headers=auth_headers, timeout=10)
                    
                    if auth_resp.status_code == 200:
                        auth_page_text = auth_resp.text.lower()
                        has_must_login_msg = must_login_text in auth_page_text
                        
                        if has_must_login_msg:
                            results.append(f"⚠️ **{name}** {link_str}: **IN STOCK (Login Required / Update Cookie)**")
                            has_any_alert = True
                        else:
                            has_taiwan_option = "taiwan" in auth_page_text
                            has_any_alert = True
                            
                            if has_taiwan_option:
                                results.append(f"✅ **{name}** {link_str}: **IN STOCK (Taiwan Available)**")
                                has_taiwan_stock = True
                            else:
                                results.append(f"⚠️ **{name}** {link_str}: **IN STOCK (Cannot Ship to Taiwan)**")
                    else:
                        results.append(f"⚠️ **{name}** {link_str}: Auth HTTP {auth_resp.status_code}")
            else:
                results.append(f"⚠️ **{name}** {link_str}: HTTP {resp.status_code}")
        except Exception as e:
            results.append(f"⚠️ **{name}** {link_str}: Request Failed")

# 3. 組合 Discord Embed 卡片
now_utc = datetime.datetime.now(datetime.timezone.utc)
taipei_tz = datetime.timezone(datetime.timedelta(hours=8))
now_taipei = now_utc.astimezone(taipei_tz).strftime("%Y-%m-%d %H:%M:%S")

if TRIGGER_SOURCE == "Manual_Test":
    color = 3447003    # 藍色：手動測試模式專屬
    title = "🧪 【MANUAL TEST REPORT】Cookie & Menu Verification"
elif has_taiwan_stock:
    color = 3066993    # 綠色：補貨可寄台灣
    title = "🚨 【IN STOCK ALERT】Taiwan Shipping Available"
elif has_any_alert:
    color = 16753920   # 橘色：未登入警告或無法寄台灣
    title = "⚠️ 【SYSTEM NOTICE】In Stock Alert / Action Required"
else:
    color = 10038562   # 灰色/紅色：全缺貨靜默報告
    title = "🔍 【Status Report】Inventory Monitor"

embed = {
    "title": title,
    "description": "\n".join(results),
    "color": color,
    "fields": [
        {"name": "Trigger Source", "value": f"`{TRIGGER_SOURCE}`", "inline": True},
        {"name": "Check Time", "value": f"`{now_taipei} (UTC+8)`", "inline": True}
    ],
    "footer": {"text": f"Stock Monitor | Mode: {TRIGGER_SOURCE}"}
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
