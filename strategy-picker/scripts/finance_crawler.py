"""
多平台帖子爬虫
支持：雪球、微博、淘股吧、东方财富、腾讯财经、和讯网
使用 playwright-stealth 绕过阿里云 WAF

用法:
    python3 xueqiu_crawler.py              # 立即抓取一次

Cookie 说明:
    六个平台均无需登录即可抓取。
"""

import hashlib
import json
import re
import shutil
import time
from bs4 import BeautifulSoup
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
from html.parser import HTMLParser

import tempfile
# ── 配置 ──────────────────────────────────────────────────────────────────────
OUTPUT_DIR   = Path(tempfile.gettempdir()) / "bitsoul_stock_info_tmp"
DEFAULT_DAYS = 3
USER_AGENT   = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

# 每个平台的抓取目标
# 公共字段：
#   name        显示名称
#   platform    平台标识（决定使用哪个解析器/抓取函数）
#   cookie_file Cookie 文件路径，不需要则填 None
#
# 博主类平台（雪球/微博/淘股吧/东方财富）专属字段：
#   user_ids    博主 ID 列表，支持多个
#
# 巨潮专属字段：
#   stocks      指定股票列表，如 ["000001,SZ","600519,SH"]；必须提供，空列表 = 跳过抓取

# 各平台博主页面 URL 模板
_URL_TEMPLATES = {
    "xueqiu":    "https://xueqiu.com/u/{uid}",
    "weibo":     "https://m.weibo.cn/u/{uid}",
    "tgb":       "https://www.tgb.cn/blog/{uid}",
    "eastmoney": "https://i.eastmoney.com/{uid}",
}

TARGETS = [
    {
        "name":        "雪球",
        "platform":    "xueqiu",
        "user_ids":    ["5999183282", "3058599833"],
        "cookie_file": None,
    },
    {
        "name":        "微博",
        "platform":    "weibo",
        "user_ids":    ["3194744501", "5560629150"],
        "cookie_file": None,
    },
    {
        "name":        "淘股吧",
        "platform":    "tgb",
        "user_ids":    ["10236056"],
        "cookie_file": None,
    },
    {
        "name":        "东方财富",
        "platform":    "eastmoney",
        "user_ids":    ["3131336010335678", "1376094486751060"],
        "cookie_file": None,
    },
]
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ── 用户名 → ID 解析 ──────────────────────────────────────────────────────────

_USER_CACHE_PATH = OUTPUT_DIR / "user_cache.json"


