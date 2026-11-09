#!/usr/bin/env python3
"""抓取公开信息，生成东方红双产品公开学习台的数据。

只使用公开页面/公开接口，不包含公司内部数据、客户信息或销售政策。
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import akshare as ak
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "dashboard.json"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST)
TODAY = NOW.date()
EPOCH = datetime(1970, 1, 1, tzinfo=CST)

PRODUCT_META = [
    {
        "id": "jiajun",
        "name": "东方红嘉俊均衡混合",
        "short": "嘉俊均衡",
        "codes": ["029299（A）", "029300（C）"],
        "type": "混合型",
        "status": "发行期",
        "status_note": "2026-11-09 起发行，公开报道募集期至 2026-11-25，以管理人公告为准",
        "manager": "马俊",
        "inception": "待基金成立",
        "equity_range": "股票资产 60%–95%",
        "hk_range": "港股通标的占股票资产 0%–50%",
        "benchmark": "沪深300×70% + 港股通综合×10% + 中债总全价×15% + 活期存款×5%",
        "fees": "管理费 1.2%/年 · 托管费 0.2%/年 · A 类申购费 0.8% · C 类销售服务费 0.4%/年",
        "risk": "混合型：预期风险高于债券型/货币型，低于股票型；风险等级以销售机构评级为准",
        "tags": ["新发", "偏股混合", "均衡策略"],
        "source": "东方红资产管理官网、同花顺、上海证券报公开报道",
    },
    {
        "id": "yixin",
        "name": "东方红益鑫纯债债券",
        "short": "益鑫纯债",
        "codes": ["003668（A）", "003669（C）", "024961（D）", "020615（E）"],
        "type": "债券型",
        "status": "正常开放",
        "status_note": "官网显示正常开放；申购状态以销售机构为准",
        "manager": "徐觅",
        "inception": "2016-11-28",
        "equity_range": "不参与股票投资",
        "hk_range": "—",
        "benchmark": "中债综合全价指数",
        "fees": "A 类申购费 0.7%（官网展示，具体以销售机构为准）",
        "risk": "债券型：预期风险高于货币市场基金，低于混合型/股票型；风险等级以销售机构评级为准",
        "tags": ["纯债", "老产品", "低波动"],
        "source": "东方红资产管理官网、证监会基金信息披露平台",
    },
]

SEED_MARKET = {
    "yields": [
        {"label": "10Y 国债", "value": 1.5829, "change_bp": -2.1, "date": "2026-11-06"},
        {"label": "30Y 国债", "value": 2.0216, "change_bp": -2.0, "date": "2026-11-06"},
    ],
    "lpr": {"1y": 3.0, "5y": 3.5, "date": "2026-10-20"},
    "shibor": {"label": "Shibor 隔夜", "value": 1.314, "date": "2026-11-09"},
    "indices": [
        {"label": "沪深300", "value": 4069.30, "change": 0.37},
        {"label": "创业板指", "value": 2487.91, "change": 0.92},
        {"label": "恒生科技", "value": 4075.42, "change": -0.07},
    ],
}

SEED_NEWS = [
    {
        "title": "资管老将马俊转型公募，11月9日首发东方红嘉俊均衡混合基金",
        "source": "上海证券报",
        "time": "2026-11-09 09:57",
        "url": "https://www.cnstock.com/",
        "tag": "产品",
        "impact": ["嘉俊"],
        "summary": "公开报道介绍产品发行期、股票仓位 60%–95%、港股通 0%–50% 及基金经理公开履历。",
        "why": "新发产品相关：看发行公告、产品要素和公开策略，不把公开报道当业绩。",
    },
    {
        "title": "三季度债基拉长久期降杠杆，长端利率下行引关注",
        "source": "上海证券报",
        "time": "2026-11-09 01:55",
        "url": "https://www.cnstock.com/",
        "tag": "债市",
        "impact": ["益鑫", "嘉俊"],
        "summary": "公开报道提到纯债基金久期拉长、杠杆下降，以及 10Y/30Y 国债收益率变化。",
        "why": "利率与债券价格反向：久期越长，利率波动对净值的影响通常越大。",
    },
]

SEED_EVENTS = [
    {"date": "2026-11-09", "time": "—", "title": "东方红嘉俊均衡开始发行（公开报道）", "region": "产品", "importance": 2, "actual": "", "forecast": "", "previous": "", "status": "进行中", "impact": ["嘉俊"], "source": "同花顺 / 上海证券报公开报道"},
    {"date": "2026-11-25", "time": "—", "title": "东方红嘉俊均衡公开募集期结束（公开报道）", "region": "产品", "importance": 2, "actual": "", "forecast": "", "previous": "", "status": "截止", "impact": ["嘉俊"], "source": "同花顺公开报道"},
]


def load_previous() -> dict:
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def as_float(value):
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        return float(value)
    except Exception:
        return None


def clean_text(value, limit=180) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit]


def latest_pair(df: pd.DataFrame, column: str):
    sub = df[["日期", column]].copy()
    sub["日期"] = pd.to_datetime(sub["日期"], errors="coerce")
    sub = sub.dropna(subset=["日期", column]).sort_values("日期")
    if len(sub) < 1:
        return None
    last = sub.iloc[-1]
    prev = sub.iloc[-2] if len(sub) >= 2 else last
    return {
        "value": round(float(last[column]), 4),
        "change_bp": round((float(last[column]) - float(prev[column])) * 100, 1) if len(sub) >= 2 else 0.0,
        "date": last["日期"].strftime("%Y-%m-%d"),
    }


def fund_stats(code: str, share_class: str):
    unit = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
    unit["净值日期"] = pd.to_datetime(unit["净值日期"], errors="coerce")
    unit = unit.dropna(subset=["净值日期"]).sort_values("净值日期")
    if unit.empty:
        return None
    unit["g"] = pd.to_numeric(unit["日增长率"], errors="coerce").fillna(0) / 100
    last = unit.iloc[-1]

    cum = ak.fund_open_fund_info_em(symbol=code, indicator="累计净值走势")
    cum["净值日期"] = pd.to_datetime(cum["净值日期"], errors="coerce")
    cum = cum.dropna(subset=["净值日期"]).sort_values("净值日期")
    latest_date = cum["净值日期"].iloc[-1]

    def ret(days: int):
        target = latest_date - pd.Timedelta(days=days)
        sub = unit[unit["净值日期"] > target]
        if len(sub) < 2:
            return None
        return round(((1 + sub["g"]).prod() - 1) * 100, 2)

    ytd_rows = unit[unit["净值日期"] >= pd.Timestamp(year=latest_date.year, month=1, day=1)]
    ytd = round(((1 + ytd_rows["g"]).prod() - 1) * 100, 2) if len(ytd_rows) > 1 else None

    one_year = cum[cum["净值日期"] >= latest_date - pd.Timedelta(days=365)].copy()
    mdd = None
    if not one_year.empty:
        one_year["peak"] = one_year["累计净值"].cummax()
        one_year["dd"] = one_year["累计净值"] / one_year["peak"] - 1
        mdd = round(float(one_year["dd"].min()) * 100, 2)

    return {
        "class": share_class,
        "date": last["净值日期"].strftime("%Y-%m-%d"),
        "nav": round(float(last["单位净值"]), 4),
        "daily": round(float(last["日增长率"]), 2) if pd.notna(last["日增长率"]) else None,
        "returns": {
            "1m": ret(30),
            "1y": ret(365),
            "3y": ret(1095),
            "since": round(((1 + unit["g"]).prod() - 1) * 100, 2),
            "ytd": ytd,
            "mdd1y": mdd,
            "basis": "按公开日增长率复利估算，未做费用调整；与官方口径可能存在差异",
        },
    }


def build_products(warnings: list[str]):
    products = []
    yixin_classes = []
    for code, cls in (("003668", "A"), ("020615", "E")):
        try:
            item = fund_stats(code, cls)
            if item:
                yixin_classes.append(item)
        except Exception as exc:
            warnings.append(f"基金 {code} 净值抓取失败：{type(exc).__name__}")

    for meta in PRODUCT_META:
        item = dict(meta)
        if meta["id"] == "jiajun":
            item.update({"nav": None, "returns": None, "nav_classes": []})
        else:
            main = next((x for x in yixin_classes if x["class"] == "A"), None)
            item.update({
                "nav": {"date": main["date"], "value": main["nav"], "daily": main["daily"], "class": "A"} if main else None,
                "returns": main["returns"] if main else None,
                "nav_classes": [
                    {"class": x["class"], "nav": x["nav"], "daily": x["daily"], "date": x["date"]}
                    for x in yixin_classes
                ],
            })
        products.append(item)
    return products


def build_market(warnings: list[str]):
    market = {"yields": [], "indices": [], "lpr": None, "shibor": None}
    try:
        rates = ak.bond_zh_us_rate(start_date=(TODAY - timedelta(days=50)).strftime("%Y%m%d"))
        for label, col in (("10Y 国债", "中国国债收益率10年"), ("30Y 国债", "中国国债收益率30年")):
            pair = latest_pair(rates, col)
            if pair:
                market["yields"].append({"label": label, **pair})
    except Exception as exc:
        warnings.append(f"国债收益率抓取失败：{type(exc).__name__}")
        market["yields"] = SEED_MARKET["yields"]

    try:
        lpr = ak.macro_china_lpr()
        last = lpr.dropna(subset=["LPR1Y"]).iloc[-1]
        market["lpr"] = {
            "1y": round(float(last["LPR1Y"]), 2),
            "5y": round(float(last["LPR5Y"]), 2),
            "date": pd.to_datetime(last["TRADE_DATE"]).strftime("%Y-%m-%d"),
        }
    except Exception as exc:
        warnings.append(f"LPR 抓取失败：{type(exc).__name__}")
        market["lpr"] = SEED_MARKET["lpr"]

    try:
        shibor = ak.rate_interbank(market="上海银行同业拆借市场", symbol="Shibor人民币", indicator="隔夜")
        last = shibor.dropna(subset=["利率"]).iloc[-1]
        market["shibor"] = {
            "label": "Shibor 隔夜",
            "value": round(float(last["利率"]), 3),
            "date": pd.to_datetime(last["报告日"]).strftime("%Y-%m-%d"),
        }
    except Exception as exc:
        warnings.append(f"资金利率抓取失败：{type(exc).__name__}")
        market["shibor"] = SEED_MARKET["shibor"]

    try:
        idx = ak.stock_zh_index_spot_em(symbol="沪深重要指数")
        wanted = {"000300": "沪深300", "399006": "创业板指", "000905": "中证500", "000001": "上证指数"}
        for code, name in wanted.items():
            row = idx[idx["代码"].astype(str).str.zfill(6) == code]
            if not row.empty:
                r = row.iloc[0]
                market["indices"].append({
                    "label": name,
                    "value": round(float(r["最新价"]), 2),
                    "change": round(float(r["涨跌幅"]), 2),
                })
    except Exception as exc:
        warnings.append(f"A 股指数抓取失败：{type(exc).__name__}")

    try:
        hk = ak.stock_hk_index_spot_sina()
        for code, name in (("HSTECH", "恒生科技"), ("HSI", "恒生指数")):
            row = hk[hk["代码"] == code]
            if not row.empty:
                r = row.iloc[0]
                market["indices"].append({
                    "label": name,
                    "value": round(float(r["最新价"]), 2),
                    "change": round(float(r["涨跌幅"]), 2),
                })
    except Exception as exc:
        warnings.append(f"港股指数抓取失败：{type(exc).__name__}")

    if not market["indices"]:
        market["indices"] = SEED_MARKET["indices"]
    return market


def event_impact(title: str, region: str):
    text = title or ""
    if any(k in text for k in ("LPR", "CPI", "PPI", "GDP", "PCE", "社融", "信贷", "M2", "M1", "PMI", "利率")):
        return ["益鑫", "嘉俊"]
    if region == "美国" or any(k in text for k in ("美联储", "非农", "关税")):
        return ["嘉俊"]
    return ["嘉俊", "益鑫"]


def event_category(title: str) -> str:
    if any(key in title for key in ("贸易帐", "出口", "进口")):
        return "trade"
    for key in ("CPI", "PPI", "LPR", "PCE", "GDP", "社融", "M2", "PMI", "工业增加值", "社会消费品零售"):
        if key in title:
            return key
    return "其他"


def event_priority(title: str) -> int:
    noise = ("原油", "天然气", "成品油", "黄金", "白银", "库存", "持仓", "API", "EIA", "SPDR", "iShares", "COMEX", "TIPS", "资产负债表", "仓单", "消费者信心", "当周")
    if any(word in title for word in noise):
        return 0
    if "CPI年率" in title or "PPI年率" in title:
        if "能源" in title or "核心" in title:
            return 96
        return 100
    if "LPR" in title:
        return 98
    if "GDP" in title or "PCE" in title:
        return 90
    if "社融" in title or "M2" in title:
        return 85
    if "PMI" in title:
        return 80
    if "工业增加值" in title or "社会消费品零售" in title:
        return 75
    if "贸易帐-美元" in title:
        return 65
    if "出口年率-美元" in title or "进口年率-美元" in title:
        return 60
    return 0


def build_events(warnings: list[str]):
    events = [dict(x, _priority=100) for x in SEED_EVENTS]
    seen = {(x["date"], x["time"], x["title"]) for x in events}

    for offset in range(0, 15):
        day = TODAY + timedelta(days=offset)
        try:
            df = ak.news_economic_baidu(date=day.strftime("%Y%m%d"))
            if df is None or df.empty:
                continue
            for _, row in df.iterrows():
                title = clean_text(row.get("事件"), 120)
                region = clean_text(row.get("地区"), 20)
                if not title or region not in ("中国", "美国"):
                    continue
                priority = event_priority(title)
                if priority <= 0:
                    continue
                try:
                    importance = int(float(row.get("重要性")))
                except Exception:
                    importance = 2
                if importance < 2:
                    continue
                actual = row.get("公布")
                status = "已公布" if pd.notna(actual) else "待公布"
                key = (day.strftime("%Y-%m-%d"), clean_text(row.get("时间"), 10) or "—", title)
                if key in seen:
                    continue
                seen.add(key)
                events.append({
                    "date": day.strftime("%Y-%m-%d"),
                    "time": clean_text(row.get("时间"), 10) or "—",
                    "title": title,
                    "region": region,
                    "importance": importance,
                    "actual": "" if pd.isna(actual) else clean_text(actual, 40),
                    "forecast": "" if pd.isna(row.get("预期")) else clean_text(row.get("预期"), 40),
                    "previous": "" if pd.isna(row.get("前值")) else clean_text(row.get("前值"), 40),
                    "status": status,
                    "impact": event_impact(title, region),
                    "source": "百度经济日历",
                    "_priority": priority,
                })
        except Exception as exc:
            warnings.append(f"经济日历 {day} 抓取失败：{type(exc).__name__}")
            break

    # 同一时间只保留一个同类事件，避免“出口/进口/贸易帐”刷屏
    best = {}
    for item in events:
        key = (item["date"], item["time"], event_category(item["title"]))
        if key not in best or item.get("_priority", 0) > best[key].get("_priority", 0):
            best[key] = item
    result = sorted(best.values(), key=lambda x: (x["date"], x["time"]))
    for item in result:
        item.pop("_priority", None)
    must = [x for x in result if x.get("region") == "产品" or "LPR" in x.get("title", "")]
    rest = [x for x in result if x not in must]
    return sorted(must + rest[:max(0, 9 - len(must))], key=lambda x: (x["date"], x["time"]))


def news_tags(title: str):
    tags = []
    if "嘉俊" in title or "029299" in title or "029300" in title:
        tags.append("嘉俊")
    if "益鑫" in title or "003668" in title or "020615" in title:
        tags.append("益鑫")
    if any(k in title for k in ("央行", "证监会", "关税", "降准", "降息", "LPR", "监管", "政策", "费率", "销售费用")):
        tags.append("政策")
    if any(k in title for k in ("债市", "国债", "信用债", "债券", "利率", "久期", "杠杆", "纯债")):
        tags.append("债市")
    if any(k in title for k in ("权益", "股市", "港股", "AI", "科技", "红利")):
        tags.append("权益")
    if any(k in title for k in ("基金", "公募", "发行", "ETF")):
        tags.append("行业")
    if not tags:
        tags.append("市场")
    return tags


def news_relevance(title: str) -> int:
    score = 0
    if "嘉俊" in title or "益鑫" in title or "东方红" in title:
        score += 10
    for word in ("债市", "国债", "信用债", "利率", "LPR", "央行", "降准", "降息", "久期", "杠杆"):
        if word in title:
            score += 3
    for word in ("基金", "费率", "销售费用", "公募", "发行"):
        if word in title:
            score += 2
    for word in ("权益", "股市", "港股", "AI", "科技", "红利", "关税"):
        if word in title:
            score += 2
    return score


def news_impact(title: str):
    tags = news_tags(title)
    if "嘉俊" in tags and "益鑫" in tags:
        return ["嘉俊", "益鑫"]
    if "益鑫" in tags or "债市" in tags:
        return ["益鑫"]
    if "嘉俊" in tags or "权益" in tags:
        return ["嘉俊"]
    return ["嘉俊", "益鑫"]


def news_why(title: str):
    tags = news_tags(title)
    if "嘉俊" in tags:
        return "新发产品相关：看发行公告、产品要素和公开策略，不把报道当业绩。"
    if "益鑫" in tags:
        return "产品相关：看净值、回撤、久期和信用暴露。"
    if "债市" in tags:
        return "利率与债券价格反向：久期越长，利率波动对净值的影响通常越大。"
    if "政策" in tags:
        return "政策变化可能影响利率、风险偏好或基金销售规则，先看原文和适用范围。"
    if "权益" in tags:
        return "权益/港股相关：关注股票仓位、行业风格和回撤。"
    if "行业" in tags:
        return "基金行业信息：关注费率、销售规则和产品供给变化。"
    return "公开市场信息，作为理解产品所处环境的背景。"


def parse_news_time(text: str):
    text = (text or "").strip()
    for value in (text[:19], text[:16], text[:10]):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt).replace(tzinfo=CST)
            except Exception:
                continue
    match = re.search(r"(20\d{2}-\d{2}-\d{2})", text)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y-%m-%d").replace(tzinfo=CST)
        except Exception:
            pass
    return None


def news_bucket(title: str) -> str:
    if any(k in title for k in ("东方红", "嘉俊", "益鑫")):
        return "product"
    if any(k in title for k in ("央行", "证监会", "关税", "降准", "降息", "LPR", "费率", "销售费用", "监管", "政策")):
        return "policy"
    if any(k in title for k in ("债市", "国债", "信用债", "利率", "久期", "杠杆", "纯债", "债券")):
        return "bond"
    if any(k in title for k in ("基金", "公募", "发行", "ETF")):
        return "industry"
    if any(k in title for k in ("权益", "股市", "港股", "AI", "科技", "红利", "算力")):
        return "equity"
    return "other"


def build_news(warnings: list[str]):
    items = []

    try:
        cls = ak.stock_info_global_cls(symbol="全部")
        for _, row in cls.iterrows():
            title = clean_text(row.get("标题"), 160)
            content = clean_text(row.get("内容"), 260)
            if not title:
                title = content[:80]
            if not title:
                continue
            time_text = f"{row.get('发布日期', '')} {row.get('发布时间', '')}".strip()
            items.append({
                "title": title,
                "source": "财联社",
                "time": time_text,
                "url": "https://www.cls.cn/telegraph",
                "summary": content[:140],
            })
    except Exception as exc:
        warnings.append(f"财联社快讯抓取失败：{type(exc).__name__}")

    try:
        em = ak.stock_info_global_em()
        for _, row in em.iterrows():
            title = clean_text(row.get("标题"), 160)
            if not title:
                continue
            items.append({
                "title": title,
                "source": "东方财富",
                "time": clean_text(row.get("发布时间"), 20),
                "url": clean_text(row.get("链接"), 300),
                "summary": clean_text(row.get("摘要"), 160),
            })
    except Exception as exc:
        warnings.append(f"东方财富快讯抓取失败：{type(exc).__name__}")

    try:
        import requests
        from bs4 import BeautifulSoup

        resp = requests.get("https://www.chnfund.com/", timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        seen = set()
        for a in soup.select('a[href^="/article/"]'):
            title = clean_text(a.get_text(" ", strip=True), 160)
            href = a.get("href") or ""
            if not title or len(title) < 8 or (href, title) in seen:
                continue
            seen.add((href, title))
            date_match = re.search(r"(20\d{2}-\d{2}-\d{2})", title)
            date_text = date_match.group(1) if date_match else ""
            title = re.sub(r"\s*20\d{2}-\d{2}-\d{2}\s*$", "", title).strip()
            items.append({
                "title": title,
                "source": "中国基金报",
                "time": date_text,
                "url": "https://www.chnfund.com" + href,
                "summary": "",
            })
    except Exception as exc:
        warnings.append(f"中国基金报头条抓取失败：{type(exc).__name__}")

    if not items:
        return SEED_NEWS

    dedup = {}
    for item in items:
        key = re.sub(r"[^\w\u4e00-\u9fff]", "", item["title"])[:80]
        if not key:
            continue
        score = news_relevance(item["title"])
        if score <= 0:
            continue
        if key not in dedup or score > dedup[key]["_score"]:
            dedup[key] = {**item, "_score": score}

    cutoff = NOW - timedelta(days=10)
    candidates = []
    for item in dedup.values():
        dt = parse_news_time(item.get("time", ""))
        if dt and dt < cutoff:
            continue
        bucket = news_bucket(item["title"])
        if item.get("source") == "中国基金报" and not dt and bucket not in ("product", "policy", "bond", "industry"):
            continue
        candidates.append({**item, "_bucket": bucket, "_dt": dt})

    buckets = {}
    for item in sorted(candidates, key=lambda x: (x["_score"], x["_dt"] or EPOCH), reverse=True):
        buckets.setdefault(item["_bucket"], []).append(item)

    selected = []
    for bucket, limit in (("product", 3), ("policy", 4), ("bond", 5), ("industry", 2), ("equity", 2)):
        selected.extend(buckets.get(bucket, [])[:limit])
    if len(selected) < 8:
        for item in sorted(candidates, key=lambda x: x["_score"], reverse=True):
            if item not in selected:
                selected.append(item)
    selected = sorted(selected[:12], key=lambda x: (x["_dt"] or EPOCH, x["_score"]), reverse=True)

    result = []
    for item in selected:
        title = item["title"]
        result.append({
            "title": title,
            "source": item["source"],
            "time": item.get("time") or "—",
            "url": item.get("url", ""),
            "summary": item.get("summary", "")[:140],
            "tag": news_tags(title)[0],
            "impact": news_impact(title),
            "why": news_why(title),
        })
    return result or SEED_NEWS


def main():
    previous = load_previous()
    warnings = []

    try:
        products = build_products(warnings)
    except Exception as exc:
        warnings.append(f"产品数据生成失败：{type(exc).__name__}")
        products = previous.get("products", [])

    try:
        market = build_market(warnings)
    except Exception as exc:
        warnings.append(f"市场数据生成失败：{type(exc).__name__}")
        market = previous.get("market", SEED_MARKET)

    try:
        events = build_events(warnings)
    except Exception as exc:
        warnings.append(f"事件日历生成失败：{type(exc).__name__}")
        events = previous.get("events", SEED_EVENTS)

    try:
        news = build_news(warnings)
    except Exception as exc:
        warnings.append(f"新闻生成失败：{type(exc).__name__}")
        news = previous.get("news", SEED_NEWS)

    data_dates = [x.get("date") for x in products if x.get("nav")]
    if market.get("yields"):
        data_dates.extend(x.get("date") for x in market["yields"])
    data_date = max([d for d in data_dates if d] or [TODAY.strftime("%Y-%m-%d")])

    payload = {
        "meta": {
            "title": "东方红 · 公开信息学习台",
            "subtitle": "11 月双产品 · 只汇总公开资料",
            "updated_at": NOW.strftime("%Y-%m-%d %H:%M"),
            "data_date": data_date,
            "warnings": warnings,
            "sources": [
                "东方红资产管理官网",
                "证监会基金信息披露平台",
                "上清所 / 中债",
                "东方财富",
                "财联社",
                "中国基金报",
                "百度经济日历",
            ],
            "disclaimer": "本页仅汇总公开信息，用于个人学习，不构成任何投资建议、产品推介或收益承诺。产品信息以基金管理人最新公告和基金合同为准。基金有风险，投资需谨慎。",
        },
        "products": products,
        "market": market,
        "events": events,
        "news": news,
        "questions": [
            "嘉俊均衡是新发产品，发行期和成立后分别该看什么？",
            "益鑫纯债的久期、杠杆和信用暴露，对回撤意味着什么？",
            "10Y/30Y 国债收益率上行 10bp，对纯债净值大致意味着什么？",
            "如果权益市场风格切换，嘉俊均衡的行业和风格均衡是否足够？",
            "公开报道、官方公告和第三方数据冲突时，应该以哪一个为准？",
        ],
    }

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[{NOW:%Y-%m-%d %H:%M}] 写入 {DATA_FILE}（产品 {len(products)}，事件 {len(events)}，新闻 {len(news)}）")
    if warnings:
        print("警告：")
        for warning in warnings:
            print(" -", warning)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FATAL: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
