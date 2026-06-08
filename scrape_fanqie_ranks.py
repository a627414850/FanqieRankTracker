import os
import json
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

START_CODE = 58344  # 0xE3E8
CHAR_SEQUENCE = [
    "D", "在", "主", "特", "家", "军", "然", "表", "场", "4", "要", "只", "v", "和", "?", "6", "别", "还", "g", "现", "儿", "岁", "?", "?", "此", "象", "月", "3", "出", "战", "工", "相", "o", "男", "直", "失", "世", "F", "都", "平", "文", "什", "V", "O", "将", "真", "T", "那", "当", "?", "会", "立", "些", "u", "是", "十", "张", "学", "气", "大", "爱", "两", "命", "全", "后", "东", "性", "通", "被", "1", "它", "乐", "接", "而", "感", "车", "山", "公", "了", "常", "以", "何", "可", "话", "先", "p", "i", "叫", "轻", "M", "士", "w", "着", "变", "尔", "快", "l", "个", "说", "少", "色", "里", "安", "花", "远", "7", "难", "师", "放", "t", "报", "认", "面", "道", "S", "?", "克", "地", "度", "I", "好", "机", "U", "民", "写", "把", "万", "同", "水", "新", "没", "书", "电", "吃", "像", "斯", "5", "为", "y", "白", "几", "日", "教", "看", "但", "第", "加", "候", "作", "上", "拉", "住", "有", "法", "r", "事", "应", "位", "利", "你", "声", "身", "国", "问", "马", "女", "他", "Y", "比", "父", "x", "A", "H", "N", "s", "X", "边", "美", "对", "所", "金", "活", "回", "意", "到", "z", "从", "j", "知", "又", "内", "因", "点", "Q", "三", "定", "8", "R", "b", "正", "或", "夫", "向", "德", "听", "更", "?", "得", "告", "并", "本", "q", "过", "记", "L", "让", "打", "f", "人", "就", "者", "去", "原", "满", "体", "做", "经", "K", "走", "如", "孩", "c", "G", "给", "使", "物", "?", "最", "笑", "部", "?", "员", "等", "受", "k", "行", "一", "条", "果", "动", "光", "门", "头", "见", "往", "自", "解", "成", "处", "天", "能", "于", "名", "其", "发", "总", "母", "的", "死", "手", "入", "路", "进", "心", "来", "h", "时", "力", "多", "开", "已", "许", "d", "至", "由", "很", "界", "n", "小", "与", "Z", "想", "代", "么", "分", "生", "口", "再", "妈", "望", "次", "西", "风", "种", "带", "J", "?", "实", "情", "才", "这", "?", "E", "我", "神", "格", "长", "觉", "间", "年", "眼", "无", "不", "亲", "关", "结", "0", "友", "信", "下", "却", "重", "己", "老", "2", "音", "字", "m", "呢", "明", "之", "前", "高", "P", "B", "目", "太", "e", "9", "起", "稜", "她", "也", "W", "用", "方", "子", "英", "每", "理", "便", "四", "数", "期", "中", "C", "外", "样", "a", "海", "们", "任"
]

def decode_text(text: str) -> str:
    if not text:
        return ""
    result = []
    for char in text:
        code = ord(char)
        idx = code - START_CODE
        if 0 <= idx < len(CHAR_SEQUENCE):
            result.append(CHAR_SEQUENCE[idx])
        else:
            result.append(char)
    return "".join(result)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

