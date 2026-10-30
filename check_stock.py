import os
import datetime
import requests
from bs4 import BeautifulSoup

# 1. 讀取 Secrets 與環境變數
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
TRIGGER_SOURCE = os.getenv("TRIGGER_SOURCE", "Unknown Source")
EVENT_NAME = os.getenv("GITHUB_EVENT_NAME", "workflow_dispatch")

ITEMS = [
    {"name": "Item A", "url": os.getenv("ITEM_A_URL")},
    {"name": "Item B", "url": os.getenv("ITEM_B_URL")},
    {"name": "Item C", "url": os.getenv("ITEM_C_URL")},
    {"name": "Item D", "url": os.getenv("ITEM_D_URL")},
    {"name": "Item E", "url": os.getenv("ITEM_E_URL")},
]

# 檢查必要的 Secret 是否存在
if not WEBHOOK_URL:
    print("❌ Error: DISCORD_WEBHOOK_URL is missing!")
    exit(1)

# 2. 爬蟲核心判定邏輯（反向判斷）
out_of_stock_text = "this product is currently out of stock and unavailable."
results = []
has_in_stock = False

for item in ITEMS:
    url = item["url"]
    name = item["name"]
    
    if not url:
        results.append(f"❓ **{name}**: Secret URL Missing")
        continue

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            page_text = resp.text.lower()
            if out_of_stock_text in page_text:
                results.append(f"❌ **{name}**: OUT OF STOCK")
            else:
                results.append(f"✅ **{name}**: **IN STOCK**")
                has_in_stock = True
        else:
            results.append(f"⚠️ **{name}**: HTTP {resp.status_code}")
    except Exception as e:
        results.append(f"⚠️ **{name}**: Request Failed")

# 3. 組合 Discord Embed 卡片
now_utc = datetime.datetime.now(datetime.timezone.utc)
taipei_tz = datetime.timezone(datetime.timedelta(hours=8))
now_taipei = now_utc.astimezone(taipei_tz).strftime("%Y-%m-%d %H:%M:%S")

# 設定卡片顏色與標題
if has_in_stock:
    color = 3066993  # 綠色
    title = "🚨 【IN STOCK ALERT】Marukyu Koyamaen"
else:
    color = 10038562  # 紅色 / 灰色
    title = f"🔍 【Status Report】Marukyu Koyamaen"

embed = {
    "title": title,
    "description": "\n".join(results),
    "color": color,
    "fields": [
        {
            "name": "Trigger Source",
            "value": f"`{TRIGGER_SOURCE}`",
            "inline": True
        },
        {
            "name": "Check Time",
            "value": f"`{now_taipei} (UTC+8)`",
            "inline": True
        }
    ],
    "footer": {
        "text": f"MK Stock Monitor | Triggered via {TRIGGER_SOURCE}"
    }
}

payload = {
    "username": "Koyamaen Monitor",
    "embeds": [embed]
}

# 僅有貨或為手動/測試觸發時發送 Discord 通知
payload["content"] = "@everyone 有商品補貨囉！" if has_in_stock else ""

response = requests.post(WEBHOOK_URL, json=payload)
if response.status_code in [200, 204]:
    print("✅ Discord notification sent successfully!")
else:
    print(f"❌ Failed to send Discord notification: {response.status_code}")
