# Jobsdb Job Scraper

批量抓取 [Jobsdb Hong Kong](https://hk.jobsdb.com) 岗位信息，自动获取完整 JD、公司 Glassdoor 评分、公司类型和行业分类，输出去重后的格式化 Excel。

## 输入 → 输出

**输入**：一个 Jobsdb HK 搜索 URL + 用于去重的基准文件（`.csv` 或 `.xlsx`）

```
https://hk.jobsdb.com/jobs-in-marketing-communications/full-time/on-site?salaryrange=20000-25000&salarytype=monthly
```

**输出**：格式化的 `.xlsx` 文件 + 更新后的 CSV

| # | 字段 | 数据来源 |
|---|------|---------|
| 1 | 序号 | 自增 |
| 2 | 类型 | 规则 + Google 搜索总部国家 |
| 3 | 行业 | API subclassification → 中文映射 |
| 4 | 公司 | API |
| 5 | 公司评分 | Google `"{公司}" glassdoor rating` 摘要提取 |
| 6 | 职位名称 | API |
| 7 | 薪资范围 | API |
| 8 | 工作描述 | 详情页 JS 渲染内容提取（完整 JD） |
| 9 | 地点 | API |
| 10 | 职位链接 | 构造自 job ID |

## 依赖

```bash
pip3 install openpyxl
```

其他依赖均为 Python 标准库 + 系统自带 curl。

## 快速开始

```bash
# 1. 抓取全部岗位（自动分页）
python3 fetch_jobs.py "https://hk.jobsdb.com/jobs-in-{分类}/full-time/on-site?...参数" -o /tmp/all_jobs.json

# 2. 去重（对比已有 CSV 或 Excel）
python3 dedup_append.py --new /tmp/all_jobs.json --existing "工作 - Sheet1.csv" --output /tmp/new.json

# 3. 获取完整 JD
python3 fetch_jd.py --input /tmp/new.json --output /tmp/new_jd.json

# 4. 补全公司信息（评分 + 类型 + 行业）
python3 enrich_company.py --input /tmp/new_jd.json --output /tmp/new_enriched.json

# 5. 写入 CSV
python3 dedup_append.py --new /tmp/new_enriched.json --existing "工作 - Sheet1.csv" --updated-csv "工作 - Sheet1.csv"

# 6. 生成 Excel
python3 export_excel.py --input "工作 - Sheet1.csv" --output "岗位收集.xlsx"
```

## 如何工作

### 数据获取

- **搜索**：通过 Jobsdb 内部 API (`/api/jobsearch/v5/search`) 获取结构化岗位列表，自动分页
- **详情**：访问 `/zh/job/{id}`（中文路径绕过 Cloudflare JS Challenge），从 `<script>` 标签 JSON 中提取完整 JD

### 公司信息补全

**评分**：Google 搜索 `"{公司名}" glassdoor rating`，从搜索结果摘要正则提取评分数字（1.0–5.0），无需访问 Glassdoor 本体。

**类型**（三层策略）：
1. 规则层（~60%）：200+ 知名公司预置映射 + 法律后缀判定
2. Google 摘要层（~30%）：搜索总部国家，从摘要提取
3. 待确认层（~10%）：标 "待确认"，人工审核

**行业**：API 返回的 subclassification → 60+ 中文行业映射表。

### 去重

按 job ID（从 URL 提取）+ 标准化公司名双重去重，基准文件支持 `.csv` 和 `.xlsx`。

## 脚本

| 脚本 | 功能 |
|------|------|
| `fetch_jobs.py` | 解析搜索 URL → 调用 API → 自动分页 → 输出 JSON |
| `fetch_jd.py` | 遍历岗位 ID → curl 详情页 → 提取完整 JD |
| `enrich_company.py` | 收集唯一公司 → Google 批量查评分+总部 → 行业映射 |
| `dedup_append.py` | 读取 CSV/Excel → 去重 → 追加写入 |
| `export_excel.py` | 读取 CSV → openpyxl 生成格式化 xlsx |

## 注意事项

- Google 搜索内置 2.5s 间隔，避免限流
- JD 提取依赖 `/zh/` 路径绕过 Cloudflare
- 大搜索量建议 `--max-pages` 分批处理
- 特殊分类可用 `--classification-id` 手动指定 API 分类 ID

## 搭配 Claude Code 使用

将此目录放入 `.claude/skills/` 并配置 skill 文件，即可在 Claude Code 中一键执行：
```
/jobsdb-scraper "搜索URL" --existing "基准文件.csv"
```
