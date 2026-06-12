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

def run_scraper(limit=30, sleep_sec=5):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    output_file = os.path.join(OUTPUT_DIR, f"fanqie_new_ranks_{date_str}.json")
    state_file = os.path.join(OUTPUT_DIR, f"task_state_{date_str}.json")

    # ------------- 状态恢复逻辑 -------------
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
    # ----------------------------------------

    with sync_playwright() as p:
        if os.environ.get("GITHUB_ACTIONS"):
            browser = p.chromium.launch(headless=True)
        else:
            browser = p.chromium.launch(headless=True, channel="chrome")

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # 提取分类用的 JS
        categories_js = """
        () => {
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
        }
        """

        # ===== 第一步：访问初始页面，提取女频分类 =====
        init_url = "https://fanqienovel.com/rank?enter_from=menu"
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在初始化并访问基础榜单页：{init_url}")
        page.goto(init_url, wait_until="load", timeout=15000)
        page.wait_for_selector('a[href^="/page/"]', timeout=5000)

        female_categories = page.evaluate(categories_js)
        for cat in female_categories:
            cat["channel"] = "女频"
        print(f"✅ 提取到女频 {len(female_categories)} 个分类标签。")

        # ===== 第二步：从女频URL推算男频URL，直接导航提取 =====
        # URL规则：/rank/X_Y_Z 中 X=0 是女频，X=1 是男频
        male_categories = []
        try:
            # 取女频第一个分类，把 X 从 0 改成 1，就是男频的对应页面
            if female_categories:
                first_female_href = female_categories[0]["href"]
                # /rank/0_1_1139 -> /rank/1_1_1139
                male_entry_href = "/rank/1" + first_female_href[first_female_href.index("_"):]
                male_entry_url = "https://fanqienovel.com" + male_entry_href

                print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在导航到男频页面：{male_entry_url}")
                page.goto(male_entry_url, wait_until="load", timeout=15000)
                page.wait_for_selector('a[href^="/page/"]', timeout=5000)

                male_categories = page.evaluate(categories_js)
                for cat in male_categories:
                    cat["channel"] = "男频"
                print(f"✅ 提取到男频 {len(male_categories)} 个分类标签。")
            else:
                print("⚠️ 未提取到女频分类，无法推算男频URL。")
        except Exception as e:
            print(f"⚠️ 导航到男频失败: {e}")

        # ===== 第三步：合并所有分类 =====
        all_channel_categories = female_categories + male_categories
        print(f"✅ 共提取到 {len(all_channel_categories)} 个分类标签（女频 {len(female_categories)} + 男频 {len(male_categories)}）。开始全量抓取...")

        # ===== 第四步：逐个导航到分类URL并抓取 =====
        for cat in all_channel_categories:
            cat_name = cat["name"]
            cat_channel = cat.get("channel", "")
            cat_full_name = f"{cat_channel}-{cat_name}" if cat_channel else cat_name
            cat_href = cat["href"]

            if cat_full_name in completed_cats:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏭️ 跳过今日已经完成抓取的类别：{cat_full_name}")
                continue

            print(f"[{datetime.now().strftime('%H:%M:%S')}] 模拟导航到分类 -> {cat_full_name}")

            try:
                cat_url = "https://fanqienovel.com" + cat_href
                page.goto(cat_url, wait_until="load", timeout=15000)
                page.wait_for_selector('a[href^="/page/"]', timeout=5000)
            except Exception as e:
                print(f"导航到分类出错或加载超时 {cat_full_name}: {e}")

            # 滚动加载：固定8次，每次1.5屏，等待3秒
            for _ in range(8):
                page.evaluate("window.scrollBy(0, window.innerHeight * 1.5)")
                time.sleep(3)
            # 提取数据
            extract_js = """
            () => {
                const bookMap = new Map();
                const links = document.querySelectorAll('a[href^="/page/"]');
                links.forEach(link => {
                    let container = link.parentElement;
                    let depth = 0;
                    while (container && depth < 6) {
                        if (container.querySelector('img') && container.innerText.includes('在读')) {
                            const href = link.getAttribute('href');
                            if (!bookMap.has(href)) {
                                bookMap.set(href, container);
                            }
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
                    let title = "";
                    if (imgNode && imgNode.getAttribute('alt')) {
                        title = imgNode.getAttribute('alt').trim();
                    }
                    if (!title) {
                        let textTitleNode = item.querySelector('h4, .title, h1') || item.querySelector('a[href^="/page/"]');
                        if (textTitleNode) {
                            let text = textTitleNode.innerText.trim();
                            if (text && !/^\\d+$/.test(text)) {
                                title = text;
                            }
                        }
                    }
                    if (!title) title = "未知";
                    if (title.includes("榜单说明")) continue;

                    let authorNode = item.querySelector('.author, .author-name') || item.querySelector('a[href^="/author-page/"]');
                    let author = authorNode ? authorNode.innerText.trim() : "未知";

                    let reads = "未知";
                    const lines = item.innerText.split('\\n');
                    for (let line of lines) {
                        if (line.includes('在读')) {
                            reads = line;
                            break;
                        }
                    }

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
            }
            """
            try:
                books_data = page.evaluate(extract_js)
            except Exception as e:
                print(f"执行JS抽取失败 {cat_full_name}: {e}")
                books_data = []

            category_books = []
            for b in books_data[:limit]:
                t = decode_text(b.get("title", ""))
                a = decode_text(b.get("author", ""))
                r_raw = decode_text(b.get("reads", ""))
                i = decode_text(b.get("intro", "")).replace("\\n", " ")
                c = b.get("cover", "")

                if "在读" in r_raw:
                    parts = r_raw.split("在读")
                    if len(parts) > 1:
                        cleaned_r = parts[1].replace(":", "").replace("：", "").strip()
                    else:
                        cleaned_r = r_raw
                else:
                    cleaned_r = r_raw

                category_books.append({
                    "title": t,
                    "author": a,
                    "reads": cleaned_r,
                    "intro": i,
                    "cover": c,
                    "url": "https://fanqienovel.com" + b.get("url", "")
                })

            all_categories.append({
                "name": cat_full_name,
                "channel": cat_channel,
                "books": category_books
            })

            snapshot = {
                "date": datetime.now().strftime('%Y-%m-%d'),
                "categories": all_categories
            }
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(snapshot, f, ensure_ascii=False, indent=2)

            completed_cats.append(cat_full_name)
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump({"completed": completed_cats}, f, ensure_ascii=False)

            print(f"成功抓取 {cat_full_name} 类别的前 {len(category_books)} 本书，且进度已存档。等待 {sleep_sec} 秒防拦截...")

            time.sleep(sleep_sec)

        browser.close()

    print(f"\n✅ 当日选定类目任务已完毕或刷新！数据源：{output_file}")

if __name__ == "__main__":
    print("开始执行番茄新书榜抓取计划...")
    run_scraper(limit=30, sleep_sec=5)

