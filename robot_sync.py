import json, asyncio, random, re, os, urllib.parse
from playwright.async_api import async_playwright

CONFIG_FILE = 'config.json'
OUTPUT_FILE = 'prices.json'

async def fetch_landmark_price(page, keyword, capacity):
    try:
        # 改成先去首頁，模擬真人搜尋
        print(f"🔍 準備搜尋: {keyword} {capacity}...")
        await page.goto("https://www.landtop.com.tw/products", wait_until="networkidle", timeout=30000)
        
        # 找到搜尋框並輸入
        search_box = page.locator("input[name='q']").first
        await search_box.fill(keyword)
        await search_box.press("Enter")
        
        # 強制多等一下，等資料噴出來
        await asyncio.sleep(8) 
        
        # 這次我們抓全網頁文字，看看到底有什麼
        body_text = await page.inner_text("body")
        lines = body_text.split('\n')
        
        model_nums = re.findall(r'\d+', keyword)
        cap_num = re.findall(r'\d+', capacity)[0] if re.findall(r'\d+', capacity) else ""

        for line in lines:
            line_upper = line.upper().replace(" ", "")
            # 只要這一行有手機型號跟容量數字
            if all(n in line_upper for n in model_nums) and cap_num in line_upper:
                # 找價格符號
                price_match = re.search(r'\$([\d,]+)', line_upper)
                if price_match:
                    price = int(price_match.group(1).replace(',', ''))
                    if 1000 < price < 100000:
                        print(f"✅ 抓到報價: {line[:20]} -> {price}")
                        return price
        
        print(f"⚠️ 網頁載入內容不足，沒看到 {keyword} 的價格標籤")
        return None
    except Exception as e:
        print(f"❌ 錯誤: {str(e)}")
        return None

async def main():
    print("🚀 銓展通訊 - 暴力模擬真人爬蟲啟動...")
    config = {k: v for k, v in (json.load(open(CONFIG_FILE, 'r', encoding='utf-8'))).items()}
    prices = json.load(open(OUTPUT_FILE, 'r', encoding='utf-8')) if os.path.exists(OUTPUT_FILE) else {}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        
        for fid, det in config.items():
            price = await fetch_landmark_price(page, det['keyword'], det['capacity'])
            if price:
                if fid not in prices: prices[fid] = {}
                if det['capacity'] not in prices[fid]: prices[fid][det['capacity']] = {}
                prices[fid][det['capacity']]["landmark"] = price
        await browser.close()
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f: json.dump(prices, f, ensure_ascii=False, indent=4)
    print("🎉 任務完成！")

if __name__ == "__main__": asyncio.run(main())
