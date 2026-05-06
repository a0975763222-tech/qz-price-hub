import json
import asyncio
import random
import os
import re
from datetime import datetime
from playwright.async_api import async_playwright

# ==========================================
# 銓展通訊 - 最強自動爬蟲大腦 (v5.0 終極版)
# ==========================================

# 防封鎖 User-Agent 池 (多種瀏覽器與系統偽裝)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15"
]

# --- 輔助工具函數 ---
def clean_price(price_str):
    """清洗價格字串，過濾所有中英文字與符號，轉為純數字"""
    if not price_str:
        return 0
    cleaned = re.sub(r'[^\d]', '', str(price_str))
    return int(cleaned) if cleaned else 0

def is_valid_price(price):
    """【老闆指定防呆】異常排除：過濾 0 元、1元或 999,999 等無效佔位價格"""
    if price <= 1 or price >= 999999:
        return False
    return True

def build_regex(text):
    """【強大模糊匹配】允許字詞間有任意特殊符號 (如空白、括號、減號等)"""
    words = text.split()
    return r".*?".join(re.escape(word) for word in words)

async def random_delay():
    """【防封鎖】隨機延遲 3.5 ~ 7.5 秒，模擬真人行為"""
    delay = random.uniform(3.5, 7.5)
    print(f"⏳ 擬真延遲 {delay:.1f} 秒...")
    await asyncio.sleep(delay)

