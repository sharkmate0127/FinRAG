# -*- coding: utf-8 -*-
"""股价查询工具（双模式：akshare 真接口 + 本地演示数据兜底）

设计要点：
1. 默认先用 akshare 调东财真实接口
2. 失败则降级到本地演示数据（10 只常见股票）
3. 再失败就返回详细错误，方便排查
4. 面试可讲：网络降级 + 多接口兜底（生产级设计）
"""
import os
import sys
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


# ===== 4. 三级降级：akshare → 基础价 + 随机波动 → 错误 =====
def _query_akshare(stock_code: str):
    """akshare 真实接口（东财行情）"""
    import akshare as ak
    df = ak.stock_bid_ask_em(symbol=stock_code)
    name = df[df["item"] == "名称"].iloc[0]["value"]
    price = float(df[df["item"] == "最新"].iloc[0]["value"])
    return name, price, "akshare真实接口"


def _query_local(stock_code: str):
    """本地演示数据（基准价 + 随机 ±3% 波动）"""
    if stock_code not in BASE_PRICES:
        return None, None, f"本地演示未收录 {stock_code}（演示模式仅支持 10 只常见股票）"
    name, base = BASE_PRICES[stock_code]
    change_pct = random.uniform(-3.0, 3.0)
    price = base * (1 + change_pct / 100)
    return name, price, f"本地演示（基准价 {base}，波动 {change_pct:+.2f}%）"


def get_stock_price(stock_code: str) -> str:
    """查股价（自动降级）

    返回格式：宁德时代(300750) 最新价: 250.36 元（数据来源: akshare真实接口）
    """
    # 优先级 1: akshare 真实接口
    try:
        name, price, source = _query_akshare(stock_code)
        return f"{name}({stock_code}) 最新价: {price:.2f} 元（数据来源: {source}）"
    except Exception as e1:
        # 优先级 2: 本地演示数据
        try:
            name, price, source = _query_local(stock_code)
            if name is None:
                return f"{stock_code} 查询失败: {source}；akshare 错误: {type(e1).__name__}"
            return f"{name}({stock_code}) 最新价: {price:.2f} 元（数据来源: {source}；akshare 失败原因: {type(e1).__name__}）"
        except Exception as e2:
            return f"{stock_code} 查询失败: akshare={type(e1).__name__}, 本地={type(e2).__name__}"


if __name__ == "__main__":
    print("=" * 60)
    print("股价查询测试（三级降级：akshare → 本地演示 → 错误）")
    print("=" * 60)
    for code in ["300750", "002594", "00700", "999999"]:  # 999999 是未收录的
        print(get_stock_price(code))
    print("=" * 60)
