#!/usr/bin/env python3
"""
公司信息补全：评分（Glassdoor）、类型（规则+Google）、行业（API 映射）。

用法:
    python3 enrich_company.py --input /tmp/jobs_with_jd.json --output /tmp/jobs_enriched.json

策略:
    1. 收集所有唯一公司名
    2. 评分: Google 搜索 "{公司名} glassdoor rating"，从摘要提取评分
    3. 类型: 规则层 → Google 搜索 "{公司名} 总部" 提取国家 → "待确认"
    4. 行业: API subclassification → 中文映射表
"""

import argparse
import json
import re
import sys
import time
import subprocess
import urllib.parse

# ── 公司类型预置映射表 ─────────────────────────────────────────────────────
COMPANY_TYPE_MAP = {
    # 日本外企
    "sony": "日本外企",
    "shiseido": "日本外企",
    "nissin foods": "日本外企",
    "muji": "日本外企",
    "uniqlo": "日本外企",
    "fast retailing": "日本外企",
    "panasonic": "日本外企",
    "hitachi": "日本外企",
    "canon": "日本外企",
    "daiwa": "日本外企",
    "mitsubishi": "日本外企",
    "mitsui": "日本外企",
    "sumitomo": "日本外企",
    "ito en": "日本外企",
    "asahi": "日本外企",
    "kirin": "日本外企",
    "suntory": "日本外企",
    "kose": "日本外企",
    "kanebo": "日本外企",
    "sk-ii": "日本外企",
    "daiichi sankyo": "日本外企",
    "takeda": "日本外企",
    "otsuka": "日本外企",
    "eisai": "日本外企",
    "astellas": "日本外企",
    # 法国外企
    "axa": "法国外企",
    "pierre fabre": "法国外企",
    "l'oreal": "法国外企",
    "loreal": "法国外企",
    "l'oréal": "法国外企",
    "chanel": "法国外企",
    "hermes": "法国外企",
    "hermès": "法国外企",
    "lvmh": "法国外企",
    "dior": "法国外企",
    "givenchy": "法国外企",
    "clarins": "法国外企",
    "sisley": "法国外企",
    "guerlain": "法国外企",
    "bioderma": "法国外企",
    "la roche-posay": "法国外企",
    "vichy": "法国外企",
    "saint laurent": "法国外企",
    "cartier": "法国外企",
    "richemont": "法国外企",
    "lpm": "法国外企",
    "chantecaille": "法国外企",
    "total": "法国外企",
    "danone": "法国外企",
    "deca": "法国外企",
    # 英国外企
    "christie": "英国外企",
    "hsbc": "英国外企",
    "standard chartered": "英国外企",
    "bp": "英国外企",
    "shell": "英国外企",
    "unilever": "英国外企",
    "diageo": "英国外企",
    "vodafone": "英国外企",
    "glaxo": "英国外企",
    "gsk": "英国外企",
    "astrazeneca": "英国外企",
    "burberry": "英国外企",
    "jaguar": "英国外企",
    "land rover": "英国外企",
    "dyson": "英国外企",
    # 美国外企
    "apple": "美国外企",
    "google": "美国外企",
    "microsoft": "美国外企",
    "meta": "美国外企",
    "amazon": "美国外企",
    "mcdonald": "美国外企",
    "starbucks": "美国外企",
    "nike": "美国外企",
    "coca-cola": "美国外企",
    "pepsi": "美国外企",
    "p&g": "美国外企",
    "johnson & johnson": "美国外企",
    "pfizer": "美国外企",
    "merck": "美国外企",
    "eli lilly": "美国外企",
    "intel": "美国外企",
    "ibm": "美国外企",
    "oracle": "美国外企",
    "salesforce": "美国外企",
    "uber": "美国外企",
    "airbnb": "美国外企",
    "netflix": "美国外企",
    "disney": "美国外企",
    "citibank": "美国外企",
    "citi group": "美国外企",
    "citi venture": "美国外企",
    "jpmorgan": "美国外企",
    "goldman sachs": "美国外企",
    "morgan stanley": "美国外企",
    "bank of america": "美国外企",
    "wells fargo": "美国外企",
    "equinix": "美国外企",
    # 德国外企
    "siemens": "德国外企",
    "bosch": "德国外企",
    "bmw": "德国外企",
    "mercedes": "德国外企",
    "volkswagen": "德国外企",
    "audi": "德国外企",
    "porsche": "德国外企",
    "adidas": "德国外企",
    "puma": "德国外企",
    "sap": "德国外企",
    "bayer": "德国外企",
    "basf": "德国外企",
    "allianz": "德国外企",
    "deutsche": "德国外企",
    "henkel": "德国外企",
    # 瑞士外企
    "nestle": "瑞士外企",
    "nestlé": "瑞士外企",
    "roche": "瑞士外企",
    "novartis": "瑞士外企",
    "ubs": "瑞士外企",
    "credit suisse": "瑞士外企",
    "swatch": "瑞士外企",
    "rolex": "瑞士外企",
    "abb": "瑞士外企",
    # 丹麦外企
    "iss global": "丹麦外企",
    "maersk": "丹麦外企",
    "novo nordisk": "丹麦外企",
    "lego": "丹麦外企",
    # 瑞典外企
    "ikea": "瑞典外企",
    "ericsson": "瑞典外企",
    "volvo": "瑞典外企",
    "h&m": "瑞典外企",
    "electrolux": "瑞典外企",
    # 香港品牌/本地企业
    "cafe de coral": "港资",
    "maxim": "港资",
    "hkbn": "港资",
    "pccw": "港资",
    "hkt": "港资",
    "csl": "港资",
    "hutchison": "港资",
    "swire": "港资",
    "jardine": "港资",
    "li & fung": "港资",
    "chow tai fook": "港资",
    "hang lung": "港资",
    "new world": "港资",
    "sun hung kai": "港资",
    "hysan": "港资",
    "link reit": "港资",
    "mtr": "港资",
    "clp": "港资",
    "towngas": "港资",
    "cathay pacific": "港资",
    # 香港外企（在港运营的外资公司特定品牌）
    "rights & brands": "香港外企",
    "nissin foods (h.k.)": "香港外企",
    # 中资/香港中资
    "citic": "中资",
    "huawei": "中资",
    "xiaomi": "中资",
    "oppo": "中资",
    "vivo": "中资",
    "tencent": "中资",
    "alibaba": "中资",
    "baidu": "中资",
    "byd": "中资",
    "lenovo": "中资",
    "zte": "中资",
    "china mobile": "中资",
    "china telecom": "中资",
    "china unicom": "中资",
    "bank of china": "中资",
    "icbc": "中资",
    "china construction bank": "中资",
    "agricultural bank of china": "中资",
    "ping an": "中资",
    "china life": "中资",
    "china resources": "中资",
    "china merchants": "中资",
    "cosco": "中资",
    "sinopec": "中资",
    "petrochina": "中资",
    "cnpc": "中资",
    "state grid": "中资",
    "chagee": "中资",
    # NGO/非营利
    "save the children": "外资NGO",
    "wwf": "外资NGO",
    "oxfam": "外资NGO",
    "unicef": "外资NGO",
    "greenpeace": "外资NGO",
    "red cross": "外资NGO",
    "habitat for humanity": "外资NGO",
    # 新加坡
    "dbs": "新加坡外企",
    "ocbc": "新加坡外企",
    "uob": "新加坡外企",
    "singtel": "新加坡外企",
    "capitaland": "新加坡外企",
    "grab": "新加坡外企",
    "shopee": "新加坡外企",
    "sea limited": "新加坡外企",
    # 韩国
    "samsung": "韩国外企",
    "lg": "韩国外企",
    "hyundai": "韩国外企",
    "kia": "韩国外企",
    # 台湾
    "tsmc": "台湾外企",
    "foxconn": "台湾外企",
    "asus": "台湾外企",
    "acer": "台湾外企",
    "htc": "台湾外企",
    "mediatek": "台湾外企",
    "evergreen": "台湾外企",
}

