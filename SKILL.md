---
name: jobsdb-scraper
description: 從 Jobsdb HK 搜尋 URL 批量抓取崗位資訊，自動補全公司評分/類型/行業，輸出格式化 Excel
---

# Jobsdb Job Scraper

批量抓取 [Jobsdb Hong Kong](https://hk.jobsdb.com) 崗位資訊，自動獲取完整 JD、Glassdoor 評分、公司類型、行業分類，輸出格式化 Excel。

## 輸入

- **必填**：一個 Jobsdb HK 搜尋 URL
- **可選**：一個用於去重的本地基準檔案（`.csv` 或 `.xlsx`）

### 兩種使用場景

**場景 A：僅提供 URL（首次收集）**
→ 抓取全部崗位 → 補全 JD 與公司資訊 → 直接輸出 Excel（跳過去重）

**場景 B：提供 URL + 本地基準檔案（增量更新）**
→ 抓取全部崗位 → 與基準檔案去重 → 僅處理新崗位 → 補全資訊 → 更新基準檔案 + 輸出 Excel

## 執行步驟

以下為場景 B（含去重）的完整流程。場景 A 跳過 Step 2。

### Step 1: 抓取全部崗位

```bash
python3 fetch_jobs.py "<搜尋URL>" -o /tmp/all_jobs.json
```

自動從 URL 解析 API 參數 → 獲取 `totalCount` → 遍歷所有分頁 → 合併輸出 JSON。

### Step 2: 去重（可選，僅場景 B）

```bash
python3 dedup_append.py \
  --new /tmp/all_jobs.json \
  --existing "<本地基準檔案>" \
  --output /tmp/new_unique.json
```

按 job ID + 標準化公司名雙重去重。自動識別基準檔案格式（CSV 或 Excel）。

### Step 3: 獲取完整 JD

```bash
python3 fetch_jd.py \
  --input /tmp/new_unique.json \
  --output /tmp/new_with_jd.json
```

透過 `/zh/job/{id}` 繞過 Cloudflare，從 `<script>` 標籤 JSON 提取 JD。

> 場景 A 時，`--input` 使用 `/tmp/all_jobs.json`。

### Step 4: 公司資訊補全

```bash
python3 enrich_company.py \
  --input /tmp/new_with_jd.json \
  --output /tmp/new_enriched.json
```

- **評分**：Google `"{公司}" glassdoor rating`，摘要提取評分數字
- **類型**：規則映射 → Google `"{公司}" 總部` 提取國家 → "待確認"
- **行業**：API subclassification → 中文映射

### Step 5: 寫入 CSV（可選，僅場景 B）

```bash
python3 dedup_append.py \
  --new /tmp/new_enriched.json \
  --existing "<本地基準檔案>" \
  --updated-csv "<本地基準檔案>" \
  --enriched
```

> 場景 A 跳過此步。

### Step 6: 生成 Excel

```bash
python3 export_excel.py \
  --input "<本地基準檔案或 /tmp/new_enriched.json>" \
  --output "崗位收集.xlsx"
```

場景 A 使用 `--new-only /tmp/new_enriched.json` 從 JSON 直接生成。

## 輸出欄位

| # | 欄位 | 來源 |
|---|------|------|
| 1 | 序號 | 自增 |
| 2 | 類型 | 規則 + Google 搜尋 |
| 3 | 行業 | API 中文映射 |
| 4 | 公司 | API |
| 5 | 公司評分 | Glassdoor 摘要提取 |
| 6 | 職位名稱 | API |
| 7 | 薪資範圍 | API |
| 8 | 工作描述 | 詳情頁完整 JD |
| 9 | 地點 | API |
| 10 | 職位連結 | `/zh/job/{id}` |

## 注意事項

- 依賴 `openpyxl`：`pip3 install openpyxl`
- Google 搜尋 2.5s 間隔，避免限流
- JD 依賴 `/zh/` 路徑繞過 Cloudflare
- 大搜尋量建議 `--max-pages` 分批處理
