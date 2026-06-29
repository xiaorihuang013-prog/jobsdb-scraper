# Jobsdb Job Scraper

批量抓取 [Jobsdb Hong Kong](https://hk.jobsdb.com) 崗位資訊，自動獲取完整 JD、公司 Glassdoor 評分、公司類型和行業分類，輸出去重後的格式化 Excel。

## 輸入 → 輸出

**輸入**：一個 Jobsdb HK 搜尋 URL + 用於去重的基準檔案（`.csv` 或 `.xlsx`）

```
https://hk.jobsdb.com/jobs-in-marketing-communications/full-time/on-site?salaryrange=20000-25000&salarytype=monthly
```

**輸出**：格式化的 `.xlsx` 檔案 + 更新後的 CSV

| # | 欄位 | 資料來源 |
|---|------|---------|
| 1 | 序號 | 自增 |
| 2 | 類型 | 規則 + Google 搜尋總部國家 |
| 3 | 行業 | API subclassification → 中文映射 |
| 4 | 公司 | API |
| 5 | 公司評分 | Google `"{公司}" glassdoor rating` 摘要提取 |
| 6 | 職位名稱 | API |
| 7 | 薪資範圍 | API |
| 8 | 工作描述 | 詳情頁 JS 渲染內容提取（完整 JD） |
| 9 | 地點 | API |
| 10 | 職位連結 | 構造自 job ID |

## 依賴

```bash
pip3 install openpyxl
```

其他依賴均為 Python 標準庫 + 系統自帶 curl。

## 快速開始

```bash
# 1. 抓取全部崗位（自動分頁）
python3 fetch_jobs.py "https://hk.jobsdb.com/jobs-in-{分類}/full-time/on-site?...參數" -o /tmp/all_jobs.json

# 2. 去重（對比已有 CSV 或 Excel）
python3 dedup_append.py --new /tmp/all_jobs.json --existing "工作 - Sheet1.csv" --output /tmp/new.json

# 3. 獲取完整 JD
python3 fetch_jd.py --input /tmp/new.json --output /tmp/new_jd.json

# 4. 補全公司資訊（評分 + 類型 + 行業）
python3 enrich_company.py --input /tmp/new_jd.json --output /tmp/new_enriched.json

# 5. 寫入 CSV
python3 dedup_append.py --new /tmp/new_enriched.json --existing "工作 - Sheet1.csv" --updated-csv "工作 - Sheet1.csv"

# 6. 生成 Excel
python3 export_excel.py --input "工作 - Sheet1.csv" --output "崗位收集.xlsx"
```

## 如何工作

### 資料獲取

- **搜尋**：透過 Jobsdb 內部 API (`/api/jobsearch/v5/search`) 獲取結構化崗位列表，自動分頁
- **詳情**：訪問 `/zh/job/{id}`（中文路徑繞過 Cloudflare JS Challenge），從 `<script>` 標籤 JSON 中提取完整 JD

### 公司資訊補全

**評分**：Google 搜尋 `"{公司名}" glassdoor rating`，從搜尋結果摘要正則提取評分數字（1.0–5.0），無需訪問 Glassdoor 本體。

**類型**（三層策略）：
1. 規則層（~60%）：200+ 知名公司預置映射 + 法律後綴判定
2. Google 摘要層（~30%）：搜尋總部國家，從摘要提取
3. 待確認層（~10%）：標 "待確認"，人工審核

**行業**：API 返回的 subclassification → 60+ 中文行業映射表。

### 去重

按 job ID（從 URL 提取）+ 標準化公司名雙重去重，基準檔案支援 `.csv` 和 `.xlsx`。

## 腳本

| 腳本 | 功能 |
|------|------|
| `fetch_jobs.py` | 解析搜尋 URL → 調用 API → 自動分頁 → 輸出 JSON |
| `fetch_jd.py` | 遍歷崗位 ID → curl 詳情頁 → 提取完整 JD |
| `enrich_company.py` | 收集唯一公司 → Google 批量查評分+總部 → 行業映射 |
| `dedup_append.py` | 讀取 CSV/Excel → 去重 → 追加寫入 |
| `export_excel.py` | 讀取 CSV → openpyxl 生成格式化 xlsx |

## Claude Code Skill 配置

將此專案配置為 Claude Code Skill，即可在對話中一鍵執行 `/jobsdb-scraper`。

### 1. Clone 專案

```bash
git clone https://github.com/xiaorihuang013-prog/jobsdb-scraper.git
cd jobsdb-scraper
pip3 install openpyxl
```

### 2. 將 SKILL.md 複製到專案

```bash
# 在你的工作目錄中
mkdir -p .claude/skills
cp jobsdb-scraper/SKILL.md .claude/skills/jobsdb-scraper.md
```

或者放到全域 skill 目錄（所有專案通用）：

```bash
cp jobsdb-scraper/SKILL.md ~/.claude/skills/jobsdb-scraper.md
```

### 3. 在 Claude Code 中使用

```
/jobsdb-scraper "https://hk.jobsdb.com/jobs-in-marketing-communications/full-time/on-site?salaryrange=20000-25000&salarytype=monthly" --existing "工作 - Sheet1.csv"
```

Claude 會自動執行全部 6 步：分頁抓取 → 去重 → JD 提取 → 公司補全 → CSV 更新 → Excel 輸出。

### Skill 檔案說明

`SKILL.md` 檔案頂部的 YAML frontmatter 是 Claude Code 識別 skill 的關鍵：

```yaml
---
name: jobsdb-scraper          # skill 名稱，對應 /jobsdb-scraper 命令
description: ...              # 描述，在 skill 列表中展示
---
```

修改 `name` 欄位可自訂命令名稱，修改後檔案名需與 `name` 一致。

## 負責任使用

- 本工具僅供個人效率提升與研究用途。
- 請勿用於大規模爬蟲或自動化資料收集。
- 請遵守目標網站的 robots.txt 及服務條款。
- 請勿轉散布本工具所獲取之受版權保護內容。

## 注意事項

- Google 搜尋內置 2.5s 間隔，避免限流
- JD 提取依賴 `/zh/` 路徑繞過 Cloudflare
- 大搜尋量建議 `--max-pages` 分批處理
- 特殊分類可用 `--classification-id` 手動指定 API 分類 ID
