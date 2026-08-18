# -*- coding: utf-8 -*-
"""financial_tool.py - Day 23：财务指标查询工具（三级降级）

导师要求：get_financial_data(stock_code, metric)
  metric 支持：营收、净利润、营收同比、净利润同比
降级策略：真接口（akshare）→ 内置演示数据 → 明确报错
"""
import os

# ===== 1. 清代理环境变量（沿用 Day 22 的防坑措施）=====
for k in list(os.environ.keys()):
    if 'proxy' in k.lower():
        os.environ[k] = ''

# ===== 2. Monkey patch requests（沿用 Day 22 已验证的写法）=====
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

# ===== 3. 内置演示财报数据（来自研报，标注为演示）=====
# 结构: {股票代码: {公司名: ..., 年度: {指标: 数值}}}
FINANCIAL_MOCK = {
    "300750": {
        "name": "宁德时代",
        "2023A": {"营收": 4009.17, "净利润": 441.21, "营收同比": 22.01, "净利润同比": 43.58},
        "2024E": {"营收": 4680.43, "净利润": 510.30, "营收同比": 16.74, "净利润同比": 15.66},
    },
    "002594": {
        "name": "比亚迪",
        "2023A": {"营收": 6023.15, "净利润": 300.41, "营收同比": 42.04, "净利润同比": 80.72},
        "2024E": {"营收": 7132.40, "净利润": 381.12, "营收同比": 18.42, "净利润同比": 26.87},
    },
    "601012": {
        "name": "隆基绿能",
        "2023A": {"营收": 1294.98, "净利润": 107.51, "营收同比": 0.39, "净利润同比": -27.41},
        "2024E": {"营收": 1385.21, "净利润": 72.30, "营收同比": 6.97, "净利润同比": -32.75},
    },
}


def get_financial_data(stock_code: str, metric: str = "营收") -> str:
    """查询公司财务指标（三级降级）

    参数:
        stock_code: 6 位股票代码，如 300750
        metric: 指标名，如 营收 / 净利润 / 营收同比 / 净利润同比
    返回: 人类可读的字符串
    """
    # 优先级 1: akshare 真接口（网络通时才有用）
    try:
        import akshare as ak
        # akshare 财务摘要接口（同花顺源，指标多）
        df = ak.stock_financial_abstract_ths(symbol=stock_code, indicator="按年度")
        # 找到指标行
        row = df[df["指标"] == metric]
        if not row.empty:
            latest = row.iloc[0]["最新值"]
            return f"{stock_code} 的 {metric}: {latest}（数据来源: akshare 同花顺）"
    except Exception as _e1:
        pass  # 网络不通，走降级

    # 优先级 2: 内置演示数据
    if stock_code in FINANCIAL_MOCK:
        info = FINANCIAL_MOCK[stock_code]
        name = info["name"]
        if "2023A" in info and metric in info["2023A"]:
            val = info["2023A"][metric]
            return f"{name}({stock_code}) 2023A {metric}: {val}（数据来源: 内置演示数据，非实时）"
        return f"{name}({stock_code}): 没有 {metric} 的演示数据"

    # 优先级 3: 明确报错
    return f"查询失败: 未收录股票 {stock_code}，且 akshare 网络不可用"


if __name__ == "__main__":
    print("=" * 60)
    print("财务指标工具测试（get_financial_data）")
    print("=" * 60)
    print(get_financial_data("300750", "营收"))
    print(get_financial_data("300750", "净利润"))
    print(get_financial_data("002594", "营收同比"))
    print(get_financial_data("999999", "营收"))
    print("=" * 60)
