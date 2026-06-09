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

def run_scraper(cat_sleep_sec=8, page_sleep_sec=2, max_retries=3):
    """
    cat_sleep_sec:  每个类目之间的防封等待秒数
    page_sleep_sec: 每翻一页（每取20条）的防封等待秒数
    max_retries:    初始化页面加载的最大重试次数
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
                completed_cats = json.load(f).get("completed", [])
            except:
                pass

    if os.path.exists(output_file) and len(completed_cats) > 0:
        with open(output_file, "r", encoding="utf-8") as f:
            try:
                all_categories = json.load(f).get("categories", [])
            except:
                pass

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.set_default_timeout(15000)

        init_url = "https://fanqienovel.com/rank?enter_from=menu"
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在初始化并访问基础榜单页：{init_url}")

        # 容错：初始化页面加载重试
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

        # 提取所有类目
        categories = page.evaluate("""() => {
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
        }""")
        print(f"✅ 成功提取到 {len(categories)} 个分类标签。")

        # =====================================================
        # 核心：JS 函数只负责请求单页（20条），翻页循环由 Python 控制
        # =====================================================
        js_fetch_one_page = """async (params) => {
            try {
                const url = `/api/rank/category/list?limit=20&offset=${params.offset}&gender=${params.gender}&category_id=${params.categoryId}&rank_list_type=${params.rankType}`;
                const res = await fetch(url);
                const data = await res.json();
                if (data.code === 0 && data.data && data.data.book_list) {
                    return { books: data.data.book_list, has_more: data.data.book_list.length === 20 };
                }
                return { books: [], has_more: false };
            } catch (e) {
                return { books: [], has_more: false, error: e.toString() };
            }
        }"""

        # ------------------- 开始遍历类目 -------------------
        for cat in categories:
            cat_name = cat["name"]
            cat_href = cat["href"]

            if cat_name in completed_cats:
                print(f"⏭️ 跳过今日已完成类别：{cat_name}")
                continue

            # 解析 URL 中的参数：/rank/type_gender_category
            try:
                parts = cat_href.split("/")[2].split("_")
                rank_type = parts[0]
                gender = parts[1]
                category_id = parts[2]
            except Exception as e:
                print(f"⚠️ 解析类目参数失败 {cat_name}: {e}，跳过。")
                continue

            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🚀 正在通过 API 抓取类目 -> {cat_name}")

            category_books = []
            offset = 0
            page_num = 1
            # ------------------- Python 端控制翻页循环 -------------------
            while True:
                print(f"  📖 第 {page_num} 页 (offset={offset})...")

                try:
                    result = page.evaluate(js_fetch_one_page, {
                        "offset": offset,
                        "gender": gender,
                        "categoryId": category_id,
                        "rankType": rank_type
                    })
                except Exception as e:
                    print(f"  ❌ API 请求失败: {e}")
                    break

                books_data = result.get("books", [])
                has_more = result.get("has_more", False)
                error = result.get("error")

                if error:
                    print(f"  ❌ API 返回错误: {error}")
                    break

                if not books_data:
                    print(f"  🔚 本页无数据，{cat_name} 类目抓取完毕。")
                    break

                # 解码并加入集合
                for b in books_data:
                    t = decode_text(b.get("book_name", "") or b.get("title", ""))
                    a = decode_text(b.get("author", "") or b.get("author_name", ""))
                    r_raw = str(b.get("read_count", "未知"))
                    i = decode_text(b.get("abstract", "") or b.get("intro", ""))
                    book_id = b.get("book_id", "")

                    category_books.append({
                        "title": t,
                        "author": a,
                        "reads": r_raw,
                        "intro": i.replace("\\n", " "),
                        "cover": f"https://p3-novel.byteimg.com/origin/{b.get('cover', '')}",
                        "url": f"https://fanqienovel.com/page/{book_id}" if book_id else ""
                    })

                print(f"  ✅ 本页获取 {len(books_data)} 条，累计 {len(category_books)} 条。")

                # 判断是否还有下一页
                if not has_more:
                    print(f"  🔚 已无更多数据，{cat_name} 类目抓取完毕。")
                    break

                # ⭐ 关键：每取完一页（20条），sleep 一下防封！
                offset += 20
                page_num += 1
                print(f"  💤 翻页防封等待 {page_sleep_sec} 秒...")
                time.sleep(page_sleep_sec)

            # ------------------- 单个类目结束，存档 -------------------
            all_categories.append({"name": cat_name, "books": category_books})

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({"date": datetime.now().strftime('%Y-%m-%d'), "categories": all_categories}, f, ensure_ascii=False, indent=2)

            completed_cats.append(cat_name)
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump({"completed": completed_cats}, f, ensure_ascii=False)

            print(f"✅ {cat_name} 抓取完成，共 {len(category_books)} 本书。等待 {cat_sleep_sec} 秒防封...")
            time.sleep(cat_sleep_sec)

        browser.close()

    print(f"\n🎉 全部任务完毕！数据源：{output_file}")


if __name__ == "__main__":
    run_scraper(cat_sleep_sec=8, page_sleep_sec=2)
