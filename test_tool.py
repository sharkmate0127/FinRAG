# -*- coding: utf-8 -*-
"""股价查询工具（多级降级：腾讯直连 → 新浪直连 → akshare → 本地演示数据）

设计要点：
1. 默认先用腾讯证券 qt.gtimg.cn 官方行情接口直连（不限频，免费）
2. 失败则降级到新浪财经 hq.sinajs.cn 官方行情接口（需 Referer 头）
3. 再失败则降级到 akshare 东财真实接口（易被风控）
4. 最后降级到本地演示数据（10 只常见股票）
5. 全部失败返回详细错误，方便排查
6. 面试可讲：多源直连 + 多级降级（生产级设计）
"""
import os
import sys
import re
import random
import traceback

# ===== 1. 清掉所有可能影响代理的环境变量 =====
for k in list(os.environ.keys()):
    if 'proxy' in k.lower():
        os.environ[k] = ''

# ===== 2. Monkey patch requests（防代理残留） =====
try:
    import requests
    _orig_session_init = requests.Session.__init__

    def _patched_session_init(self, *args, **kwargs):
        _orig_session_init(self, *args, **kwargs)
        self.trust_env = False
        self.proxies = {}

    requests.Session.__init__ = _patched_session_init

    _orig_get = requests.get

    def _patched_get(url, **kwargs):
        kwargs['proxies'] = {'http://': '', 'https://': ''}
        return _orig_get(url, **kwargs)

    requests.get = _patched_get
except Exception as _e:
    print(f"[warn] patch requests 失败（不影响主流程）: {_e}")


def _code_with_prefix(code: str) -> str:
    """A 股代码 → 腾讯/新浪接口的带前缀代码（5/6/7/9=sh 沪, 0/2/3=sz 深）"""
    if code.startswith(('5', '6', '7', '9')):
        return 'sh' + code
    return 'sz' + code


# ===== 3. 演示用基础价（最新一次手动查询：2026-08 中旬） =====
BASE_PRICES = {
    '300750': ('宁德时代', 250.36),
    '002594': ('比亚迪', 320.45),
    '601012': ('隆基绿能', 18.62),
    '300274': ('阳光电源', 65.83),
    '688111': ('金山办公', 280.50),
    '00700': ('腾讯控股', 380.20),
    '000063': ('中兴通讯', 28.95),
    '603019': ('中科曙光', 45.30),
    '000977': ('浪潮信息', 32.10),
    '000001': ('平安银行', 12.85),
}


# ===== 4. 一级降级：腾讯证券官方行情直连 =====
def _query_tencent(stock_code: str):
    """https://qt.gtimg.cn/q=sz002594 返回 GBK 文本，~ 分隔字段"""
    sym = _code_with_prefix(stock_code)
    r = requests.get(f"https://qt.gtimg.cn/q={sym}", timeout=10)
    r.encoding = "gbk"
    text = r.text
    if f'v_{sym}=""' in text or f'v_{sym}' not in text:
        raise RuntimeError(f"腾讯接口返回异常: {text[:80]}")
    m = re.search(re.escape(sym) + r'="([^"]+)"', text)
    if not m:
        raise RuntimeError("腾讯接口字段解析失败")
    parts = m.group(1).split("~")
    if len(parts) < 35:
        raise RuntimeError(f"腾讯接口字段数不足: {len(parts)}")
    name = parts[1].strip()
    price = float(parts[3])
    ttime = parts[30]
    return name, price, f"腾讯证券真实接口(qt.gtimg.cn,行情时间{ttime})"


# ===== 5. 二级降级：新浪财经官方行情直连（需 Referer 头） =====
def _query_sina(stock_code: str):
    """https://hq.sinajs.cn/list=sz000001 需 Referer: https://finance.sina.com.cn"""
    sym = _code_with_prefix(stock_code)
    headers = {"Referer": "https://finance.sina.com.cn"}
    r = requests.get(f"https://hq.sinajs.cn/list={sym}", headers=headers, timeout=10)
    r.encoding = "gbk"
    text = r.text
    if f'hq_str_{sym}=""' in text or f'hq_str_{sym}' not in text:
        raise RuntimeError(f"新浪接口返回异常: {text[:80]}")
    m = re.search(re.escape(sym) + r'="([^"]*)"', text)
    if not m:
        raise RuntimeError("新浪接口字段解析失败")
    parts = m.group(1).split(",")
    if len(parts) < 32:
        raise RuntimeError(f"新浪接口字段数不足: {len(parts)}")
    name = parts[0]
    price = float(parts[3])
    ttime = parts[30] + " " + parts[31]
    return name, price, f"新浪财经真实接口(hq.sinajs.cn,行情时间{ttime})"


