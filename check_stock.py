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
        except Exception as e