# ── 法律后缀 → 可能国家 ───────────────────────────────────────────────────
SUFFIX_HINTS = {
    "株式会社": "日本",
    "co., ltd.": "中国/日本/韩国",  # 模糊，需进一步判断
    "co. ltd.": "中国",
    "limited": "香港",  # Limited 是香港标配，不一定是英国
    "(h.k.) limited": "香港",
    "(hong kong) limited": "香港",
    "ltd": "香港",
    "inc.": "美国",
    "inc": "美国",
    "corp.": "美国",
    "corporation": "美国",
    "llc": "美国",
    "plc": "英国",  # PLC 才是英国特有
    "gmbh": "德国",
    "s.a.": "法国/瑞士",
    "s.a.s.": "法国",
    "sas": "法国",
    "s.p.a.": "意大利",
    "s.r.l.": "意大利",
    "pte ltd": "新加坡",
    "pte. ltd.": "新加坡",
    "b.v.": "荷兰",
    "n.v.": "荷兰/比利时",
    "ab": "瑞典",
    "a/s": "丹麦",
    "oy": "芬兰",
    "k.k.": "日本",
}

# ── 行业 subclassification → 中文映射 ──────────────────────────────────────
INDUSTRY_MAP = {
    "marketing communications": "市场营销",
    "marketing & communications": "市场营销",
    "digital marketing": "数字营销",
    "digital & search marketing": "数字营销",
    "brand management": "品牌管理",
    "brand marketing": "品牌管理",
    "trade marketing": "渠道营销",
    "channel marketing": "渠道营销",
    "public relations": "公关/传讯",
    "public relations & corporate affairs": "公关/传讯",
    "corporate communications": "企业传讯",
    "internal communications": "内部传讯",
    "market research & analysis": "市场调研",
    "market research": "市场调研",
    "event management": "活动/会展",
    "event marketing": "活动/会展",
    "events & exhibitions": "活动/会展",
    "direct marketing & crm": "直销/CRM",
    "crm marketing": "CRM",
    "product marketing": "产品营销",
    "product management & development": "产品管理",
    "marketing communications (other)": "市场营销",
    "marketing (other)": "市场营销",
    "marketing assistants/coordinators": "市场营销",
    "management": "管理",
    "general management": "综合管理",
    "sales": "销售",
    "business development": "业务拓展",
    "account management": "客户管理",
    "consulting": "咨询",
    "strategy & planning": "战略规划",
    "advertising": "广告",
    "media planning & buying": "媒介策划",
    "creative & design": "创意/设计",
    "content marketing": "内容营销",
    "social media marketing": "社交媒体",
    "e-commerce marketing": "电商营销",
    "e-commerce": "电商",
    "retail": "零售",
    "retail & consumer products": "零售/消费品",
    "fmcg": "快消",
    "fast moving consumer goods": "快消",
    "food & beverage": "餐饮",
    "hospitality": "酒店/旅游",
    "tourism": "旅游",
    "beauty & cosmetics": "美妆",
    "cosmetics": "美妆",
    "fashion": "服装/零售",
    "luxury": "奢侈品",
    "automotive": "汽车",
    "automobile": "汽车",
    "information technology": "IT",
    "it": "IT",
    "technology": "科技",
    "telecommunications": "通信",
    "telecom": "通信",
    "financial services": "金融服务",
    "banking": "银行",
    "insurance": "保险",
    "real estate": "房地产",
    "property": "房地产",
    "construction": "建筑",
    "engineering": "工程",
    "manufacturing": "制造",
    "logistics": "物流",
    "supply chain": "供应链",
    "transport": "运输",
    "education": "教育",
    "education & training": "教育/培训",
    "healthcare": "医疗",
    "pharmaceutical": "制药",
    "pharmaceuticals": "制药",
    "medical": "医疗",
    "biotechnology": "生物科技",
    "chemical": "化工",
    "energy": "能源",
    "environmental": "环保",
    "legal": "法律",
    "legal services": "法律",
    "human resources": "人力资源",
    "hr": "人力资源",
    "recruitment": "招聘",
    "admin": "行政",
    "administration": "行政",
    "accounting": "会计",
    "audit": "审计",
    "finance": "财务",
    "media": "媒体",
    "entertainment": "娱乐",
    "publishing": "出版",
    "printing": "印刷",
    "arts": "艺术",
    "design": "设计",
    "architecture": "建筑设计",
    "government": "政府",
    "public sector": "公共部门",
    "non-profit": "非营利",
    "ngo": "非营利",
    "sports": "体育",
    "gaming": "游戏",
    "electronics": "电子",
    "electrical": "电气",
    "automation": "自动化",
    "aviation": "航空",
    "maritime": "航运",
    "agriculture": "农业",
    "food": "食品",
    "food science": "食品",
    "quality assurance": "质量保证",
    "safety": "安全",
    "security": "安全",
    "customer service": "客服",
    "call centre": "呼叫中心",
    "translation": "翻译",
    "writing & editing": "写作/编辑",
    "journalism": "新闻",
    "photography": "摄影",
    "video": "视频",
    "audio": "音频",
    "performing arts": "表演艺术",
    "social services": "社会服务",
    "community services": "社区服务",
    "religious": "宗教",
    "other": "其他",
}