def _load_user_cache() -> dict:
    try:
        if _USER_CACHE_PATH.exists():
            return json.loads(_USER_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_user_cache(cache: dict) -> None:
    try:
        _USER_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _USER_CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        log.warning("[用户缓存] 写入失败: %s", e)


def _resolve_user_id(name_or_id: str, platform: str) -> str:
    """
    将用户名（昵称）解析为对应平台的用户 ID。
    若传入的已是纯数字 ID 则直接返回。
    支持平台：xueqiu（雪球）、weibo（微博）、eastmoney（东方财富）、tgb（淘股吧）。
    解析结果会缓存到 user_cache.json，下次直接命中，无需重新搜索。
    """
    if re.match(r"^\d+$", name_or_id.strip()):
        return name_or_id.strip()

    username = name_or_id.strip()

    # 先查缓存
    cache = _load_user_cache()
    cached_uid = cache.get(username, {}).get(platform)
    if cached_uid:
        log.info("[%s] 用户名 '%s' 命中缓存，ID: %s", platform, username, cached_uid)
        return cached_uid

    if platform == "xueqiu":
        # 用 Playwright 加载搜索页，拦截 search/user.json 接口（无需登录）
        try:
            from playwright.sync_api import sync_playwright
            from playwright_stealth import Stealth
            found = []
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                ctx = browser.new_context(user_agent=USER_AGENT, locale="zh-CN")
                page = ctx.new_page()
                Stealth().apply_stealth_sync(page)

                def _on_resp(response):
                    if "search/user.json" in response.url:
                        try:
                            found.append(response.json())
                        except Exception:
                            pass
                page.on("response", _on_resp)
                page.goto(f"https://xueqiu.com/k?q={username}",
                          timeout=20000, wait_until="domcontentloaded")
                page.wait_for_timeout(4000)
                browser.close()

            for result in found:
                for u in result.get("list", []):
                    if u.get("screen_name") == username:
                        uid = str(u.get("id", ""))
                        log.info("[雪球] 用户名 '%s' 解析为 ID: %s", username, uid)
                        return _cache_user_id(username, platform, uid)
            # 精确匹配失败，仅当第一个结果名字包含关键词时接受
            for result in found:
                lst = result.get("list", [])
                if lst:
                    first_name = lst[0].get("screen_name", "")
                    if username in first_name or first_name in username:
                        uid = str(lst[0].get("id", ""))
                        log.warning("[雪球] 未精确匹配 '%s'，取近似结果: %s (%s)",
                                    username, first_name, uid)
                        return _cache_user_id(username, platform, uid)
                    break
        except Exception as e:
            log.warning("[雪球] 用户名解析失败 '%s': %s", username, e)

    elif platform == "weibo":
        try:
            from playwright.sync_api import sync_playwright
            from playwright_stealth import Stealth
            found = []
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                ctx = browser.new_context(user_agent=USER_AGENT, locale="zh-CN")
                page = ctx.new_page()
                Stealth().apply_stealth_sync(page)

                def _on_resp(response):
                    if "containerid=100103" in response.url:
                        try:
                            found.append(response.json())
                        except Exception:
                            pass
                page.on("response", _on_resp)
                page.goto(
                    f"https://m.weibo.cn/search?containerid=100103type%3D3%26q%3D{username}&page_type=searchall",
                    timeout=20000, wait_until="domcontentloaded",
                )
                page.wait_for_timeout(4000)
                browser.close()

            for result in found:
                cards = result.get("data", {}).get("cards", [])
                for card in cards:
                    for item in card.get("card_group", []):
                        user = item.get("user", {})
                        if user.get("screen_name") == username:
                            uid = str(user.get("id", ""))
                            log.info("[微博] 用户名 '%s' 解析为 ID: %s", username, uid)
                            return _cache_user_id(username, platform, uid)
            # 精确匹配失败，仅当第一个结果名字包含关键词时接受
            for result in found:
                cards = result.get("data", {}).get("cards", [])
                for card in cards:
                    for item in card.get("card_group", []):
                        user = item.get("user", {})
                        if user.get("id"):
                            first_name = user.get("screen_name", "")
                            if username in first_name or first_name in username:
                                uid = str(user["id"])
                                log.warning("[微博] 未精确匹配 '%s'，取近似结果: %s (%s)",
                                            username, first_name, uid)
                                return _cache_user_id(username, platform, uid)
                            break
                    break
                break
        except Exception as e:
            log.warning("[微博] 用户名解析失败 '%s': %s", username, e)

    elif platform == "eastmoney":
        try:
            import requests as req, json as _json, re as _re
            param = _json.dumps({
                "uid": "", "keyword": username,
                "type": ["passport"],
                "client": "web", "clientType": "web", "clientVersion": "curr",
                "param": {"passport": {"pageSize": 10, "pageIndex": 1,
                                       "preTag": "", "postTag": ""}},
            }, ensure_ascii=False)
            r = req.get(
                "https://search-api-web.eastmoney.com/search/jsonp",
                params={"cb": "em_cb", "param": param},
                headers={"User-Agent": USER_AGENT, "Referer": "https://so.eastmoney.com/"},
                timeout=10,
            )
            m = _re.search(r"em_cb\((.*)\)$", r.text, _re.S)
            if m:
                data = _json.loads(m.group(1))
                users_list = data.get("result", {}).get("passport", [])
                for u in users_list:
                    # alias/nickname 含 <em> 标签，需去除
                    name_clean = _re.sub(r"<[^>]+>", "", u.get("nickname", ""))
                    if name_clean == username:
                        uid = str(u.get("uid", ""))
                        log.info("[东方财富] 用户名 '%s' 解析为 ID: %s", username, uid)
                        return _cache_user_id(username, platform, uid)
                if users_list:
                    first_name = _re.sub(r"<[^>]+>", "", users_list[0].get("nickname", ""))
                    if username in first_name or first_name in username:
                        uid = str(users_list[0].get("uid", ""))
                        log.warning("[东方财富] 未精确匹配 '%s'，取近似结果: %s (%s)",
                                    username, first_name, uid)
                        return _cache_user_id(username, platform, uid)
        except Exception as e:
            log.warning("[东方财富] 用户名解析失败 '%s': %s", username, e)

    elif platform == "tgb":
        # 用 Playwright 加载淘股吧搜索页，从 HTML 中提取 blog/{id} 与用户名对应关系
        try:
            from playwright.sync_api import sync_playwright
            from playwright_stealth import Stealth
            from bs4 import BeautifulSoup as _BS
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                ctx = browser.new_context(user_agent=USER_AGENT, locale="zh-CN")
                page = ctx.new_page()
                Stealth().apply_stealth_sync(page)
                page.goto(f"https://www.tgb.cn/search?kw={username}&type=blogger",
                          timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                soup = _BS(page.content(), "html.parser")
                browser.close()

            # 提取所有 blog/{id} 链接旁的用户名，精确匹配优先
            candidates = []
            for a in soup.select('a[href*="blog/"]'):
                name = a.get_text(strip=True)
                if not name:
                    continue
                href = a.get("href", "")
                uid = href.split("blog/")[-1].split("?")[0].strip()
                if uid.isdigit():
                    candidates.append((name, uid))

            for name, uid in candidates:
                if name == username:
                    log.info("[淘股吧] 用户名 '%s' 解析为 ID: %s", username, uid)
                    return _cache_user_id(username, platform, uid)
            if candidates:
                first_name, uid = candidates[0]
                if username in first_name or first_name in username:
                    log.warning("[淘股吧] 未精确匹配 '%s'，取近似结果: %s (%s)",
                                username, first_name, uid)
                    return _cache_user_id(username, platform, uid)
        except Exception as e:
            log.warning("[淘股吧] 用户名解析失败 '%s': %s", username, e)

    log.warning("[%s] 无法解析用户名 '%s'，跳过", platform, username)
    return ""


def _cache_user_id(username: str, platform: str, uid: str) -> str:
    """将解析结果写入缓存并返回 uid，方便在 return 处内联调用。"""
    cache = _load_user_cache()
    cache.setdefault(username, {})[platform] = uid
    _save_user_cache(cache)
    return uid


# ── HTML 纯文本提取 ────────────────────────────────────────────────────────────

def strip_html(html_text: str) -> str:
    """去除 HTML 标签，保留纯文本。"""
    class _S(HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts = []
        def handle_data(self, data):
            self.parts.append(data)
    p = _S()
    p.feed(html_text or "")
    return " ".join(p.parts).strip()


# ── 平台解析器 ────────────────────────────────────────────────────────────────

def _parse_xueqiu(raw: dict) -> dict | None:
    """解析雪球 API 单条帖子。"""
    user = raw.get("user", {})
    created_ms = raw.get("created_at", 0)
    return {
        "id":            str(raw.get("id", "")),
        "user_id":       str(user.get("id", "")),
        "created_at":    datetime.fromtimestamp(created_ms / 1000).strftime("%Y-%m-%d %H:%M:%S") if created_ms else "",
        "text":          strip_html(raw.get("text", "")),
        "url":           f"https://xueqiu.com/{user.get('id','')}/{raw.get('id','')}",
        "author":        user.get("screen_name", ""),
        "like_count":    raw.get("like_count", 0),
        "reply_count":   raw.get("reply_count", 0),
        "retweet_count": raw.get("retweet_count", 0),
    }


def _parse_weibo(card: dict) -> dict | None:
    """解析微博手机版 API 单条帖子（card_type=9）。"""
    if card.get("card_type") != 9:
        return None
    mb = card.get("mblog", {})
    if not mb:
        return None
    user = mb.get("user", {})
    uid  = user.get("id", "")
    mid  = mb.get("mid", mb.get("id", ""))
    # 微博原始格式如 "Sat Mar 13 10:30:00 +0800 2026"，转为标准格式
    raw_ts = mb.get("created_at", "")
    try:
        created_at = datetime.strptime(raw_ts, "%a %b %d %H:%M:%S %z %Y").strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        created_at = raw_ts
    text = strip_html(mb.get("text", ""))
    return {
        "id":            str(mid),
        "user_id":       str(uid),
        "created_at":    created_at,
        "text":          text,
        "full_text":     text,
        "url":           f"https://weibo.com/{uid}/{mb.get('bid', mid)}",
        "author":        user.get("screen_name", ""),
        "like_count":    mb.get("attitudes_count", 0),
        "reply_count":   mb.get("comments_count", 0),
        "retweet_count": mb.get("reposts_count", 0),
    }


def _parse_tgb(raw: dict) -> dict | None:
    """解析淘股吧 HTML 提取的单条帖子。"""
    post_id = str(raw.get("id", ""))
    if not post_id:
        return None
    return {
        "id":            post_id,
        "user_id":       str(raw.get("user_id", raw.get("uid", ""))),
        "created_at":    raw.get("created_at", ""),
        "text":          raw.get("title", ""),
        "url":           raw.get("url", f"https://www.tgb.cn/a/{post_id}"),
        "author":        raw.get("author", ""),
        "like_count":    0,
        "reply_count":   raw.get("reply_count", 0),
        "retweet_count": 0,
    }


def _parse_eastmoney(raw: dict) -> dict | None:
    """解析东方财富 userPostArticles API 帖子。"""
    post_id = str(raw.get("post_id") or raw.get("id") or "")
    if not post_id:
        return None
    # 发布时间
    ts = raw.get("post_publish_time") or raw.get("time") or ""
    # 内容：优先正文，无则用标题
    text = strip_html(raw.get("post_content") or raw.get("post_title") or "")
    # 股吧代码用于拼 URL
    guba = raw.get("post_guba", {}) or {}
    code = guba.get("stockbar_code", "")
    mkt  = "SH" if guba.get("stockbar_market") == "1" else "SZ"
    url  = (f"https://guba.eastmoney.com/news,{mkt}{code},{post_id}.html"
            if code else f"https://guba.eastmoney.com/news,{post_id}.html")
    post_user = raw.get("post_user") or {}
    return {
        "id":            post_id,
        "user_id":       str(post_user.get("user_id") or raw.get("user_id") or raw.get("post_user_id") or ""),
        "created_at":    str(ts),
        "text":          text,
        "url":           url,
        "author":        post_user.get("user_nickname") or raw.get("user_nickname") or raw.get("post_user_name") or "",
        "like_count":    raw.get("post_like_count") or 0,
        "reply_count":   raw.get("post_comment_count") or 0,
        "retweet_count": raw.get("post_forward_count") or 0,
    }


def _parse_relative_time(text: str) -> str | None:
    """
    将多种中文相对/绝对时间格式解析为 'YYYY-MM-DD HH:MM:SS' 字符串。
    解析失败时返回当前时间字符串（不过滤该条目）。
    """
    now = datetime.now()
    text = text.strip()
    if not text:
        return now.strftime("%Y-%m-%d %H:%M:%S")

    # "X分钟前"
    m = re.match(r"(\d+)\s*分钟前", text)
    if m:
        return (now - timedelta(minutes=int(m.group(1)))).strftime("%Y-%m-%d %H:%M:%S")

    # "X小时前"
    m = re.match(r"(\d+)\s*小时前", text)
    if m:
        return (now - timedelta(hours=int(m.group(1)))).strftime("%Y-%m-%d %H:%M:%S")

    # "X天前"
    m = re.match(r"(\d+)\s*天前", text)
    if m:
        return (now - timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d %H:%M:%S")

    # "今天 HH:MM" 或 "今天HH:MM"
    m = re.match(r"今天\s*(\d{1,2}:\d{2})", text)
    if m:
        t = datetime.strptime(m.group(1), "%H:%M")
        return now.replace(hour=t.hour, minute=t.minute, second=0).strftime("%Y-%m-%d %H:%M:%S")

    # "昨天 HH:MM" 或 "昨天HH:MM"
    m = re.match(r"昨天\s*(\d{1,2}:\d{2})", text)
    if m:
        t = datetime.strptime(m.group(1), "%H:%M")
        yesterday = now - timedelta(days=1)
        return yesterday.replace(hour=t.hour, minute=t.minute, second=0).strftime("%Y-%m-%d %H:%M:%S")

    # "MM-DD HH:MM" 或 "MM/DD HH:MM"
    m = re.match(r"(\d{1,2})[-/](\d{1,2})\s+(\d{1,2}:\d{2})", text)
    if m:
        mo, day, hm = int(m.group(1)), int(m.group(2)), m.group(3)
        try:
            t = datetime.strptime(f"{now.year}-{mo:02d}-{day:02d} {hm}", "%Y-%m-%d %H:%M")
            return t.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass

    # "YYYY-MM-DD HH:MM:SS" 或 "YYYY-MM-DD HH:MM" 或 "YYYY-MM-DD"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
                "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass

    # 解析失败，返回当前时间（不过滤）
    log.debug("时间解析失败: %r，使用当前时间", text)
    return now.strftime("%Y-%m-%d %H:%M:%S")


def _within_days(created_at: str, cutoff: datetime) -> bool:
    """判断 created_at 字符串是否在 cutoff 之后，解析失败时返回 True（不误杀）。"""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(created_at, fmt) >= cutoff
        except ValueError:
            pass
    return True  # 解析失败保留


def _parse_qq_finance(raw: dict) -> dict | None:
    """解析腾讯财经 HTML 提取的单条新闻。"""
    title = raw.get("title", "").strip()
    url   = raw.get("url", "").strip()
    if not title or not url:
        return None
    # id：优先用完整 article_id（如 20260314A021JC00），其次 MD5
    post_id = (raw.get("article_id")
               or hashlib.md5(url.encode()).hexdigest()[:8])
    return {
        "id":            post_id,
        "created_at":    raw.get("created_at", ""),
        "text":          title,
        "url":           url,
        "author":        raw.get("author", ""),
        "like_count":    0,
        "reply_count":   0,
        "retweet_count": 0,
    }


def _parse_hexun(raw: dict) -> dict | None:
    """解析和讯网 HTML 提取的单条新闻。"""
    title = raw.get("title", "").strip()
    url   = raw.get("url", "").strip()
    if not title or not url:
        return None
    m = re.search(r"(\d{6,})", url)
    post_id = m.group(1) if m else hashlib.md5(url.encode()).hexdigest()[:8]
    return {
        "id":            post_id,
        "created_at":    raw.get("created_at", ""),
        "text":          title,
        "url":           url,
        "author":        raw.get("author", ""),
        "like_count":    0,
        "reply_count":   0,
        "retweet_count": 0,
    }


def _parse_cninfo(raw: dict, record_type: str = "announcement") -> dict | None:
    """解析巨潮资讯网单条公告或互动问答。
    record_type: "announcement"（公告）或 "interactive"（互动问答）
    pdf_url 仅保存 URL，不下载文件。
    """
    ann_id = str(raw.get("announcementId", ""))
    if not ann_id:
        return None
    adjunct = raw.get("adjunctUrl", "")
    pdf_url = f"https://static.cninfo.com.cn/{adjunct}" if adjunct else ""
    sec_code = raw.get("secCode", "")
    sec_name  = raw.get("secName", "")
    url = (f"https://www.cninfo.com.cn/new/disclosure/detail"
           f"?announcementId={ann_id}&orgId={raw.get('orgId','')}")
    ts = raw.get("announcementTime", 0)
    created_at = (datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M:%S")
                  if ts else "")
    return {
        "id":            ann_id,
        "created_at":    created_at,
        "text":          raw.get("announcementTitle", "").strip(),
        "url":           url,
        "author":        f"{sec_name}({sec_code})" if sec_code else sec_name,
        "like_count":    0,
        "reply_count":   0,
        "retweet_count": 0,
        "pdf_url":       pdf_url,       # PDF 链接，仅保存不下载
        "record_type":   record_type,   # "announcement" 或 "interactive"
    }


PARSERS = {
    "xueqiu":     _parse_xueqiu,
    "weibo":      _parse_weibo,
    "tgb":        _parse_tgb,
    "eastmoney":  _parse_eastmoney,
    "qq_finance": _parse_qq_finance,
    "hexun":      _parse_hexun,
    "cninfo":     _parse_cninfo,
}


# ── 腾讯财经 & 和讯网：playwright HTML 解析 ───────────────────────────────────

def fetch_qq_finance(target: dict, days: int = 3) -> list[dict]:
    """
    用 playwright 加载腾讯财经首页，BeautifulSoup 解析新闻列表。
    仅返回 days 天内的条目。
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    from playwright_stealth import Stealth

    url   = "https://finance.qq.com"
    posts = []
    cutoff = datetime.now() - timedelta(days=days)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=USER_AGENT,
            locale="zh-CN",
            viewport={"width": 1280, "height": 800},
        )
        page = ctx.new_page()
        Stealth().apply_stealth_sync(page)

        log.info("[腾讯财经] 正在访问 %s …", url)
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
        except PWTimeout:
            log.warning("[腾讯财经] 页面加载超时，继续解析内容")
        except Exception as e:
            log.warning("[腾讯财经] 导航异常: %s，继续解析内容", e)

        page.wait_for_timeout(5000)
        # 多次滚动以触发懒加载，每次滚动后稍等渲染
        for _ in range(6):
            page.evaluate("window.scrollBy(0, 800)")
            page.wait_for_timeout(1500)
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")

    # 实际结构：div.channel-feed-item 包含 a.article-title > span.article-title-text
    # dt-params 属性含 article_id=YYYYMMDD... 可提取日期
    items = (soup.select("div.channel-feed-item") or
             soup.select("div.channel-hot-item") or
             soup.select("li.item"))

    for item in items:
        # 标题链接
        a = item.select_one("a.article-title, a[href]")
        if not a:
            continue
        href = a.get("href", "")
        # 过滤无效链接
        if not href or href.startswith("javascript"):
            continue
        title_el = item.select_one("span.article-title-text") or a
        title = title_el.get_text(strip=True)
        if not title or len(title) < 4:
            continue

        # 从 dt-params 提取完整 article_id（如 20260314A021JC00）
        article_id = ""
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dt_params = item.get("dt-params", "")
        # article_type=4 是视频，无正文可抓，跳过
        if "article_type=4" in dt_params:
            continue
        m = re.search(r"article_id=([A-Za-z0-9]+)", dt_params)
        if m:
            article_id = m.group(1)
            # 前 8 位是日期 YYYYMMDD
            try:
                created_at = datetime.strptime(article_id[:8], "%Y%m%d").strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass
        else:
            # 备用：从 href 中提取日期段
            m2 = re.search(r"/(\d{8})[A-Z]", href)
            if m2:
                try:
                    created_at = datetime.strptime(m2.group(1), "%Y%m%d").strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass

        # 3 天过滤
        try:
            if datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S") < cutoff:
                continue
        except ValueError:
            pass

        raw = {"title": title, "url": href, "created_at": created_at, "author": "", "article_id": article_id}
        parsed = _parse_qq_finance(raw)
        if parsed:
            posts.append(parsed)

    log.info("[腾讯财经] 共解析 %d 条新闻", len(posts))
    return posts


def fetch_hexun(target: dict, days: int = 3) -> list[dict]:
    """
    用 playwright 加载和讯网股票频道页，BeautifulSoup 解析新闻列表。
    仅返回 days 天内的条目。
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    from playwright_stealth import Stealth

    url   = "https://stock.hexun.com"
    posts = []
    cutoff = datetime.now() - timedelta(days=days)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=USER_AGENT,
            locale="zh-CN",
            viewport={"width": 1280, "height": 800},
        )
        page = ctx.new_page()
        Stealth().apply_stealth_sync(page)

        log.info("[和讯网] 正在访问 %s …", url)
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
        except PWTimeout:
            log.warning("[和讯网] 页面加载超时，继续解析内容")
        except Exception as e:
            log.warning("[和讯网] 导航异常: %s，继续解析内容", e)

        page.wait_for_timeout(5000)
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")

    # 实际结构：ul.newsList > li > a，URL 含日期路径 /YYYY-MM-DD/
    items = (soup.select("ul.newsList li") or
             soup.select("div.leftContent li") or
             soup.select("ul.txt-list li") or
             soup.select("div.list li"))

    for item in items:
        a = item.select_one("a[href*='hexun.com'], a[href]")
        if not a:
            continue
        href  = a.get("href", "")
        # 只保留 hexun.com 且含日期路径的正文页，过滤直播/推广/旧视频链接
        if "hexun.com" not in href or not re.search(r"/\d{4}-\d{2}-\d{2}/", href):
            continue
        title = a.get("title") or a.get_text(strip=True)
        if not title or len(title) < 4:
            continue

        # 优先从 URL 路径提取日期（/2026-03-13/）
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        m = re.search(r"/(\d{4}-\d{2}-\d{2})/", href)
        if m:
            try:
                created_at = datetime.strptime(m.group(1), "%Y-%m-%d").strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass
        else:
            time_el = item.select_one("span.time, span.date, em.time, em.date")
            time_text = time_el.get_text(strip=True) if time_el else ""
            created_at = _parse_relative_time(time_text)

        try:
            if datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S") < cutoff:
                continue
        except ValueError:
            pass

        raw = {"title": title, "url": href, "created_at": created_at, "author": ""}
        parsed = _parse_hexun(raw)
        if parsed:
            posts.append(parsed)

    log.info("[和讯网] 共解析 %d 条新闻", len(posts))
    return posts


# ── 通用响应拦截逻辑 ───────────────────────────────────────────────────────────

def _make_response_handler(platform: str, results: list):
    """根据平台返回对应的 playwright 响应回调。"""

    def _xueqiu(response):
        if "user_timeline" not in response.url:
            return
        try:
            data = response.json()
            for raw in data.get("statuses", []):
                p = _parse_xueqiu(raw)
                if p:
                    results.append(p)
            log.info("[雪球] 拦截到 %d 条帖子", len(data.get("statuses", [])))
        except Exception as e:
            log.warning("[雪球] 解析响应失败: %s", e)

    def _weibo(response):
        if "containerid=107603" not in response.url:
            return
        try:
            data = response.json()
            cards = data.get("data", {}).get("cards", [])
            for card in cards:
                p = _parse_weibo(card)
                if p:
                    results.append(p)
            log.info("[微博] 拦截到 %d 个 cards，解析 %d 条帖子", len(cards), len(results))
        except Exception as e:
            log.warning("[微博] 解析响应失败: %s", e)

    def _tgb(response):
        ct = response.headers.get("content-type", "")
        if "json" not in ct or "tgb.cn" not in response.url:
            return
        try:
            data = response.json()
            dto = data.get("dto", {})
            # 兼容列表或分页对象
            items = dto if isinstance(dto, list) else dto.get("list") or dto.get("data") or []
            for raw in items:
                if isinstance(raw, dict) and (raw.get("postID") or raw.get("title")):
                    p = _parse_tgb(raw)
                    if p:
                        results.append(p)
        except Exception:
            pass

    def _eastmoney(response):
        ct = response.headers.get("content-type", "")
        if "json" not in ct or "eastmoney.com" not in response.url:
            return
        try:
            data = response.json()
            # 尝试多种返回格式
            items = (data.get("result", {}).get("list")
                     or data.get("data", {}).get("list")
                     or data.get("list")
                     or [])
            for raw in items:
                if isinstance(raw, dict):
                    p = _parse_eastmoney(raw)
                    if p:
                        results.append(p)
        except Exception:
            pass

    return {"xueqiu": _xueqiu, "weibo": _weibo, "tgb": _tgb, "eastmoney": _eastmoney}[platform]


# ── 东方财富：纯 HTTP 抓取（无需浏览器）────────────────────────────────────────

def fetch_eastmoney(uids: list[str], days: int = DEFAULT_DAYS) -> list[dict]:
    """
    直接调用东方财富内部 API，无需登录也无需浏览器。
    API：/api/guba/userPostArticles
    支持多个 UID，按时间过滤，最多翻 10 页。
    """
    import requests as req

    api = "https://i.eastmoney.com/api/guba/userPostArticles"
    cutoff = datetime.now() - timedelta(days=days)
    posts = []

    for uid in uids:
        headers = {
            "User-Agent": USER_AGENT,
            "Referer": f"https://i.eastmoney.com/{uid}",
        }

        for page in range(1, 6):  # 安全上限 5 页
            last_err = None
            body = None
            for attempt in range(3):  # 最多重试 3 次
                try:
                    r = req.get(api, params={"uid": uid, "page": page, "pagesize": 20},
                                headers=headers, timeout=8)
                    r.raise_for_status()
                    body = r.json()
                    last_err = None
                    break
                except Exception as e:
                    last_err = e
                    if attempt < 2:
                        time.sleep(2 ** attempt)  # 1s, 2s
            if last_err is not None:
                log.error("[东方财富-%s] 第 %d 页请求失败（已重试3次）: %s", uid, page, last_err)
                break
            items = body.get("re", []) if isinstance(body, dict) else body
            if not items:
                break
            page_posts = []
            all_expired = True
            for raw in items:
                p = _parse_eastmoney(raw)
                if not p:
                    continue
                if _within_days(p["created_at"], cutoff):
                    page_posts.append(p)
                    all_expired = False
            posts.extend(page_posts)
            log.info("[东方财富-%s] 第 %d 页获取 %d 条（窗口内 %d 条）", uid, page, len(items), len(page_posts))
            if all_expired:
                break
            time.sleep(0.5)
    return posts


# ── 巨潮资讯：纯 HTTP 抓取（无需浏览器）──────────────────────────────────────

def fetch_cninfo(target: dict, days: int = DEFAULT_DAYS) -> list[dict]:
    """
    调用巨潮资讯 POST API，获取最近 days 天的公告（含 pdf_url，不下载）。
    必须在 target["stocks"] 中指定股票列表，不支持全市场抓取。
    API: POST https://www.cninfo.com.cn/new/hisAnnouncement/query
    注：巨潮互动问答位于独立的深交所互动易系统，无公开 JSON API，暂不支持抓取。
    """
    import requests as req

    api = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": "https://www.cninfo.com.cn/new/index",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    cutoff   = datetime.now() - timedelta(days=days)
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = cutoff.strftime("%Y-%m-%d")

    stocks   = target.get("stocks", [])     # 必须非空，否则由 _crawl_target 提前跳过

    posts = []

    # 将用户输入的股票代码（如 "000001,SZ" 或 "000001"）转换为巨潮格式 "000001,orgId"
    def _resolve_stock(code: str) -> str:
        """查询巨潮 topSearch 接口，返回 "secCode,orgId" 格式。"""
        sec_code = code.split(",")[0].strip()
        try:
            r = req.post(
                "https://www.cninfo.com.cn/new/information/topSearch/query",
                data={"keyWord": sec_code, "maxNum": 1},
                headers=headers,
                timeout=10,
            )
            results = r.json()
            if results:
                return f"{results[0]['code']},{results[0]['orgId']}"
        except Exception as e:
            log.warning("[巨潮资讯] 股票代码解析失败 %s: %s", code, e)
        return sec_code

    if stocks:
        stocks = [_resolve_stock(s) for s in stocks]
        log.info("[巨潮资讯] 解析后股票代码: %s", stocks)

    # 指定股票时按股票循环；stocks 为空时不应走到这里（_crawl_target 会提前拦截）
    if stocks:
        iter_items = [("", s) for s in stocks]   # (column, stock)
    else:
        iter_items = []  # 安全兜底，不应执行

    # 分别抓公告和互动问答
    for tab, rtype in [("fulltext", "announcement")]:
        for column, stock in iter_items:
            for page in range(1, 51):   # 安全上限 50 页
                data = {
                    "pageNum":    str(page),
                    "pageSize":   "30",
                    "tabName":    tab,
                    "column":     column,
                    "stock":      stock,
                    "category":   "",
                    "plate":      "",
                    "seDate":     f"{start_date}~{end_date}",
                    "searchkey":  "",
                    "secid":      "",
                    "trade":      "",
                    "sortName":   "time",
                    "sortType":   "desc",
                    "isHLtitle":  "true",
                }
                try:
                    r = req.post(api, data=data, headers=headers, timeout=15)
                    r.raise_for_status()
                    items = r.json().get("announcements") or []
                    if not items:
                        break
                    for raw in items:
                        p = _parse_cninfo(raw, record_type=rtype)
                        if p and _within_days(p["created_at"], cutoff):
                            posts.append(p)
                    label = stock or column
                    log.info("[巨潮资讯-%s][%s] 第 %d 页 %d 条", label, tab, page, len(items))
                    # 若本页最后一条已超出时间窗口，后续页更早，可提前退出
                    if items:
                        last_time = str(items[-1].get("announcementTime", ""))
                        if last_time and not _within_days(last_time, cutoff):
                            break
                    time.sleep(0.5)
                except Exception as e:
                    log.error("[巨潮资讯] 请求失败: %s", e)
                    break

    log.info("[巨潮资讯] 共获取 %d 条公告", len(posts))
    return posts


# ── 股票讨论抓取 ──────────────────────────────────────────────────────────────

def fetch_stock_eastmoney(stock_code: str, stock_name: str, days: int = DEFAULT_DAYS, *,
                          _browser=None) -> list[dict]:
    """
    抓取东方财富股吧机构号热门帖子（热门→机构 tab）。
    通过 Playwright 拦截 HighQuality_Articlelist JSONP 接口获取数据。
    直接使用接口返回的 post_content 作为正文，无需再抓文章页。
    stock_code: 纯数字代码，如 "600519"
    _browser: 可选的已有 Playwright Browser 实例，传入时复用，不传时自行启动。
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    from playwright_stealth import Stealth
    import re as _re

    url = f"https://guba.eastmoney.com/list,{stock_code},99,j.html"
    cutoff = datetime.now() - timedelta(days=days)
    posts = []
    captured: list[dict] = []

    def _on_response(response):
        if "HighQuality_Articlelist" not in response.url:
            return
        try:
            text = response.text()
            m = _re.search(r"quality_content\((\{.+\})\)", text, _re.DOTALL)
            if m:
                captured.append(json.loads(m.group(1)))
        except Exception:
            pass

    def _run(browser):
        ctx = browser.new_context(user_agent=USER_AGENT, locale="zh-CN",
                                  viewport={"width": 1280, "height": 800})
        page = ctx.new_page()
        page.on("response", _on_response)
        Stealth().apply_stealth_sync(page)
        log.info("[东方财富股吧-%s] 正在访问 %s …", stock_name, url)
        try:
            with page.expect_response(
                lambda r: "HighQuality_Articlelist" in r.url, timeout=25000
            ):
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
        except PWTimeout:
            log.warning("[东方财富股吧-%s] 加载超时，继续解析", stock_name)
        except Exception as e:
            log.warning("[东方财富股吧-%s] 导航异常: %s", stock_name, e)
        ctx.close()

    if _browser is not None:
        _run(_browser)
    else:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            _run(browser)
            browser.close()

    if not captured:
        log.warning("[东方财富股吧-%s] 未捕获到机构号数据", stock_name)
        return posts

    for raw in captured[0].get("re", []):
        try:
            created_at = str(raw.get("post_publish_time", ""))
            if not _within_days(created_at, cutoff):
                continue
            post_id = str(raw.get("post_id", ""))
            user = raw.get("post_user", {})
            guba = raw.get("post_guba", {})
            code = guba.get("stockbar_code", stock_code) if guba else stock_code
            # 过滤掉非本股票的帖子（机构可能发其他股票帖）
            if code not in (stock_code, f"SH{stock_code}", f"SZ{stock_code}"):
                # 仅保留正文中含股票名或代码的帖子
                content = raw.get("post_content", "") + raw.get("post_title", "")
                if stock_code not in content and stock_name not in content:
                    continue
            posts.append({
                "id":            post_id,
                "user_id":       str(user.get("user_id", "")),
                "created_at":    created_at,
                "text":          raw.get("post_title", ""),
                "full_text":     raw.get("post_content", ""),
                "url":           f"https://guba.eastmoney.com/news,{stock_code},{post_id}.html",
                "author":        user.get("user_nickname", ""),
                "like_count":    int(raw.get("post_like_count", 0) or 0),
                "reply_count":   int(raw.get("post_comment_count", 0) or 0),
                "retweet_count": int(raw.get("post_forward_count", 0) or 0),
                "stock":         stock_name,
            })
        except Exception:
            continue

    log.info("[东方财富股吧-%s] 共获取 %d 条机构号帖子", stock_name, len(posts))
    return posts


def fetch_stock_xueqiu(stock_code: str, stock_name: str, days: int = DEFAULT_DAYS, *,
                       _browser=None) -> list[dict]:
    """
    抓取雪球股票页热帖（symbol/search/status.json?sort=hot）。
    通过 Playwright 拦截 API 响应获取数据，直接使用 description 字段作为正文。
    stock_code: 带交易所前缀，如 "SH600519" 或 "SZ000001"
    _browser: 可选的已有 Playwright Browser 实例。
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    from playwright_stealth import Stealth

    cutoff = datetime.now() - timedelta(days=days)
    found = []

    def _run(browser):
        ctx = browser.new_context(user_agent=USER_AGENT, locale="zh-CN")
        page = ctx.new_page()
        Stealth().apply_stealth_sync(page)

        def _on_resp(response):
            if "symbol/search/status.json" in response.url and "sort=alpha" in response.url:
                try:
                    found.append(response.json())
                except Exception:
                    pass
        page.on("response", _on_resp)

        stock_url = f"https://xueqiu.com/S/{stock_code}"
        log.info("[雪球-%s] 正在访问 %s …", stock_name, stock_url)
        try:
            page.goto(stock_url, timeout=20000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            # 关闭可能出现的弹窗，点击热帖 tab（sort=alpha）
            try:
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)
                page.evaluate("document.querySelectorAll('.dimmer, .modal').forEach(el => el.remove())")
                page.wait_for_timeout(200)
                with page.expect_response(
                    lambda r: "symbol/search/status.json" in r.url and "sort=alpha" in r.url,
                    timeout=6000
                ):
                    page.click("text=热帖", force=True)
            except Exception:
                pass
        except PWTimeout:
            log.warning("[雪球-%s] 加载超时", stock_name)
        except Exception as e:
            log.warning("[雪球-%s] 导航异常: %s", stock_name, e)
        ctx.close()

    if _browser is not None:
        _run(_browser)
    else:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            _run(browser)
            browser.close()

    posts = []
    for result in found:
        for raw in result.get("list", []):
            try:
                created_ms = raw.get("created_at", 0)
                created_at = datetime.fromtimestamp(created_ms / 1000).strftime("%Y-%m-%d %H:%M:%S") if created_ms else ""
                if not _within_days(created_at, cutoff):
                    continue
                user = raw.get("user", {})
                uid = str(user.get("id", ""))
                pid = str(raw.get("id", ""))
                full_text = strip_html(raw.get("text") or raw.get("description", ""))
                posts.append({
                    "id":            pid,
                    "user_id":       uid,
                    "created_at":    created_at,
                    "text":          full_text[:100],
                    "full_text":     full_text,
                    "url":           f"https://xueqiu.com/{uid}/{pid}",
                    "author":        user.get("screen_name", ""),
                    "like_count":    raw.get("like_count", 0),
                    "reply_count":   raw.get("reply_count", 0),
                    "retweet_count": raw.get("retweet_count", 0),
                    "stock":         stock_name,
                })
            except Exception:
                continue

    log.info("[雪球-%s] 共获取 %d 条热帖", stock_name, len(posts))
    return posts


def fetch_stock_weibo(stock_name: str, days: int = DEFAULT_DAYS, *,
                      _browser=None) -> list[dict]:
    """
    通过 Playwright 抓取微博上关于指定股票的热门讨论（type=60 热门搜索）。
    _browser: 可选的已有 Playwright Browser 实例。
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    from playwright_stealth import Stealth

    cutoff = datetime.now() - timedelta(days=days)
    found = []

    def _run(browser):
        ctx = browser.new_context(user_agent=USER_AGENT, locale="zh-CN")
        page = ctx.new_page()
        Stealth().apply_stealth_sync(page)

        def _on_resp(response):
            if "api/container/getIndex" in response.url and "containerid=100103type%3D60" in response.url:
                try:
                    found.append(response.json())
                except Exception:
                    pass
        page.on("response", _on_resp)

        search_url = f"https://m.weibo.cn/search?containerid=100103type%3D60%26q%3D{stock_name}&page_type=searchall"
        log.info("[微博-%s] 正在访问 %s …", stock_name, search_url)
        try:
            with page.expect_response(
                lambda r: "api/container/getIndex" in r.url and "containerid=100103type%3D60" in r.url,
                timeout=15000
            ):
                page.goto(search_url, timeout=20000, wait_until="domcontentloaded")
        except PWTimeout:
            log.warning("[微博-%s] 加载超时", stock_name)
        except Exception as e:
            log.warning("[微博-%s] 导航异常: %s", stock_name, e)
        ctx.close()

    if _browser is not None:
        _run(_browser)
    else:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            _run(browser)
            browser.close()

    posts = []
    for result in found:
        cards = result.get("data", {}).get("cards", [])
        for card in cards:
            p = _parse_weibo(card)
            if p and _within_days(p.get("created_at", ""), cutoff):
                p["stock"] = stock_name
                posts.append(p)

    log.info("[微博-%s] 共获取 %d 条帖子", stock_name, len(posts))
    return posts


def fetch_stock_hexun(stock_code: str, stock_name: str, days: int = DEFAULT_DAYS) -> list[dict]:
    """
    抓取和讯网股票公司新闻页，返回指定天数内的新闻列表。
    URL: https://stock.hexun.com/{code}/gongsixinwen/
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    from playwright_stealth import Stealth

    cutoff = datetime.now() - timedelta(days=days)
    url = f"https://stock.hexun.com/{stock_code}/gongsixinwen/"
    log.info("[和讯网-%s] 正在访问 %s …", stock_name, url)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=USER_AGENT, locale="zh-CN",
            viewport={"width": 1280, "height": 800},
        )
        page = ctx.new_page()
        Stealth().apply_stealth_sync(page)
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
        except PWTimeout:
            log.warning("[和讯网-%s] 页面加载超时，继续解析", stock_name)
        except Exception as e:
            log.warning("[和讯网-%s] 导航异常: %s", stock_name, e)
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")
    posts = []

    for ul in soup.find_all("ul"):
        news_links = ul.find_all(
            "a", href=lambda h: h and re.search(r"/20\d\d-\d\d-\d\d/", h)
        )
        if len(news_links) < 3:
            continue
        for a in news_links:
            href = a.get("href", "")
            title = a.get_text(strip=True)
            if not title or not href:
                continue
            # 从 URL 路径解析日期 /2026-03-17/
            m = re.search(r"/(\d{4}-\d{2}-\d{2})/", href)
            created_at = m.group(1) if m else ""
            if created_at and not _within_days(created_at, cutoff):
                continue
            post_id = href.rstrip("/").split("/")[-1]
            posts.append({
                "id":            post_id,
                "user_id":       "",
                "created_at":    created_at,
                "text":          title,
                "url":           href,
                "author":        "",
                "like_count":    0,
                "reply_count":   0,
                "retweet_count": 0,
                "stock":         stock_name,
            })
        break  # 只取第一个匹配的 ul

    log.info("[和讯网-%s] 共获取 %d 条新闻", stock_name, len(posts))
    return posts


def fetch_stock_tgb(stock_code: str, stock_name: str, days: int = DEFAULT_DAYS, *,
                    _browser=None) -> list[dict]:
    """
    通过 Playwright 访问淘股吧股票行情页（quotes/sh{code}），解析 HTML 帖子列表。
    stock_code: 带交易所前缀的小写代码，如 "sh600519" 或 "sz300394"
    _browser: 可选的已有 Playwright Browser 实例。
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    from playwright_stealth import Stealth
    import re as _re

    cutoff = datetime.now() - timedelta(days=days)
    url = f"https://www.tgb.cn/quotes/{stock_code.lower()}"
    log.info("[淘股吧-%s] 正在访问 %s …", stock_name, url)
    html = ""

    def _run(browser):
        nonlocal html
        ctx = browser.new_context(
            user_agent=USER_AGENT,
            locale="zh-CN",
            viewport={"width": 1280, "height": 800},
        )
        page = ctx.new_page()
        Stealth().apply_stealth_sync(page)
        try:
            page.goto(url, timeout=35000, wait_until="commit")
            try:
                page.wait_for_selector("div.stock-right", timeout=15000)
            except Exception:
                page.wait_for_timeout(5000)
        except PWTimeout:
            log.warning("[淘股吧-%s] 页面加载超时，继续解析", stock_name)
        except Exception as e:
            log.warning("[淘股吧-%s] 导航异常: %s", stock_name, e)
        html = page.content()
        ctx.close()

    if _browser is not None:
        _run(_browser)
    else:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            _run(browser)
            browser.close()

    soup = BeautifulSoup(html, "html.parser")
    posts = []

    for block in soup.find_all("div", class_=lambda c: c and "stock-right" in c):
        try:
            # 用户信息
            user_a = block.select_one("div.user-name a")
            author = user_a.get_text(strip=True) if user_a else ""
            user_href = user_a.get("href", "") if user_a else ""
            uid_m = _re.search(r"/blog/(\d+)", user_href)
            uid = uid_m.group(1) if uid_m else ""

            # 时间
            rs = block.select_one("div.related-sources")
            rs_text = rs.get_text(strip=True) if rs else ""
            # 格式："2026-03-17 21:34  跟帖回复"
            date_m = _re.match(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})", rs_text)
            created_at = date_m.group(1).replace("  ", " ") if date_m else ""
            if not _within_days(created_at, cutoff):
                continue

            # 主帖：有 related-subject，跟帖：只有 subInfo
            subj_a = block.select_one("div.related-subject a")
            body_a = block.select_one("a.related-body")

            if subj_a:
                # 主帖
                title = subj_a.get_text(strip=True)
                href = subj_a.get("href", "")
                # 帖子 ID 从 gioMsg_T_{id} div 的 id 属性提取
                gio = block.select_one("div[id^='gioMsg_T_']")
                post_id = gio.get("id", "").replace("gioMsg_T_", "") if gio else href.split("/a/")[-1].split("#")[0]
                text = ""
                if body_a:
                    text = strip_html(body_a.get_text(strip=True))
            elif body_a:
                # 跟帖回复
                href = body_a.get("href", "")
                title = ""
                # URL 格式 /a/{topicID}/{commentID}
                parts = href.rstrip("/").split("/a/")[-1].split("/")
                post_id = parts[-1].split("#")[0] if parts else ""
                text = strip_html(body_a.get_text(strip=True))
            else:
                continue

            if not href.startswith("http"):
                href = "https://www.tgb.cn/" + href.lstrip("/")
            if not post_id:
                continue

            # 统计
            praise_el = block.select_one("span.praise-num, em.praise-num")
            view_el   = block.select_one("span.view-num, em.view-num")
            comment_el= block.select_one("span.comment-num, em.comment-num")
            like_count    = int(praise_el.get_text(strip=True) or 0) if praise_el else 0
            view_count    = int(view_el.get_text(strip=True)   or 0) if view_el   else 0
            reply_count   = int(comment_el.get_text(strip=True)or 0) if comment_el else 0

            posts.append({
                "id":            post_id,
                "user_id":       uid,
                "created_at":    created_at,
                "text":          (title or text)[:100],
                "full_text":     title + ("\n" + text if text else ""),
                "url":           href,
                "author":        author,
                "like_count":    like_count,
                "reply_count":   reply_count,
                "retweet_count": 0,
                "view_count":    view_count,
                "stock":         stock_name,
            })
        except Exception:
            continue

    log.info("[淘股吧-%s] 共获取 %d 条帖子", stock_name, len(posts))
    return posts


# ── 淘股吧：playwright HTML 解析（无需登录）──────────────────────────────────

def fetch_tgb(target: dict, days: int = DEFAULT_DAYS) -> list[dict]:
    """
    用 playwright-stealth 加载淘股吧博客页面，解析 HTML 中的帖子列表。
    支持多个博主 URL，在同一个浏览器会话内依次抓取。
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    from playwright_stealth import Stealth

    urls  = [_URL_TEMPLATES["tgb"].format(uid=uid) for uid in target["user_ids"]]
    posts = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=USER_AGENT,
            locale="zh-CN",
            viewport={"width": 1280, "height": 800},
        )
        page = ctx.new_page()
        Stealth().apply_stealth_sync(page)

        for url in urls:
            log.info("[淘股吧] 正在访问 %s …", url)
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
            except PWTimeout:
                log.warning("[淘股吧] 页面加载超时，继续解析内容")
            except Exception as e:
                log.warning("[淘股吧] 导航异常: %s，继续解析内容", e)

            page.wait_for_timeout(5000)
            html = page.content()

            soup = BeautifulSoup(html, "html.parser")
            for block in soup.select("div.article_tittle"):
                a = block.select_one("a[href^='a/']")
                if not a:
                    continue
                short_path  = a["href"]
                title       = a.get("title", a.get_text()).strip()
                post_id     = short_path.split("/")[-1]
                full_url    = f"https://www.tgb.cn/{short_path}"

                stats = block.select_one(".tittle_llhf")
                reply_count = 0
                if stats:
                    parts = stats.get_text(strip=True).split("/")
                    reply_count = int(parts[1]) if len(parts) == 2 and parts[1].isdigit() else 0

                date_el    = block.select_one(".tittle_fbshijian")
                created_at = date_el.get_text(strip=True) if date_el else ""

                posts.append({
                    "id":          post_id,
                    "created_at":  created_at,
                    "title":       title,
                    "url":         full_url,
                    "author":      "",
                    "reply_count": reply_count,
                })

        browser.close()

    log.info("[淘股吧] 共解析 %d 条帖子", len(posts))
    cutoff = datetime.now() - timedelta(days=days)
    result = []
    for r in posts:
        if not r:
            continue
        parsed_time = _parse_relative_time(r.get("created_at", ""))
        if _within_days(parsed_time, cutoff):
            parsed = _parse_tgb(r)
            if parsed:
                parsed["created_at"] = parsed_time
                result.append(parsed)
    return result


# ── playwright 抓取核心 ────────────────────────────────────────────────────────

def fetch_platform(target: dict) -> list[dict]:
    """用 playwright-stealth 无头浏览器抓取单个平台的帖子。"""
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    from playwright_stealth import Stealth

    name     = target["name"]
    platform = target["platform"]
    urls     = [_URL_TEMPLATES[platform].format(uid=uid) for uid in target["user_ids"]]
    cookie_file = target.get("cookie_file")

    # 检查需要 Cookie 的平台是否已配置
    if cookie_file and not Path(cookie_file).exists():
        log.warning("[%s] 需要登录 Cookie，但未找到 %s，跳过", name, cookie_file)
        log.warning("[%s] 请在浏览器登录后，将 Cookie 复制到 %s", name, cookie_file)
        return []

    cookies = {}
    if cookie_file and Path(cookie_file).exists():
        cookies = json.loads(Path(cookie_file).read_text(encoding="utf-8"))
        log.info("[%s] 已加载 Cookie（%d 个）", name, len(cookies))

    results = []
    handler = _make_response_handler(platform, results)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=USER_AGENT,
            locale="zh-CN",
            viewport={"width": 1280, "height": 800},
        )
        if cookies:
            domain = urls[0].split("/")[2]
            ctx.add_cookies([
                {"name": k, "value": v, "domain": f".{domain}", "path": "/"}
                for k, v in cookies.items()
            ])

        page = ctx.new_page()
        Stealth().apply_stealth_sync(page)
        page.on("response", handler)

        _VERIFY_KEYWORDS = ("人机验证", "滑动验证", "请完成验证", "访问验证", "security check",
                            "please verify", "captcha", "robot check")

        for url in urls:
            log.info("[%s] 正在访问 %s …", name, url)
            before_count = len(results)
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
            except PWTimeout:
                log.warning("[%s] 页面加载超时，继续等待内容", name)
            except Exception as e:
                log.warning("[%s] 导航异常: %s，继续等待内容", name, e)

            page.wait_for_timeout(6000)

            # 微博需要额外等待 containerid 加载
            if platform == "weibo" and not results:
                page.evaluate("window.scrollTo(0, 300)")
                page.wait_for_timeout(3000)

            # 检查是否命中验证码/人机验证（API 未触发时才检查）
            if len(results) == before_count:
                try:
                    body_text = page.inner_text("body").lower()
                    cur_url = page.url
                    if any(kw in body_text for kw in _VERIFY_KEYWORDS):
                        log.warning("[%s] 检测到访问验证页面（当前 URL: %s），本博主帖子跳过。"
                                    "建议配置 Cookie 或更换 IP 后重试。", name, cur_url)
                    else:
                        log.warning("[%s] 未获取到帖子（API 无响应），URL: %s", name, cur_url)
                except Exception:
                    pass

        browser.close()

    log.info("[%s] 共获取 %d 条帖子", name, len(results))
    return results


