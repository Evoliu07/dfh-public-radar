# 东方红 · 公开信息学习台

只汇总**公开信息**的个人学习页，不包含公司内部数据、客户信息、渠道政策或销售话术。

页面围绕 2026 年 11 月的两只产品：

- 东方红嘉俊均衡混合（A 029299 / C 029300）
- 东方红益鑫纯债债券（A 003668 / C 003669 / D 024961 / E 020615）

## 页面结构

1. **两只产品**：嘉俊看发行期、产品要素、公开策略；益鑫看净值、回撤、申赎状态。
2. **政策与事件**：CPI、PPI、LPR、M2、美国 CPI/PPI、产品发行/募集节点，并标注对哪只产品更相关。
3. **市场温度**：10Y/30Y 国债、LPR、Shibor 隔夜，以及沪深300、创业板、中证500、上证指数、恒生科技、恒生指数。
4. **新闻雷达**：财联社、东方财富、中国基金报的公开标题，按嘉俊/益鑫/政策/债市分类，附一句“为什么相关”。
5. **学习问题**：看完之后用自己的话回答。

## 文件

```text
index.html              页面
styles.css              样式
app.js                  前端渲染
fetch_data.py           抓取公开数据，写 data/dashboard.json
publish_update.py       把 data/dashboard.json 同步到 GitHub
update_and_publish.sh   本机定时任务入口
data/dashboard.json     页面数据（自动生成）
requirements.txt        Python 依赖
```

## 本地运行

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python fetch_data.py
.venv/bin/python -m http.server 8765
```

打开 `http://127.0.0.1:8765/`。不要直接双击 `index.html`，浏览器会拦截 `fetch(data/dashboard.json)`。

## 自动更新

当前用 macOS LaunchAgent 在本机运行：工作日 08:00–19:00 每 30 分钟执行一次：

```bash
.venv/bin/python fetch_data.py
.venv/bin/python publish_update.py
```

只提交 `data/dashboard.json`。Mac 睡眠或关机时不运行；重新唤醒后下一次定时会继续。

数据源：

- 东方红资产管理官网 / 证监会基金信息披露平台：产品要素、净值、公告
- 上清所 / 中债：国债收益率
- 东方财富、财联社、中国基金报：公开新闻标题
- 百度经济日历：宏观事件
- akshare：公开数据接口封装

> 如果以后要改成 GitHub Actions 原生定时，需要给 GitHub 授权 `workflow` 权限，再添加 `.github/workflows/update.yml`。目前没有使用这个方案，因为现有授权没有 workflow 权限。

## 注意

- 这是**个人学习页**，不是公司官方页面，也不构成投资建议、产品推介或收益承诺。
- 产品信息以基金管理人最新公告、基金合同、招募说明书为准。
- 新闻只保留标题、链接和短摘要，不转载全文；使用前请自行确认来源授权。
- 收益率按公开日增长率复利估算，未做费用调整，与官方口径可能不一致。
- 如果以后要加入内部数据，必须改为私有部署和权限控制，不能放在公开 GitHub Pages。