def google_search(query: str, retries: int = 2) -> str:
    """使用 curl 进行 Google 搜索，返回搜索结果页 HTML/文本。"""
    encoded = urllib.parse.quote(query)
    url = f"https://www.google.com/search?q={encoded}&hl=zh-CN&num=10"

    for attempt in range(retries):
        cmd = [
            "curl", "-s", "-L",
            "--max-time", "15",
            "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "-H", "Accept-Language: zh-CN,zh;q=0.9,en;q=0.8",
            url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        stdout = result.stdout.strip()
        if stdout and len(stdout) > 500:
            return stdout
        if attempt < retries - 1:
            time.sleep(3)
    return result.stdout.strip()


def extract_glassdoor_rating(html: str, company: str) -> str:
    """从 Google 搜索结果中提取 Glassdoor 评分。

    在搜索结果摘要中寻找类似 "Rating: 3.8/5" 或 "3.8 ★" 的模式。
    """
    # 确保我们只看搜索结果区域
    # 方法1: 搜索 "glassdoor" 附近的小数
    glassdoor_section = re.findall(
        r'glassdoor[^<]{0,200}(\d\.\d{1,2})',
        html, re.IGNORECASE
    )
    if glassdoor_section:
        # 找最像评分的数字 (1.0-5.0)
        for match in glassdoor_section:
            try:
                val = float(match)
                if 1.0 <= val <= 5.0:
                    return str(val)
            except ValueError:
                continue

    # 方法2: 搜索 star/rating 关键词附近的数字
    rating_patterns = re.findall(
        r'(?:rating|reviews?|score|stars?)[^<]{0,100}?(\d\.\d{1,2})',
        html, re.IGNORECASE
    )
    for match in rating_patterns:
        try:
            val = float(match)
            if 1.0 <= val <= 5.0:
                return str(val)
        except ValueError:
            continue

    # 方法3: 搜索 ★ 符号附近的数字
    star_rating = re.findall(r'(\d\.\d{1,2})\s*(?:★|☆|star)', html)
    for match in star_rating:
        try:
            val = float(match)
            if 1.0 <= val <= 5.0:
                return str(val)
        except ValueError:
            continue

    # 方法4: 搜索评分数字在 company 名附近
    company_short = re.escape(company[:15])
    near_company = re.findall(
        rf'{company_short}[^<]{{0,300}}?(\d\.\d)',
        html, re.IGNORECASE
    )
    for match in near_company:
        try:
            val = float(match)
            if 2.0 <= val <= 5.0:  # 更保守的范围
                return str(val)
        except ValueError:
            continue

    return ""


def extract_headquarters_country(html: str, company: str) -> str:
    """从 Google 搜索结果摘要中提取公司总部国家。

    搜索 "{公司名} 总部" 或 "{公司名} headquarters"，
    从摘要中找国家/地区关键词。
    """
    # 从 HTML 中提取文本片段（去除标签）
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text)

    # 香港相关
    hk_keywords = [
        "香港", "hong kong", "kowloon", "新界", "港岛",
        "headquartered in hong kong", "总部位于香港",
        "香港总部", "hong kong-based", "hong kong based",
    ]
    for kw in hk_keywords:
        if kw.lower() in text.lower():
            return "香港"

    # 中国内地
    cn_keywords = [
        "中国大陆", "总部位于中国", "中国总部", "总部设在",
        "深圳", "上海", "北京", "广州", "杭州",
        "headquartered in china", "china-based",
        "headquartered in beijing", "headquartered in shanghai",
        "headquartered in shenzhen", "headquartered in guangzhou",
        "总部位于深圳", "总部位于上海", "总部位于北京",
    ]
    for kw in cn_keywords:
        if kw.lower() in text.lower():
            return "中国内地"

    # 日本
    jp_keywords = [
        "日本", "东京", "japan", "tokyo", "osaka",
        "headquartered in japan", "japanese",
    ]
    for kw in jp_keywords:
        if kw.lower() in text.lower():
            return "日本"

    # 法国
    fr_keywords = [
        "法国", "巴黎", "france", "paris",
        "headquartered in france", "french",
    ]
    for kw in fr_keywords:
        if kw.lower() in text.lower():
            return "法国"

    # 英国
    uk_keywords = [
        "英国", "伦敦", "united kingdom", "london", "england",
        "headquartered in the uk", "british",
        "headquartered in london",
    ]
    for kw in uk_keywords:
        if kw.lower() in text.lower():
            return "英国"

    # 美国
    us_keywords = [
        "美国", "usa", "united states", "new york", "california",
        "san francisco", "los angeles", "seattle", "chicago",
        "headquartered in the us", "american",
        "headquartered in the united states",
    ]
    for kw in us_keywords:
        if kw.lower() in text.lower():
            return "美国"

    # 德国
    de_keywords = [
        "德国", "germany", "berlin", "munich", "frankfurt",
        "headquartered in germany", "german",
    ]
    for kw in de_keywords:
        if kw.lower() in text.lower():
            return "德国"

    # 新加坡
    sg_keywords = [
        "新加坡", "singapore",
        "headquartered in singapore",
    ]
    for kw in sg_keywords:
        if kw.lower() in text.lower():
            return "新加坡"

    # 瑞士
    ch_keywords = [
        "瑞士", "switzerland", "zurich", "geneva",
        "headquartered in switzerland", "swiss",
    ]
    for kw in ch_keywords:
        if kw.lower() in text.lower():
            return "瑞士"

    # 韩国
    kr_keywords = [
        "韩国", "首尔", "korea", "seoul",
        "headquartered in korea", "korean",
    ]
    for kw in kr_keywords:
        if kw.lower() in text.lower():
            return "韩国"

    # 台湾
    tw_keywords = [
        "台湾", "台北", "taiwan", "taipei",
        "headquartered in taiwan", "taiwanese",
    ]
    for kw in tw_keywords:
        if kw.lower() in text.lower():
            return "台湾"

    return ""