# ── 去重 & 保存 ───────────────────────────────────────────────────────────────

def _clear_output_dir() -> None:
    """清空输出目录下所有抓取数据，保留 user_cache.json（用户名缓存）。"""
    if not OUTPUT_DIR.exists():
        return
    # 备份 user_cache
    cache_data = None
    if _USER_CACHE_PATH.exists():
        cache_data = _USER_CACHE_PATH.read_bytes()
    shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)
    if cache_data is not None:
        _USER_CACHE_PATH.write_bytes(cache_data)
    log.info("已清空输出目录: %s", OUTPUT_DIR)


def cleanup_expired(days: int) -> None:
    """
    删除超出时间窗口的过期数据，保留 days 天内的所有记录和文章文件。

    清理内容：
    1. 每个平台目录下日期超出范围的 YYYY-MM-DD.json 文件
    2. 对应 articles/ 目录下已不被任何有效 JSON 引用的文章文件
    """
    if not OUTPUT_DIR.exists():
        return

    # 以日期为粒度：保留最近 days 天（含今天），更早的全部删除
    # cutoff_date = 今天00:00 往前推 (days-1) 天，即保留窗口的最早一天
    today_midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    cutoff_date = today_midnight - timedelta(days=days - 1)

    for platform_dir in OUTPUT_DIR.iterdir():
        if not platform_dir.is_dir():
            continue
        platform = platform_dir.name

        # 1. 找出所有日期 JSON，区分有效/过期
        valid_ids: set[str] = set()
        expired_jsons: list[Path] = []

        for json_file in sorted(platform_dir.glob("????-??-??.json")):
            try:
                file_date = datetime.strptime(json_file.stem, "%Y-%m-%d")
            except ValueError:
                continue
            if file_date < cutoff_date:
                expired_jsons.append(json_file)
            else:
                # 收集有效窗口内所有帖子的 ID
                try:
                    posts = json.loads(json_file.read_text(encoding="utf-8"))
                    for p in posts:
                        pid = p.get("id")
                        if pid:
                            valid_ids.add(str(pid))
                except Exception:
                    pass

        # 2. 删除过期 JSON
        for f in expired_jsons:
            f.unlink()
            log.info("[cleanup][%s] 删除过期记录文件: %s", platform, f.name)

        # 3. 删除 articles/ 中不被有效 JSON 引用的文章文件
        articles_dir = platform_dir / "articles"
        if articles_dir.exists():
            for item in articles_dir.iterdir():
                if item.is_file():
                    # 直接在 articles/ 下的文件（cninfo PDF 或旧格式）
                    if item.stem not in valid_ids:
                        item.unlink()
                        log.info("[cleanup][%s] 删除过期文章: %s", platform, item.name)
                elif item.is_dir():
                    # articles/{user_id}/ 子目录
                    for art_file in item.iterdir():
                        if art_file.is_file() and art_file.stem not in valid_ids:
                            art_file.unlink()
                            log.info("[cleanup][%s] 删除过期文章: %s/%s",
                                     platform, item.name, art_file.name)
                    # 删除空子目录
                    if not any(item.iterdir()):
                        item.rmdir()
                        log.info("[cleanup][%s] 删除空目录: articles/%s", platform, item.name)