# ===== 6. 三级降级：akshare 东财真实接口（易被风控） =====
def _query_akshare(stock_code: str):
    """akshare 真实接口（东财历史 K 线最近一日收盘价作准实时）"""
    import akshare as ak
    from datetime import datetime, timedelta
    end = datetime.now().strftime("%Y%m%d")
    start = (datetime.now() - timedelta(days=60)).strftime("%Y%m%d")
    df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", adjust="qfq",
                            start_date=start, end_date=end)
    if df is None or df.empty:
        raise ValueError(f"akshare 返回空数据（代码 {stock_code}，最近 60 日无交易）")
    last = df.iloc[-1]
    close_price = float(last["收盘"])
    trade_date = str(last["日期"])
    name = BASE_PRICES.get(stock_code, (f"股票{stock_code}",))[0]
    return name, close_price, f"akshare真实接口（{trade_date} 收盘）"


# ===== 7. 四级降级：本地演示数据 =====
def _query_local(stock_code: str):
    """本地演示数据（基准价 + 随机 ±3% 波动）"""
    if stock_code not in BASE_PRICES:
        return None, None, f"本地演示未收录 {stock_code}（演示模式仅支持 10 只常见股票）"
    name, base = BASE_PRICES[stock_code]
    change_pct = random.uniform(-3.0, 3.0)
    price = base * (1 + change_pct / 100)
    return name, price, f"本地演示（基准价 {base}，波动 {change_pct:+.2f}%）"


def get_stock_price(stock_code: str) -> str:
    """查股价（四级自动降级）

    优先级：腾讯证券直连 → 新浪财经直连 → akshare 东财 → 本地演示
    返回格式：宁德时代(300750) 最新价: 250.36 元（数据来源: 腾讯证券真实接口...）
    """
    # 优先级 1: 腾讯证券官方行情直连
    try:
        name, price, source = _query_tencent(stock_code)
        return f"{name}({stock_code}) 最新价: {price:.2f} 元（数据来源: {source}）"
    except Exception as e1:
        # 优先级 2: 新浪财经官方行情直连
        try:
            name, price, source = _query_sina(stock_code)
            return f"{name}({stock_code}) 最新价: {price:.2f} 元（数据来源: {source}；腾讯失败: {type(e1).__name__}）"
        except Exception as e2:
            # 优先级 3: akshare 东财真实接口
            try:
                name, price, source = _query_akshare(stock_code)
                return f"{name}({stock_code}) 最新价: {price:.2f} 元（数据来源: {source}；直连失败: 腾讯={type(e1).__name__}/新浪={type(e2).__name__}）"
            except Exception as e3:
                # 优先级 4: 本地演示数据
                try:
                    name, price, source = _query_local(stock_code)
                    if name is None:
                        return f"{stock_code} 查询失败: {source}；网络错误: 腾讯={type(e1).__name__}/新浪={type(e2).__name__}/akshare={type(e3).__name__}"
                    return f"{name}({stock_code}) 最新价: {price:.2f} 元（数据来源: {source}；真接口失败: 腾讯={type(e1).__name__}/新浪={type(e2).__name__}/akshare={type(e3).__name__}）"
                except Exception as e4:
                    return f"{stock_code} 查询失败: 腾讯={type(e1).__name__}/新浪={type(e2).__name__}/akshare={type(e3).__name__}/本地={type(e4).__name__}"


if __name__ == "__main__":
    print("=" * 60)
    print("股价查询测试（四级降级：腾讯直连 → 新浪直连 → akshare → 本地演示）")
    print("=" * 60)
    for code in ["300750", "002594", "00700", "999999"]:  # 999999 是未收录的
        print(get_stock_price(code))
    print("=" * 60)