def classify_company_type(company: str, country_from_search: str = "") -> str:
    """综合判断公司类型。

    优先级:
    1. 预置映射表（精确匹配）
    2. Google 搜索结果（国家关键词）
    3. 法律后缀规则
    4. 默认 "港资"
    """
    company_lower = company.lower().strip()

    # 1. 预置映射表（用词边界避免误匹配，如 "lg" 不应匹配 "herbalgy"）
    for key, ctype in COMPANY_TYPE_MAP.items():
        # 短关键词（≤6字符）用词边界匹配，防止子串误判
        # 例如: "lg" ⊄ "herbalgy", "citi" ⊄ "citic"
        if len(key) <= 6:
            if re.search(rf'\b{re.escape(key)}\b', company_lower):
                return ctype
        else:
            if key in company_lower:
                return ctype

    # 2. Google 搜索结果
    if country_from_search:
        country = country_from_search
        if country == "香港":
            return "港资"
        elif country == "中国内地":
            return "中资"
        elif country in ("日本", "法国", "英国", "美国", "德国", "瑞士",
                         "瑞典", "丹麦", "荷兰", "芬兰", "意大利", "西班牙",
                         "韩国", "新加坡", "台湾", "澳大利亚", "加拿大"):
            if country in ("香港", "中国内地", "台湾", "新加坡"):
                return f"{country}外企"
            return f"{country}外企"

    # 3. 法律后缀规则
    for suffix, country_hint in SUFFIX_HINTS.items():
        if suffix in company_lower:
            # 排除香港注册的外企（有外资品牌但在香港注册）
            if "(h.k.)" in company_lower or "(hong kong)" in company_lower:
                # 检查是否有外资品牌关键词
                for key in COMPANY_TYPE_MAP:
                    if key in company_lower and "港资" not in COMPANY_TYPE_MAP[key]:
                        return COMPANY_TYPE_MAP[key]
                return "香港外企"
            if "日本" in country_hint:
                return "日本外企"
            if "香港" in country_hint:
                return "香港外企" if "(h.k.)" in company_lower else "港资"
            if "中国" in country_hint:
                return "中资"
            if "美国" in country_hint:
                return "美国外企"
            if "英国" in country_hint:
                return "英国外企"
            if "德国" in country_hint:
                return "德国外企"
            if "法国" in country_hint:
                return "法国外企"
            if "新加坡" in country_hint:
                return "新加坡外企"
            if "瑞典" in country_hint:
                return "瑞典外企"
            if "意大利" in country_hint:
                return "意大利外企"

    # 4. 名称关键词
    if any(kw in company_lower for kw in ["（hk）", "(hk)", "(hong kong)", "h.k."]):
        return "香港外企"

    # 5. 默认
    return "待确认"