def save_posts(posts: list[dict], platform: str, date_str: str) -> None:
    platform_dir = OUTPUT_DIR / platform
    platform_dir.mkdir(parents=True, exist_ok=True)
    out_file = platform_dir / f"{date_str}.json"

    existing = []
    if out_file.exists():
        existing = json.loads(out_file.read_text(encoding="utf-8"))

    existing.extend(posts)
    out_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("[%s] 已写入 %s（共 %d 条）", platform, out_file, len(existing))


# ── 文章正文清洗 ──────────────────────────────────────────────────────────────

# 遇到这些行时截断（后面全是页脚/无关内容）
_STOP_PATTERNS = [
    r"^【免责声明】",
    r"^本站郑重声明",
    r"^举报/投诉",
    r"^Copyright[©®]",
    r"^京ICP",
    r"^本文仅代表作者",
]

# 单独过滤掉（不截断，继续处理后续行）
_SKIP_PATTERNS = [
    r"^（责任编辑[：:]",
    r"^\s*看全文\s*$",
    r"^\s*举报\s*$",
    r"^\s*写评论\s*$",
    r"^\s*已有\d*条评论\s*$",
    r"^\s*还可输入\d*字\s*$",
    r"^\s*查看剩下\d*条评论\s*$",
    r"^\s*跟帖用户自律公约\s*$",
    r"^\s*提\s*交\s*$",
    r"^\s*最新评论\s*$",
    r"^\s*相关推荐.*$",
    r"^\s*热门阅读\s*$",
    r"^\s*财道头条.*$",
    r"^\s*和讯特稿\s*$",
    r"^\s*关注\s*$",
]


