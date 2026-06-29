---
name: jobsdb-scraper
description: 从 Jobsdb HK 搜索 URL 批量抓取岗位信息，自动补全公司评分/类型/行业，输出格式化 Excel
---

# Jobsdb Job Scraper

批量抓取 [Jobsdb Hong Kong](https://hk.jobsdb.com) 岗位信息，自动获取完整 JD、Glassdoor 评分、公司类型、行业分类，输出格式化 Excel。

## 输入

- 一个 Jobsdb HK 搜索 URL：`https://hk.jobsdb.com/jobs-in-{分类}/full-time/on-site?salaryrange=20000-25000&salarytype=monthly`
- 用于去重的基准文件路径（`.csv` 或 `.xlsx`）

## 执行步骤

### Step 1: 抓取全部岗位

```bash
python3 fetch_jobs.py "<搜索URL>" -o /tmp/all_jobs.json
```

自动从 URL 解析 API 参数 → 获取 `totalCount` → 遍历所有分页 → 合并输出 JSON。

### Step 2: 去重

```bash
python3 dedup_append.py \
  --new /tmp/all_jobs.json \
  --existing "<基准文件.csv或.xlsx>" \
  --output /tmp/new_unique.json \
  --updated-csv "<基准文件.csv>"
```

按 job ID（URL 提取）+ 标准化公司名双重去重。自动识别基准文件格式。

### Step 3: 获取完整 JD

```bash
python3 fetch_jd.py \
  --input /tmp/new_unique.json \
  --output /tmp/new_with_jd.json
```

通过 `/zh/job/{id}` 绕过 Cloudflare，从 `<script>` 标签 JSON 提取 JD。

### Step 4: 公司信息补全

```bash
python3 enrich_company.py \
  --input /tmp/new_with_jd.json \
  --output /tmp/new_enriched.json
```

- **评分**：Google `"{公司}" glassdoor rating`，摘要提取评分数字
- **类型**：规则映射 → Google `"{公司}" 总部` 提取国家 → "待确认"
- **行业**：API subclassification → 中文映射

### Step 5: 写入 CSV

```bash
python3 dedup_append.py \
  --new /tmp/new_enriched.json \
  --existing "<基准文件.csv>" \
  --updated-csv "<基准文件.csv>" \
  --enriched
```

### Step 6: 生成 Excel

```bash
python3 export_excel.py \
  --input "<基准文件.csv>" \
  --output "岗位收集_{关键词}_{日期}.xlsx"
```

## 输出字段

| # | 字段 | 来源 |
|---|------|------|
| 1 | 序号 | 自增 |
| 2 | 类型 | 规则 + Google 搜索 |
| 3 | 行业 | API 中文映射 |
| 4 | 公司 | API |
| 5 | 公司评分 | Glassdoor 摘要提取 |
| 6 | 职位名称 | API |
| 7 | 薪资范围 | API |
| 8 | 工作描述 | 详情页完整 JD |
| 9 | 地点 | API |
| 10 | 职位链接 | `/zh/job/{id}` |

## 注意事项

- 依赖 `openpyxl`：`pip3 install openpyxl`
- Google 搜索 2.5s 间隔，避免限流
- JD 依赖 `/zh/` 路径绕过 Cloudflare
- 大搜索量建议 `--max-pages` 分批处理