def map_industry(subclass: str) -> str:
    """将 API subclassification 映射为中文行业。"""
    if not subclass:
        return "其他"

    key = subclass.strip().lower()
    if key in INDUSTRY_MAP:
        return INDUSTRY_MAP[key]

    # 模糊匹配
    for k, v in INDUSTRY_MAP.items():
        if k in key or key in k:
            return v

    return subclass  # 返回原始值


def enrich_companies(jobs: list, skip_rating: bool = False,
                     skip_type: bool = False) -> list:
    """批量补全所有公司的评分、类型、行业。"""
    # 收集唯一公司
    unique_companies = {}
    for job in jobs:
        company = job.get("company", "")
        if company and company not in unique_companies:
            unique_companies[company] = {
                "rating": "",
                "type": "",
                "industry": map_industry(job.get("subclass", "")),
            }

    companies_list = list(unique_companies.keys())
    print(f"[INFO] 共 {len(companies_list)} 个唯一公司待查询", file=sys.stderr)

    # 批量查询评分和类型
    for i, company in enumerate(companies_list):
        print(f"  [{i+1}/{len(companies_list)}] {company[:60]}", file=sys.stderr)

        # 先判断类型（快速规则）
        company_type = classify_company_type(company)
        need_search_type = company_type == "待确认"
        unique_companies[company]["type"] = company_type

        # Google 搜索评分
        if not skip_rating:
            query = f'"{company}" glassdoor rating'
            html = google_search(query)
            rating = extract_glassdoor_rating(html, company)
            if rating:
                unique_companies[company]["rating"] = rating
                print(f"    ✓ 评分: {rating}", file=sys.stderr)
            else:
                print(f"    ✗ 未找到评分", file=sys.stderr)

        # 对规则未覆盖的公司，Google 搜索总部
        if need_search_type and not skip_type:
            query = f'"{company}" 总部 headquarters'
            html = google_search(query)
            country = extract_headquarters_country(html, company)
            if country:
                company_type = classify_company_type(company, country)
                unique_companies[company]["type"] = company_type
                print(f"    ✓ 类型(搜索): {company_type}", file=sys.stderr)
            else:
                print(f"    ✗ 未找到总部信息 → 待确认", file=sys.stderr)

        # 控制频率：Google 搜索间隔
        if i < len(companies_list) - 1:
            time.sleep(2.5)

    # 应用到所有岗位
    for job in jobs:
        company = job.get("company", "")
        if company in unique_companies:
            info = unique_companies[company]
            if not job.get("rating") and info["rating"]:
                job["rating"] = info["rating"]
            if not job.get("company_type") and info["type"]:
                job["company_type"] = info["type"]
            if not job.get("industry_cn") and info["industry"]:
                job["industry_cn"] = info["industry"]

    # 统计
    rated = sum(1 for v in unique_companies.values() if v["rating"])
    typed = sum(1 for v in unique_companies.values() if v["type"] and v["type"] != "待确认")
    print(f"\n[DONE] 评分覆盖: {rated}/{len(companies_list)}, 类型覆盖: {typed}/{len(companies_list)}", file=sys.stderr)

    return jobs