def _clean_article_text(content: str) -> str:
    """去除文章正文中的导航、页脚、免责声明、评论区等杂项内容。"""
    lines = content.splitlines()
    cleaned = []
    for line in lines:
        if any(re.search(p, line) for p in _STOP_PATTERNS):
            break
        if any(re.match(p, line) for p in _SKIP_PATTERNS):
            continue
        cleaned.append(line)
    # 合并连续空行
    result = re.sub(r"\n{3,}", "\n\n", "\n".join(cleaned))
    return result.strip()


# ── 文章详情抓取 ──────────────────────────────────────────────────────────────

# 各平台文章正文 CSS 选择器（按优先级排列，匹配即止）
_ARTICLE_SELECTORS = {
    "xueqiu":          ["div.article__bd__detail", "div.article__bd"],
    "weibo":           [".weibo-text", "article.weibo-main"],
    "tgb":             [".p_coten", "div.article-text", "div.artMain",
                        "div#postContent", "div.article-content"],
    "eastmoney":       ["div.newstext", "div.newsPage", "div.content"],
    "eastmoney_guba":  ["div.newstext", "div.newsPage", "div.content"],
    "qq_finance":      ["div.content-article", "div.qq_article_tag", "div#Main"],
    "hexun":           ["div.art_context", "div.art_contextBox", "div#artibody"],
}


