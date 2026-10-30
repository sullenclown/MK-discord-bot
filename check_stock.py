import os
import datetime
import requests
from bs4 import BeautifulSoup

# 1. 讀取 Secrets 與環境變數（100% 去識別化）
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
ACCOUNT_URL = os.getenv("ACCOUNT_URL")
USER_COOKIE = os.getenv("USER_COOKIE", "")
TRIGGER_SOURCE = os.getenv("TRIGGER_SOURCE", "Unknown Source")

# 5 個品項設定（完全對應個別的 Secret 名稱）
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

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

if USER_COOKIE:
    headers["Cookie"] = USER_COOKIE

# 🔍 步驟 1：優先透過 Secrets 中的 ACCOUNT_URL 驗證登入狀態
is_logged_in = False
if USER_COOKIE and ACCOUNT_URL:
    try:
        acc_resp = requests.get(ACCOUNT_URL, headers=headers, timeout=10)
        if acc_resp.status_code == 200 and "log out" in acc_resp.text.lower():
            is_logged_in = True
            print("✅ Login Verification: SUCCESS (LOG OUT found on account page)")
        else:
            print("⚠️ Login Verification: FAILED (LOG OUT not found or Cookie expired)")
    except Exception as e:
        print(f"⚠️ Account Check Failed: {e}")

# 🔍 步驟 2：進行商品庫存與寄送區域檢測
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
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 正向尋找是否有真實可購買的 Add to Cart 按鈕或元素
            cart_elements = soup.select(".single_add_to_cart_button, button.single_add_to_cart_button, input[name='add-to-cart']")
            has_add_to_cart = len(cart_elements) > 0 or ("add to cart" in page_text and "out of stock" not in page_text)
            
            # 檢查運費選單是否有 Taiwan
            has_taiwan_option = "taiwan" in page_text
            
            print(f"[{name}] AddToCart: {has_add_to_cart} | TaiwanOpt: {has_taiwan_option}")
            
            # 狀態判定
            if not is_logged_in and USER_COOKIE:
                results.append(f"⚠️ **{name}** {link_str}: Cookie Expired / Not Logged In")
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
        results.append(f"⚠️ **{name}** {link_str}: Request Failed")

# 3. 組合 Discord Embed 卡片（去識別化）
now_utc = datetime.datetime.now(datetime.timezone.utc)
taipei_tz = datetime.timezone(datetime.timedelta(hours=8))
now_taipei = now_utc.astimezone(taipei_tz).strftime("%Y-%m-%d %H:%M:%S")

# 設定卡片顏色與標題
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
if response.status_code in [200, 204]:
    print("✅ Discord notification sent successfully!")
else:
    print(f"❌ Failed to send Discord notification: {response.status_code}")
