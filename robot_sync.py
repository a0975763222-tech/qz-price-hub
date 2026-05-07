import json
import asyncio
import random
import re
import os
import urllib.parse
from playwright.async_api import async_playwright

# --- 設定區 ---
CONFIG_FILE = 'config.json'
OUTPUT_FILE = 'prices.json'

# 防封鎖：隨機 User-Agent 清單
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0"
]

def load_json(filepath):
    """讀取 JSON 檔案，若不存在則回傳空字典"""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(data, filepath):
    """儲存 JSON 檔案"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

async def fetch_landmark_price(page, keyword, capacity):
    """地標網通專用抓價邏輯"""
    try:
        # 將關鍵字轉為網址編碼，直接進入搜尋結果頁
        search_url = f"https://www.landtop.com.tw/products?q={urllib.parse.quote(keyword)}"
        print(f"🔍 正在搜尋地標網通: {keyword} {capacity}...")
        await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
        
        # 隨機延遲，模擬真人看網頁，避免被鎖 IP (3~6秒)
        await asyncio.sleep(random.uniform(3, 6))
        
        # 取得網頁內所有商品卡片的文字內容
        # 地標的商品卡片通常包含 a 標籤或特定的 class，這裡我們抓取整個網頁的主要商品區塊
        products = await page.locator("a[href*='/products/']").all()
        
        for product in products:
            text_content = await product.inner_text()
            text_content = text_content.upper().replace(" ", "") # 轉大寫去空白方便比對
            
            # 正規化我們的搜尋條件 (例如: 將 iPhone 17 Pro Max 轉成 IPHONE17PROMAX)
            target_keyword = keyword.upper().replace(" ", "")
            target_capacity = capacity.upper().replace("G", "GB") # 有時候網頁寫 256GB
            
            # 如果商品標題同時包含「型號」與「容量」
            if target_keyword in text_content and (capacity.upper() in text_content or target_capacity in text_content):
                # 用 Regex 抓取價格，尋找 $ 符號後面的數字 (例如 $43,000 -> 43000)
                price_match = re.search(r'\$([\d,]+)', text_content)
                if price_match:
                    price_str = price_match.group(1).replace(',', '')
                    price_int = int(price_str)
                    
                    # 異常排除：價格如果是 0 或 999999 就不採用
                    if 0 < price_int < 999999:
                        print(f"✅ 成功抓取: {keyword} {capacity} -> {price_int} 元")
                        return price_int
                        
        print(f"⚠️ 找不到符合條件的商品或價格: {keyword} {capacity}")
        return None
        
    except Exception as e:
        print(f"❌ 抓取 {keyword} 時發生錯誤: {str(e)}")
        return None

async def main():
    print("🚀 銓展通訊 - 地標專用爬蟲啟動...")
    
    # 讀取設定與現有報價
    config = load_json(CONFIG_FILE)
    prices = load_json(OUTPUT_FILE) # 讀取舊的，這樣可以保留手動輸入或其他欄位的資料
    
    if not config:
        print("❌ 找不到 config.json 或檔案為空！")
        return

    async with async_playwright() as p:
        # 啟動無頭瀏覽器
        browser = await p.chromium.launch(headless=True)
        # 隨機挑選 User-Agent
        context = await browser.new_context(user_agent=random.choice(USER_AGENTS))
        page = await context.new_page()
        
        for frontend_id, details in config.items():
            keyword = details.get("keyword")
            capacity = details.get("capacity")
            
            # 呼叫地標專屬抓價功能
            landmark_price = await fetch_landmark_price(page, keyword, capacity)
            
            if landmark_price:
                # 確保 prices.json 的巢狀結構存在
                if frontend_id not in prices:
                    prices[frontend_id] = {}
                if capacity not in prices[frontend_id]:
                    prices[frontend_id][capacity] = {}
                    
                # 寫入地標價格
                prices[frontend_id][capacity]["landmark"] = landmark_price
                
        await browser.close()
        
    # 輸出最終結果
    save_json(prices, OUTPUT_FILE)
    print("🎉 爬蟲執行完畢，資料已更新至 prices.json！")

if __name__ == "__main__":
    asyncio.run(main())