def _fetch_article_batch(posts: list[dict], platform: str, articles_dir: Path) -> None:
    """在单个 playwright 会话中批量抓取文章正文，写入 articles_dir/{user_id}/{post_id}.txt。
    若 post 无 user_id，则退回到 articles_dir/{post_id}.txt（向后兼容）。
    _browser: 可选的已有 Playwright Browser 实例，传入时复用，不传时自行启动。
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    from playwright_stealth import Stealth

    selectors = _ARTICLE_SELECTORS.get(platform) or _ARTICLE_SELECTORS.get(platform.replace("stock_", ""), [])

    def _out_path(post: dict) -> Path:
        uid = post.get("user_id", "")
        if uid:
            d = articles_dir / uid
            d.mkdir(parents=True, exist_ok=True)
            return d / f"{post['id']}.txt"
        return articles_dir / f"{post['id']}.txt"

    pending = [p for p in posts if p.get("id") and p.get("url")
               and not _out_path(p).exists()]
    if not pending:
        return

    log.info("[%s] 开始抓取 %d 篇文章正文...", platform, len(pending))

    # 淘股吧文章正文已包含在 HTML 中（.p_coten），无需登录即可获取全文
    # 若存在 tgb_cookies.json 则注入 Cookie（可选，有助于访问部分限权帖子）
    tgb_cookies: dict = {}
    if platform in ("tgb", "stock_tgb"):
        cookie_path = Path("tgb_cookies.json")
        if cookie_path.exists():
            tgb_cookies = json.loads(cookie_path.read_text(encoding="utf-8"))
            log.info("[淘股吧] 已加载文章 Cookie（%d 个）", len(tgb_cookies))

    def _run(browser):
        ctx = browser.new_context(
            user_agent=USER_AGENT,
            locale="zh-CN",
            viewport={"width": 1280, "height": 800},
        )
        if tgb_cookies:
            ctx.add_cookies([
                {"name": k, "value": v, "domain": ".tgb.cn", "path": "/"}
                for k, v in tgb_cookies.items()
            ])

        for post in pending:
            post_id = post["id"]
            # 微博：用移动版 URL 替换桌面版，避免登录墙；用 id（数字 mid）构造
            if platform == "weibo":
                url = f"https://m.weibo.cn/detail/{post_id}"
            else:
                url = post["url"]
            page    = ctx.new_page()
            Stealth().apply_stealth_sync(page)
            content = ""

            try:
                wait = "commit" if platform in ("eastmoney", "xueqiu", "eastmoney_guba", "stock_eastmoney_guba") else "domcontentloaded"
                page.goto(url, timeout=30000, wait_until=wait)
                # 微博移动版是 Vue SPA，需等待正文元素渲染
                if platform in ("weibo", "stock_weibo"):
                    try:
                        page.wait_for_selector(".weibo-text", timeout=8000)
                    except Exception:
                        pass
                else:
                    # 等待正文选择器出现，比固定等待更快
                    if selectors:
                        try:
                            page.wait_for_selector(", ".join(selectors), timeout=8000)
                        except Exception:
                            pass
                    else:
                        page.wait_for_timeout(3000)

                # 淘股吧：移除 CSS 高度截断，让全文可见（无需登录）
                if platform in ("tgb", "stock_tgb"):
                    page.evaluate("""
                        document.querySelectorAll('.article-text, .p_coten, #first').forEach(el => {
                            el.style.height = 'auto';
                            el.style.overflow = 'visible';
                        });
                    """)

                for sel in selectors:
                    try:
                        el = page.query_selector(sel)
                        if el:
                            t = el.inner_text().strip()
                            if len(t) > 20:
                                content = t
                                break
                    except Exception:
                        pass

                # 微博不做整页 fallback（整页含大量导航噪音）
                # 其他平台选择器未命中时，取整页文本作为兜底
                if not content and platform not in ("weibo", "stock_weibo"):
                    content = (page.evaluate("document.body.innerText") or "").strip()

                # 修复雪球等平台将标点符号单独置于一行的问题（标点归并到上行）
                content = re.sub(r'\n([，。、？！：；])', r'\1', content)
                # 行尾逗号/顿号说明句子未完，直接拼上下一行
                content = re.sub(r'([，、])\n', r'\1', content)
                # 去除导航、页脚、免责声明等杂项
                content = _clean_article_text(content)

                out_file = _out_path(post)
                out_file.write_text(content, encoding="utf-8")
                log.info("[%s] 文章 %s 已保存（%d 字符）→ %s", platform, post_id, len(content), out_file)

            except Exception as e:
                log.warning("[%s] 文章 %s 抓取失败: %s", platform, post_id, e)
            finally:
                page.close()

            time.sleep(1)

        ctx.close()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        _run(browser)
        browser.close()


def fetch_and_save_articles(new_posts: list[dict], platform: str) -> None:
    """
    对新帖子访问文章 URL 抓取完整正文，保存到
    crawler_posts/{platform}/articles/{user_id}/{post_id}.txt。
    若 post 无 user_id，退回到 articles/{post_id}.txt。
    """
    if not new_posts:
        return

    articles_dir = OUTPUT_DIR / platform / "articles"
    articles_dir.mkdir(parents=True, exist_ok=True)
    _fetch_article_batch(new_posts, platform, articles_dir)


def fetch_cninfo_pdfs(new_posts: list[dict]) -> None:
    pass  # 已废弃，PDF 不再下载，pdf_url 保存在 JSON 中


# ── 主流程 ────────────────────────────────────────────────────────────────────

def crawl_stock(stocks: list[str], days: int = DEFAULT_DAYS) -> int:
    """crawl_once(stocks=...) 的向后兼容别名。"""
    return crawl_once(days=days, stocks=stocks)


def _print_stock_summary(stock: str, platform: str, posts: list[dict], plat_key: str) -> None:
    plat_label = {"eastmoney_guba": "东方财富股吧", "xueqiu": "雪球", "weibo": "微博", "tgb": "淘股吧", "hexun": "和讯网"}.get(platform, platform)
    print(f"\n── {plat_label}·{stock} 新帖（{len(posts)} 条）" + "─" * 36)
    for p in posts:
        snippet = p["text"].replace("\n", " ")[:80]
        print(f"  [{p['created_at']}] {snippet}")
        print(f"    链接: {p['url']}")
        print(f"    点赞:{p['like_count']}  评论:{p['reply_count']}  转发:{p['retweet_count']}")
        uid = p.get("user_id", "")
        art = (OUTPUT_DIR / plat_key / "articles" / uid / f"{p['id']}.txt" if uid
               else OUTPUT_DIR / plat_key / "articles" / f"{p['id']}.txt")
        if art.exists():
            print(f"    正文: {art}")
    print()


def _crawl_target(target: dict, days: int, date_str: str, cutoff: datetime) -> int:
    """抓取单个平台，返回新增帖子数。每个平台独立运行，可并行调用。"""
    name     = target["name"]
    platform = target["platform"]

    # 各平台路由
    if platform == "eastmoney":
        raw_posts = fetch_eastmoney(target["user_ids"], days=days)
    elif platform == "tgb":
        raw_posts = fetch_tgb(target, days=days)
    elif platform == "qq_finance":
        raw_posts = fetch_qq_finance(target, days=days)
    elif platform == "hexun":
        raw_posts = fetch_hexun(target, days=days)
    elif platform == "cninfo":
        if not target.get("stocks"):
            log.info("[%s] 未指定股票，跳过抓取（请通过 --stocks 或 crawl_once(stocks=...) 指定）", name)
            return 0
        raw_posts = fetch_cninfo(target, days=days)
    else:
        raw_posts = fetch_platform(target)
        # 雪球/微博：created_at 已是标准格式，在此过滤
        raw_posts = [p for p in raw_posts if _within_days(p.get("created_at", ""), cutoff)]

    new_posts = []
    for post in raw_posts:
        post["platform"] = name
        new_posts.append(post)

    if new_posts:
        save_posts(new_posts, platform, date_str)
        if platform == "cninfo":
            pass   # PDF 不下载，pdf_url 已保存在 JSON 中
        else:
            fetch_and_save_articles(new_posts, platform)
        _print_summary(name, new_posts, platform)
    else:
        log.info("[%s] 没有新帖子", name)

    return len(new_posts)


def crawl_stock(stocks: list[str], days: int = DEFAULT_DAYS) -> int:
    """
    按股票名称/代码在所有支持的平台搜索相关讨论，返回本次新增帖子总数。

    参数：
        stocks - 股票列表，支持名称（"贵州茅台"）或代码（"600519"/"SH600519"），可混用
        days   - 抓取最近 N 天（默认 DEFAULT_DAYS）

    支持平台：
        东方财富股吧  - 按股票代码抓取股吧帖子
        雪球          - 按股票名称关键词搜索讨论帖
        微博          - 按股票名称实时搜索
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _parse_stock(s: str) -> tuple[str, str, str]:
        """返回 (display_name, em_code, xq_code)"""
        s = s.strip()
        m = re.match(r"^(SH|SZ|sh|sz)(\d{6})$", s)
        if m:
            prefix, code = m.group(1).upper(), m.group(2)
            return s, code, f"{prefix}{code}"
        # 支持 "股票名 代码" 或 "代码 股票名" 混合格式，如 "贵州茅台 600519"
        m2 = re.search(r"(\d{6})", s)
        if m2:
            code = m2.group(1)
            name = s.replace(code, "").strip()
            if not name:
                name = code
            prefix = "SH" if code.startswith("6") else "SZ"
            return name, code, f"{prefix}{code}"
        if re.match(r"^\d{6}$", s):
            prefix = "SH" if s.startswith("6") else "SZ"
            return s, s, f"{prefix}{s}"
        try:
            import requests as req
            r = req.post(
                "https://www.cninfo.com.cn/new/information/topSearch/query",
                data={"keyWord": s, "maxNum": 1},
                headers={"User-Agent": USER_AGENT},
                timeout=8,
            )
            results = r.json()
            if results:
                code = results[0]["code"]
                prefix = "SH" if code.startswith("6") else "SZ"
                return s, code, f"{prefix}{code}"
        except Exception as e:
            log.warning("[股票解析] '%s' 代码查询失败: %s", s, e)
        return s, "", s

    parsed = [_parse_stock(s) for s in stocks]
    log.info("股票解析结果: %s", [(n, c) for n, c, _ in parsed])

    date_str = datetime.now().strftime("%Y-%m-%d")
    OUTPUT_DIR.mkdir(exist_ok=True)
    _clear_output_dir()

    def _crawl_stock_platform(name: str, em_code: str, xq_code: str, stock_plat: str) -> int:
        if stock_plat == "eastmoney_guba":
            if not em_code:
                return 0
            raw_posts = fetch_stock_eastmoney(em_code, name, days=days)
        elif stock_plat == "xueqiu":
            raw_posts = fetch_stock_xueqiu(xq_code, name, days=days)
        elif stock_plat == "weibo":
            raw_posts = fetch_stock_weibo(name, days=days)
        elif stock_plat == "tgb":
            if not xq_code:
                return 0
            raw_posts = fetch_stock_tgb(xq_code.lower(), name, days=days)
        else:
            return 0

        plat_key = f"stock_{stock_plat}"

        new_posts = []
        for post in raw_posts:
            post["platform"] = stock_plat
            new_posts.append(post)

        if new_posts:
            save_posts(new_posts, plat_key, date_str)
            if stock_plat in ("weibo", "xueqiu", "tgb"):
                # 正文已在 full_text 字段中，直接写文件，无需再抓文章页
                arts_dir = OUTPUT_DIR / plat_key / "articles"
                for post in new_posts:
                    full_text = post.get("full_text", "").strip()
                    if not full_text:
                        continue
                    uid = post.get("user_id", "anonymous")
                    pid = post.get("id", "")
                    art_path = arts_dir / uid / f"{pid}.txt"
                    art_path.parent.mkdir(parents=True, exist_ok=True)
                    art_path.write_text(full_text, encoding="utf-8")
                    log.info("[%s] 文章 %s 已保存（%d 字符）→ %s", plat_key, pid, len(full_text), art_path)
            else:
                # eastmoney_guba：post_content 仅为摘要，需抓文章页获取全文
                fetch_and_save_articles(new_posts, plat_key)
            _print_stock_summary(name, stock_plat, new_posts, plat_key)
        else:
            log.info("[%s-%s] 没有新帖子", stock_plat, name)

        return len(new_posts)

    tasks = [
        (name, em_code, xq_code, plat)
        for name, em_code, xq_code in parsed
        for plat in ["eastmoney_guba", "xueqiu", "weibo", "tgb"]
    ]
    with ThreadPoolExecutor(max_workers=min(len(tasks), 6)) as executor:
        futures = {
            executor.submit(_crawl_stock_platform, name, em_code, xq_code, plat): f"{plat}-{name}"
            for name, em_code, xq_code, plat in tasks
        }
        total_new = sum(f.result() for f in as_completed(futures))

    log.info("股票搜索共新增 %d 条帖子", total_new)
    return total_new