def run_scraper(sleep_sec=8, max_retries=3):
    """
    sleep_sec: 每个类目抓完后的防封等待秒数
    max_retries: 遇到网络或点击错误时的最大重试次数
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    output_file = os.path.join(OUTPUT_DIR, f"fanqie_ranks_{date_str}.json")
    state_file = os.path.join(OUTPUT_DIR, f"task_state_{date_str}.json")

    # ------------- 断点续传逻辑 -------------
    completed_cats = []
    all_categories = []

    if os.path.exists(state_file):
        with open(state_file, "r", encoding="utf-8") as f:
            try:
                state = json.load(f)
                completed_cats = state.get("completed", [])
            except:
                pass

    if os.path.exists(output_file) and len(completed_cats) > 0:
        with open(output_file, "r", encoding="utf-8") as f:
            try:
                existing = json.load(f)
                all_categories = existing.get("categories", [])
            except:
                pass

    with sync_playwright() as p:
        # 根据 GitHub Actions 环境变量决定是否使用无头模式
        if os.environ.get("GITHUB_ACTIONS"):
            browser = p.chromium.launch(headless=True)
        else:
            browser = p.chromium.launch(headless=True, channel="chrome")

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # 设置默认超时时间，防止加载慢时直接报错退出
        page.set_default_timeout(15000)

        init_url = "https://fanqienovel.com/rank?enter_from=menu"
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在初始化并访问基础榜单页：{init_url}")

        # 容错1：初始化页面加载重试
        for attempt in range(max_retries):
            try:
                page.goto(init_url, wait_until="networkidle", timeout=30000)
                page.wait_for_selector('a[href^="/page/"]', timeout=15000)
                break
            except Exception as e:
                print(f"⚠️ 初始化页面加载慢或失败，重试 {attempt + 1}/{max_retries}... 错误: {e}")
                if attempt == max_retries - 1:
                    print("❌ 初始化页面彻底失败，程序退出。")
                    browser.close()
                    return
                time.sleep(3)

        # 动态解析所有类目
        categories_js = """() => {
            const links = Array.from(document.querySelectorAll('a'));
            const categories = [];
            const seenHrefs = new Set();
            for (const a of links) {
                const href = a.getAttribute('href') || '';
                const name = a.innerText.trim();
                if (name && /\\/rank\\/\\d+_\\d+_\\d+/.test(href)) {
                    if (!seenHrefs.has(href)) {
                        seenHrefs.add(href);
                        categories.push({ name: name, href: href });
                    }
                }
            }
            return categories;
        }"""

        try:
            categories = page.evaluate(categories_js)
            print(f"✅ 成功提取到 {len(categories)} 个分类标签。开始抓取...")
        except Exception as e:
            print(f"❌ 提取分类失败: {e}")
            browser.close()
            return

        extract_js = """() => {
            const bookMap = new Map();
            const links = document.querySelectorAll('a[href^="/page/"]');
            links.forEach(link => {
                let container = link.parentElement;
                let depth = 0;
                while (container && depth < 6) {
                    if (container.querySelector('img') && container.innerText.includes('在读')) {
                        const href = link.getAttribute('href');
                        if (!bookMap.has(href)) { bookMap.set(href, container); }
                        break;
                    }
                    container = container.parentElement;
                    depth++;
                }
            });

            const cards = Array.from(bookMap.values());
            const results = [];
            for (const item of cards) {
                let imgNode = item.querySelector('img');
                let cover = imgNode ? imgNode.getAttribute('src') : "";
                let title = (imgNode && imgNode.getAttribute('alt')) ? imgNode.getAttribute('alt').trim() : "";
                if (!title) {
                    let textTitleNode = item.querySelector('h4, .title, h1') || item.querySelector('a[href^="/page/"]');
                    if (textTitleNode) {
                        let text = textTitleNode.innerText.trim();
                        if (text && !/^\\d+$/.test(text)) title = text;
                    }
                }
                if (!title || title.includes("榜单说明")) continue;

                let authorNode = item.querySelector('.author, .author-name') || item.querySelector('a[href^="/author-page/"]');
                let author = authorNode ? authorNode.innerText.trim() : "未知";

                let reads = "未知";
                const lines = item.innerText.split('\\n');
                for (let line of lines) { if (line.includes('在读')) { reads = line; break; } }

                let introNode = item.querySelector('.intro, .abstract, .desc');
                let intro = introNode ? introNode.innerText.trim() : "暂无简介";

                results.push({
                    title: title,
                    author: author,
                    reads: reads,
                    intro: intro,
                    cover: cover,
                    url: item.querySelector('a[href^="/page/"]').getAttribute('href')
                });
            }
            return results;
        }"""

        # ------------------- 开始遍历类目 -------------------
        for cat in categories:
            cat_name = cat["name"]
            cat_href = cat["href"]

            if cat_name in completed_cats:
                print(f"⏭️ 跳过今日已完成类别：{cat_name}")
                continue

            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🔄 切换类别 -> {cat_name}")
            try:
                page.locator(f"a[href='{cat_href}']").click()
                # 容错2：点击类目后，智能等待网络空闲和元素出现
                page.wait_for_load_state("networkidle", timeout=15000)
                page.wait_for_selector('a[href^="/page/"]', timeout=10000)
            except Exception as e:
                print(f"⚠️ 切换分类超时或出错 {cat_name}: {e}")
                continue  # 跳过当前类目，继续下一个

            category_books = []
            page_num = 1

            # ------------------- 开始翻页循环 -------------------
            while True:
                print(f"  📖 正在抓取第 {page_num} 页...")

                # 容错3：滚动加载慢的处理
                # 滚动到底部触发懒加载，并等待页面高度不再变化（说明加载完毕）
                last_height = page.evaluate("document.body.scrollHeight")
                for _ in range(3):
                    page.evaluate("window.scrollBy(0, window.innerHeight)")
                    time.sleep(0.5)

                # 智能等待页面数据加载完毕
                try:
                    page.wait_for_function(f"document.body.scrollHeight > {last_height}", timeout=5000)
                except:
                    pass  # 超时说明到底了，或者没新数据加载，继续执行即可

                # 最后再确保网络请求完毕
                try:
                    page.wait_for_load_state("networkidle", timeout=8000)
                except:
                    pass

                # 提取当前页面书籍数据
                try:
                    books_data = page.evaluate(extract_js)
                    if not books_data and page_num == 1:
                        print("  ⚠️ 第一页未提取到数据，可能加载异常。")
                except Exception as e:
                    print(f"  ❌ 第 {page_num} 页提取数据失败: {e}")
                    books_data = []

                # 解码并加入集合
                for b in books_data:
                    t = decode_text(b.get("title", ""))
                    a = decode_text(b.get("author", ""))
                    r_raw = decode_text(b.get("reads", ""))
                    i = decode_text(b.get("intro", "")).replace("\\n", " ")
                    if "在读" in r_raw:
                        parts = r_raw.split("在读")
                        cleaned_r = parts[1].replace(":", "").replace("：", "").strip() if len(parts) > 1 else r_raw
                    else:
                        cleaned_r = r_raw

                    category_books.append({
                        "title": t,
                        "author": a,
                        "reads": cleaned_r,
                        "intro": i,
                        "cover": b.get("cover", ""),
                        "url": "https://fanqienovel.com" + b.get("url", "")
                    })

                # 寻找并点击“下一页”按钮
                try:
                    # 常见的下一页按钮选择器（根据网页实际情况，可能是 button 或 a 标签）
                    next_button = page.locator('button:has-text("下一页"), a:has-text("下一页"), .pagination-next, .next').first
                    if next_button.is_visible() and next_button.is_enabled():
                        next_button.click()
                        page_num += 1
                        # 容错4：点击下一页后，等待新数据出现
                        time.sleep(1)  # 给一点DOM销毁重建的时间
                        page.wait_for_load_state("networkidle", timeout=15000)
                        page.wait_for_selector('a[href^="/page/"]', timeout=10000)
                    else:
                        print("  🔚 没有更多页面，当前类目抓取完毕。")
                        break
                except Exception as e:
                    print(f"  🔚 未找到下一页按钮或已到最后一页: {e}")
                    break

            # ------------------- 单个类目结束，存档 -------------------
            all_categories.append({"name": cat_name, "books": category_books})

            # 实时写入JSON
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({"date": datetime.now().strftime('%Y-%m-%d'), "categories": all_categories}, f, ensure_ascii=False, indent=2)

            completed_cats.append(cat_name)
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump({"completed": completed_cats}, f, ensure_ascii=False)

            print(f"✅ {cat_name} 抓取完成，共 {len(category_books)} 本书。等待 {sleep_sec} 秒防封...")
            time.sleep(sleep_sec)

        browser.close()

    print(f"\n🎉 全部任务完毕！数据源：{output_file}")

if __name__ == "__main__":
    # sleep_sec 设置大一点更安全，比如 8-10 秒
    run_scraper(sleep_sec=8)
    