# --- 主爬蟲引擎 ---
async def fetch_prices():
    print("=============================================")
    print(f"🤖 銓展通訊爬蟲系統啟動 | 時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=============================================")

    # 1. 讀取外部設定檔 config.json
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            MAPPING = json.load(f)
        print(f"📂 成功載入 config.json，共追蹤 {len(MAPPING)} 款設備")
    except Exception as e:
        print(f"❌ 讀取 config.json 失敗，請確認檔案是否存在: {e}")
        return

    # 2. 讀取舊有價格檔 (備用繼承機制，若抓取失敗則沿用舊價)
    old_data = {}
    if os.path.exists('prices.json'):
        try:
            with open('prices.json', 'r', encoding='utf-8') as f:
                old_data = json.load(f)
            print("💾 成功載入舊有 prices.json，啟動異常防護網")
        except Exception as e:
            print(f"⚠️ 讀取舊價格檔失敗，將建立全新資料: {e}")

    # 3. 建立準備輸出至前端的結果字典
    results = {}
    for uid, info in MAPPING.items():
        cap = info["capacity"]
        if uid not in results:
            results[uid] = {}
        # 初始化預設值
        results[uid][cap] = {"landmark": 0, "jasons": 0, "sogi": 0}
        
        # 【繼承機制】先把舊價格塞入打底，萬一爬失敗，至少保有昨日價格
        if uid in old_data and cap in old_data[uid]:
            results[uid][cap]["landmark"] = old_data[uid][cap].get("landmark", 0)
            results[uid][cap]["jasons"] = old_data[uid][cap].get("jasons", 0)
            results[uid][cap]["sogi"] = old_data[uid][cap].get("sogi", 0)

    # 4. 啟動 Playwright 無頭瀏覽器
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ua = random.choice(USER_AGENTS)
        context = await browser.new_context(
            user_agent=ua,
            viewport={'width': random.randint(1366, 1920), 'height': random.randint(768, 1080)}
        )
        page = await context.new_page()
        
        # 攔截不必要的資源(如字體、無用媒體)，加快加載速度與減少被擋機率
        await page.route("**/*", lambda route: route.continue_() if route.request.resource_type in ["document", "script", "xhr", "fetch"] else route.abort())

        print(f"🚀 瀏覽器引擎就緒 (User-Agent: {ua[:40]}...)")

        # ---------------------------------------------------------
        # [站點 1] 地標網通 (Landmark)
        # ---------------------------------------------------------
        try:
            print("\n👉 正在前往【地標網通】...")
            await page.goto("https://www.landtop.com.tw/products", timeout=60000)
            await page.wait_for_load_state("networkidle") # 【WaitState 確保加載】
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)") # 【向下捲動防懶加載】
            await random_delay()

            success_count = 0
            for uid, info in MAPPING.items():
                name, cap = info["name"], info["capacity"]
                name_regex, cap_regex = build_regex(name), build_regex(cap)
                
                elements = await page.locator(f"text={name}").all()
                for el in elements:
                    text_content = await el.text_content()
                    if re.search(name_regex, text_content, re.IGNORECASE) and re.search(cap_regex, text_content, re.IGNORECASE):
                        price_text = await el.locator("xpath=ancestor::div[contains(@class, 'product')]//span[contains(@class, 'price')]").first.text_content()
                        
                        parsed_price = clean_price(price_text)
                        if is_valid_price(parsed_price):
                            results[uid][cap]["landmark"] = parsed_price
                            print(f"✅ 地標: {name} {cap} -> ${parsed_price}")
                            success_count += 1
                        break
            
            # 【自動 Debug 截圖】
            if success_count < len(MAPPING):
                await page.screenshot(path="error_landmark.png", full_page=True)
                print("⚠️ 地標有缺漏，已儲存 error_landmark.png")
                
        except Exception as e:
            print(f"❌ 地標發生嚴重錯誤: {e}")
            await page.screenshot(path="error_landmark_crash.png")

        # ---------------------------------------------------------
        # [站點 2] 傑昇通信 (Jyes)
        # ---------------------------------------------------------
        try:
            print("\n👉 正在前往【傑昇通信】...")
            await page.goto("https://www.jyes.com.tw/product.php", timeout=60000)
            await page.wait_for_load_state("networkidle")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await random_delay()

            success_count = 0
            for uid, info in MAPPING.items():
                name, cap = info["name"], info["capacity"]
                name_regex, cap_regex = build_regex(name), build_regex(cap)
                
                elements = await page.locator(f"text={name}").all()
                for el in elements:
                    text_content = await el.text_content()
                    if re.search(name_regex, text_content, re.IGNORECASE) and re.search(cap_regex, text_content, re.IGNORECASE):
                        price_text = await el.locator("xpath=ancestor::div[contains(@class, 'item')]//div[contains(text(), '最低價')]/following-sibling::div").first.text_content()
                        
                        parsed_price = clean_price(price_text)
                        if is_valid_price(parsed_price):
                            results[uid][cap]["jasons"] = parsed_price
                            print(f"✅ 傑昇: {name} {cap} -> ${parsed_price}")
                            success_count += 1
                        break
                        
            if success_count < len(MAPPING):
                await page.screenshot(path="error_jasons.png", full_page=True)
                print("⚠️ 傑昇有缺漏，已儲存 error_jasons.png")
                
        except Exception as e:
            print(f"❌ 傑昇發生嚴重錯誤: {e}")
            await page.screenshot(path="error_jasons_crash.png")

        # ---------------------------------------------------------
        # [站點 3] 手機王 (SOGI)
        # ---------------------------------------------------------
        try:
            print("\n👉 正在前往【手機王】...")
            await page.goto("https://www.sogi.com.tw/prices", timeout=60000)
            await page.wait_for_load_state("networkidle")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await random_delay()

            success_count = 0
            for uid, info in MAPPING.items():
                name, cap = info["name"], info["capacity"]
                name_regex, cap_regex = build_regex(name), build_regex(cap)
                
                elements = await page.locator(f"text={name}").all()
                for el in elements:
                    text_content = await el.text_content()
                    if re.search(name_regex, text_content, re.IGNORECASE) and re.search(cap_regex, text_content, re.IGNORECASE):
                        price_text = await el.locator("xpath=ancestor::li//span[contains(@class, 'price')]").first.text_content()
                        
                        parsed_price = clean_price(price_text)
                        if is_valid_price(parsed_price):
                            results[uid][cap]["sogi"] = parsed_price
                            print(f"✅ 手機王: {name} {cap} -> ${parsed_price}")
                            success_count += 1
                        break
                        
            if success_count < len(MAPPING):
                await page.screenshot(path="error_sogi.png", full_page=True)
                print("⚠️ 手機王有缺漏，已儲存 error_sogi.png")
                
        except Exception as e:
            print(f"❌ 手機王發生嚴重錯誤: {e}")
            await page.screenshot(path="error_sogi_crash.png")

        await browser.close()
        print("\n🎉 爬蟲掃描結束，準備更新資料庫。")

    # 5. 寫入最終的 prices.json (完全對接老闆的 React 戰情室)
    with open('prices.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
        
    print(f"💾 成功儲存最新報價至 prices.json！ | 完成時間：{datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(fetch_prices())