def crawl_once(
    users: list[str],
    days: int = DEFAULT_DAYS,
) -> int:
    """
    按博主抓取帖子，返回本次新增帖子总数。

    参数：
        users - 博主 ID 或用户名列表（雪球/微博/淘股吧/东方财富），
                  可混用数字 ID 与昵称；
                  自动在所有支持的平台搜索，只抓取找到该用户的平台
        days  - 抓取最近 N 天（默认 DEFAULT_DAYS）
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import copy

    # ── 博主抓取模式 ────────────────────────────────────────────────────────────
    _BLOGGER_PLATFORMS = {t["platform"]: t for t in TARGETS if t["platform"] in _URL_TEMPLATES}

    # 并行对所有博主平台做用户名解析，收集每个平台解析成功的 uid 列表
    def _resolve_for_platform(pname: str) -> tuple[str, list[str]]:
        resolved = [_resolve_user_id(u, pname) for u in users]
        return pname, [uid for uid in resolved if uid]

    blogger_pnames = list(_BLOGGER_PLATFORMS.keys())
    with ThreadPoolExecutor(max_workers=len(blogger_pnames)) as ex:
        futures_resolve = {ex.submit(_resolve_for_platform, pn): pn for pn in blogger_pnames}
        resolve_results = {pn: res for fut in as_completed(futures_resolve)
                           for pn, res in [fut.result()]}

    # 只保留至少解析到一个 uid 的平台
    targets = copy.deepcopy([t for t in TARGETS if resolve_results.get(t["platform"])])

    for t in targets:
        t["user_ids"] = resolve_results[t["platform"]]

    if not targets:
        log.warning("在所有平台均未找到用户 %s，无内容可抓取", users)
        return 0

    log.info("用户名搜索完成，将在以下平台抓取：%s", [t["name"] for t in targets])

    date_str = datetime.now().strftime("%Y-%m-%d")
    OUTPUT_DIR.mkdir(exist_ok=True)
    cutoff = datetime.now() - timedelta(days=days)

    _clear_output_dir()

    with ThreadPoolExecutor(max_workers=len(targets)) as executor:
        futures = {
            executor.submit(_crawl_target, target, days, date_str, cutoff): target["name"]
            for target in targets
        }
        total_new = sum(f.result() for f in as_completed(futures))

    log.info("本次共新增 %d 条帖子", total_new)
    return total_new


def _print_summary(name: str, posts: list[dict], platform: str = "") -> None:
    print(f"\n── {name} 新帖（{len(posts)} 条）" + "─" * 40)
    for p in posts:
        snippet = p["text"].replace("\n", " ")[:80]
        rtype = p.get("record_type", "")
        rtype_label = f"[{rtype}] " if rtype else ""
        print(f"  [{p['created_at']}] {rtype_label}{snippet}")
        print(f"    链接: {p['url']}")
        print(f"    点赞:{p['like_count']}  评论:{p['reply_count']}  转发:{p['retweet_count']}")
        if platform == "cninfo" and p.get("pdf_url"):
            print(f"    PDF: {p['pdf_url']}")
        elif platform:
            uid = p.get("user_id", "")
            art = (OUTPUT_DIR / platform / "articles" / uid / f"{p['id']}.txt" if uid
                   else OUTPUT_DIR / platform / "articles" / f"{p['id']}.txt")
            if art.exists():
                print(f"    正文: {art}")
    print()


# ── 入口 ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="多平台帖子爬虫")
    parser.add_argument("--platform", metavar="NAME",
                        help="只抓取指定平台（雪球/微博/淘股吧/东方财富/腾讯财经/和讯网/巨潮资讯）")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS,
                        help="只抓取最近 N 天的内容（默认 3 天）")
    parser.add_argument("--users", metavar="UID", nargs="+",
                        help="覆盖配置中的博主 ID（雪球/微博/淘股吧/东方财富），"
                             "多个用空格分隔；不填则使用 TARGETS 中的配置")
    parser.add_argument("--stocks", metavar="CODE", nargs="+",
                        help="巨潮：必须指定股票列表，如 000001 600519 平安银行；不指定则跳过巨潮抓取")
    args = parser.parse_args()

    crawl_once(
        days=args.days,
        platform=args.platform,
        users=args.users,
        stocks=args.stocks,
    )

