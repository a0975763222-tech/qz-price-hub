import json, asyncio, random, re, os, urllib.parse
from playwright.async_api import async_playwright

CONFIG_FILE = 'config.json'
OUTPUT_FILE = 'prices.json'

async def fetch_landmark_price(page, keyword, capacity):
    try:
        # 改用更輕量的網址，並放寬載入條件
        print(f"🔍 試探搜尋: {keyword}...")
        search_url = f"https://www.landtop.com.tw/products?q={urllib.parse.quote(keyword)}"
        
        # wait_until 改成 commit，只要一連上就開始，不等網頁轉完
        await page.goto(search_url, wait_until="commit", timeout=20000)
        
        # 給它一點時間反應，但不強求網路閒置
        await asyncio.sleep(10) 
        
        # 抓取所有看得見的文字
        content = await page.content()
        # 移除 HTML 標籤只留純文字
        clean_text = re.sub('<[^<]+?>', '', content).upper().replace(" ", "")
        
        model_nums = re.findall(r'\d+', keyword)
        cap_num = re.findall(r'\d+', capacity)[0] if re.findall(r'\d+', capacity) else ""

        if all(n in clean_text for n in model_nums) and cap_num in clean_text:
            # 尋找價格格式
            matches = re.findall(r'\$([\d,]+)', clean_text)
            if matches:
                # 通常搜尋結果第一個就是我們要的
                price = int(matches[0].replace(',', ''))
                print(f"✅ 成功摸到價格: {price}")
                return price
        
        print(f"⚠️ 摸到了網頁但沒看到 {keyword} 的數字")
        return None
    except Exception as e:
        print(f"❌ 連線失敗: 網站可能封鎖了 GitHub 伺服器")
        return None

async def main():
    print("🚀 詮展通訊 - 輕量化繞路測試...")
    config = json.load(open(CONFIG_FILE, 'r', encoding='utf-8'))
    prices = json.load(open(OUTPUT_FILE, 'r', encoding='utf-8')) if os.path.exists(OUTPUT_FILE) else {}
    
    async with async_playwright() as p:
        # 模擬更像一般人的電腦
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        for fid, det in config.items():
            price = await fetch_landmark_price(page, det['keyword'], det['capacity'])
            if price:
                if fid not in prices: prices[fid] = {}
                if det['capacity'] not in prices[fid]: prices[fid][det['capacity']] = {}
                prices[fid][det['capacity']]["landmark"] = price
        await browser.close()
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(prices, f, ensure_ascii=False, indent=4)
    print("🎉 測試結束")

if __name__ == "__main__":
    asyncio.run(main())