def main():
    parser = argparse.ArgumentParser(description="公司信息补全")
    parser.add_argument("--input", "-i", required=True, help="输入 JSON 文件")
    parser.add_argument("--output", "-o", default="/tmp/jobs_enriched.json", help="输出 JSON 文件")
    parser.add_argument("--skip-rating", action="store_true", help="跳过评分查询")
    parser.add_argument("--skip-type", action="store_true", help="跳过类型查询")
    parser.add_argument("--companies-only", action="store_true", help="仅输出公司查询结果")
    parser.add_argument("--delay", type=float, default=2.5, help="Google 搜索间隔秒数")

    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        jobs = data
    elif isinstance(data, dict) and "jobs" in data:
        jobs = data["jobs"]
    else:
        jobs = [data]

    print(f"[INFO] 输入 {len(jobs)} 个岗位", file=sys.stderr)

    # 收集唯一公司
    unique_companies = {}
    for job in jobs:
        company = job.get("company", "")
        if company and company not in unique_companies:
            unique_companies[company] = {
                "rating": job.get("rating", ""),
                "type": job.get("company_type", ""),
                "industry": map_industry(job.get("subclass", "")),
            }

    if args.companies_only:
        # 仅输出公司列表
        for company, info in unique_companies.items():
            ctype = classify_company_type(company) if not info["type"] else info["type"]
            unique_companies[company]["type"] = ctype

        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(unique_companies, f, ensure_ascii=False, indent=2)
        print(f"[OUTPUT] {len(unique_companies)} 家公司 → {args.output}", file=sys.stderr)
        return

    # 批量补全
    enriched = enrich_companies(
        jobs,
        skip_rating=args.skip_rating,
        skip_type=args.skip_type,
    )

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)

    print(f"[OUTPUT] → {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
