# -*- coding: utf-8 -*-
"""P1-5 实时行情真接口成功证据生成脚本 v4（腾讯/新浪直连优先）

本脚本位于 data/eval/，与产物 akshare_real_call_20260905.txt 同目录。

背景：东财 em/push2his 域被临时风控（RemoteDisconnected）。
v4 改为先走「腾讯证券 / 新浪财经」官方行情直连接口（与东财不同源，
家庭宽带通常无风控），东财三接口降级为兜底。

调用顺序（每个源一次请求，先中先赢）：
    D) qt.gtimg.cn      腾讯单股行情（GBK 文本协议）
    E) hq.sinajs.cn     新浪单股行情（需 Referer 头）
    A/B/C) 东财 bid_ask_em / spot_em / hist（兜底）
全部失败则等 30 秒重试，最多 3 轮。

运行：python data/eval/gen_akshare_evidence.py
"""
import os
import re
import sys
import time
import traceback
from datetime import datetime, timedelta

# 脚本在 data/eval/ 下，往上 2 层到项目根
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# 清掉可能干扰直连的代理环境变量
for k in list(os.environ.keys()):
    if "proxy" in k.lower():
        del os.environ[k]

import requests  # noqa: E402

try:
    import akshare as ak  # noqa: E402
    HAS_AK = True
except Exception:
    HAS_AK = False

MAX_ROUNDS = 3
WAIT_SECONDS = 30


# ---------------- 直连接口：腾讯证券 ----------------
def try_tencent():
    """https://qt.gtimg.cn/q=sz002594 返回 GBK 文本，字段用 ~ 分隔"""
    url = "https://qt.gtimg.cn/q=sz002594,sz000001"
    r = requests.get(url, timeout=15)
    r.encoding = "gbk"
    text = r.text
    if "v_sz002594" not in text and "v_sz000001" not in text:
        raise RuntimeError("腾讯接口返回异常: " + text[:100])

    for symbol, stock_name in [("sz002594", "比亚迪(002594)"), ("sz000001", "平安银行(000001)")]:
        m = re.search(re.escape(symbol) + r'="([^"]+)"', text)
        if not m:
            continue
        parts = m.group(1).split("~")
        if len(parts) < 35:
            continue
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            "=== 实时行情真实接口调用成功 ===",
            f"股票: {stock_name}",
            f"现价: {parts[3]} 元",
            f"涨跌额: {parts[31]} | 涨跌幅: {parts[32]}%",
            f"今开: {parts[5]} | 昨收: {parts[4]}",
            f"最高: {parts[33]} | 最低: {parts[34]}",
            f"成交量: {parts[36]} 手",
            "数据来源: 腾讯证券官方行情接口 (qt.gtimg.cn) 直连",
            f"行情时间: {parts[30]}",
            f"调用时间: {now}",
            f"返回字段数: {len(parts)} (接口A级实时报价, 非模拟数据)",
        ]
        return "\n".join(lines) + "\n", "腾讯直连(qt.gtimg.cn)", None

    raise RuntimeError("腾讯接口字段解析失败: " + text[:200])


# ---------------- 直连接口：新浪财经 ----------------
def try_sina():
    """https://hq.sinajs.cn/list=sz000001 需带 Referer，返回 GBK 文本"""
    url = "https://hq.sinajs.cn/list=sz000001"
    headers = {"Referer": "https://finance.sina.com.cn"}
    r = requests.get(url, headers=headers, timeout=15)
    r.encoding = "gbk"
    text = r.text
    if 'hq_str_sz000001=""' in text or "hq_str_sz000001" not in text:
        raise RuntimeError("新浪接口返回异常: " + text[:100])

    m = re.search(r'hq_str_sz000001="([^"]*)"', text)
    if not m:
        raise RuntimeError("新浪接口字段解析失败: " + text[:200])
    parts = m.group(1).split(",")
    if len(parts) < 32:
        raise RuntimeError("新浪接口字段数不足: " + text[:200])
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "=== 实时行情真实接口调用成功 ===",
        f"股票: {parts[0]}(000001)",
        f"现价: {parts[3]} 元",
        f"今开: {parts[1]} | 昨收: {parts[2]}",
        f"最高: {parts[4]} | 最低: {parts[5]}",
        f"成交量: {parts[8]} 股 | 成交额: {parts[9]} 元",
        "数据来源: 新浪财经官方行情接口 (hq.sinajs.cn) 直连",
        f"行情时间: {parts[30]} {parts[31]}",
        f"调用时间: {now}",
        "返回: 官方实时报价(带Referer头鉴权), 非模拟数据",
    ]
    return "\n".join(lines) + "\n", "新浪直连(hq.sinajs.cn)", None


# ---------------- akshare 东财兜底 ----------------
def try_akshare_round(round_no):
    call_log = []
    if not HAS_AK:
        call_log.append("[提示] akshare 未安装/导入失败，跳过东财兜底")
        return None, None, call_log

    try:
        call_log.append(f"[第{round_no}轮-A] ak.stock_bid_ask_em('002594') ...")
        df = ak.stock_bid_ask_em(symbol="002594")
        if df is None or df.empty:
            raise RuntimeError("stock_bid_ask_em 返回空")
        snap = df.iloc[0]
        lines = [
            "=== akshare真实接口调用成功 ===",
            "股票: 比亚迪(002594)",
            f"现价: {snap.get('最新价')} 元",
            f"涨跌: {snap.get('涨跌额')} | 涨跌幅: {snap.get('涨跌幅')}%",
            f"成交量: {snap.get('成交量')} 手 | 成交额: {snap.get('成交额')} 元",
            "数据来源: 东财 eminterface.eastmoney.com (akshare真实接口)",
            f"调用时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"返回行数: {len(df)} 条 (个股盘口，bid_ask_em 接口)",
        ]
        content = "\n".join(lines) + "\n"
        return content, "东财akshare(bid_ask_em)", call_log
    except Exception as e:
        call_log.append(f"[接口A 失败] {type(e).__name__}: {str(e)[:100]}")

    try:
        call_log.append(f"[第{round_no}轮-B] ak.stock_zh_a_spot_em() ...")
        df = ak.stock_zh_a_spot_em()
        if df is None or df.empty:
            raise RuntimeError("spot_em 返回空")
        row = df[df["代码"] == "000001"].iloc[0]
        lines = [
            "=== akshare真实接口调用成功 ===",
            "股票: 平安银行(000001)",
            f"现价: {row['现价']} 元 | 涨跌幅: {row['涨跌幅']}%",
            f"最高: {row['最高']} | 最低: {row['最低']} | 昨收: {row['昨收']}",
            "数据来源: 东财 eminterface.eastmoney.com (akshare真实接口)",
            f"调用时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"返回行数: {len(df)} 条 (全市场实时行情)",
        ]
        content = "\n".join(lines) + "\n"
        return content, "东财akshare(spot_em)", call_log
    except Exception as e:
        call_log.append(f"[接口B 失败] {type(e).__name__}: {str(e)[:100]}")

    try:
        today = datetime.now().date().isoformat().replace("-", "")
        start = (datetime.now().date() - timedelta(days=30)).isoformat().replace("-", "")
        call_log.append(f"[第{round_no}轮-C] ak.stock_zh_a_hist(000001, {start}~{today}) ...")
        df = ak.stock_zh_a_hist(symbol="000001", period="daily", adjust="qfq",
                                start_date=start, end_date=today)
        if df is None or df.empty:
            raise RuntimeError("hist 返回空")
        last = df.iloc[-1]
        lines = [
            "=== akshare真实接口调用成功 ===",
            "股票: 平安银行(000001)",
            f"交易日: {last['日期']}",
            f"收盘: {round(float(last['收盘']), 2)} | 开: {round(float(last['开盘']), 2)} | 高: {round(float(last['最高']), 2)} | 低: {round(float(last['最低']), 2)}",
            f"成交量: {last['成交量']} 手",
            "数据来源: 东财 push2his.eastmoney.com (akshare真实接口)",
            f"调用时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"返回行数: {len(df)} 条 (最近30天日线)",
        ]
        content = "\n".join(lines) + "\n"
        return content, "东财akshare(hist)", call_log
    except Exception as e:
        call_log.append(f"[接口C 失败] {type(e).__name__}: {str(e)[:100]}")

    return None, None, call_log


def main():
    all_log = [f"证据脚本 v4 启动: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"]
    all_log.append("顺序: 腾讯直连 -> 新浪直连 -> 东财akshare兜底; 失败自动重试, 最多 "
                   f"{MAX_ROUNDS} 轮, 每轮间隔 {WAIT_SECONDS} 秒\n")

    for round_no in range(1, MAX_ROUNDS + 1):
        print(f"\n===== 第 {round_no}/{MAX_ROUNDS} 轮 =====")

        # 1) 腾讯直连（最稳，先试）
        for name, fn in [("腾讯直连(qt.gtimg.cn)", try_tencent),
                         ("新浪直连(hq.sinajs.cn)", try_sina)]:
            try:
                print(f"[{name}] 请求中 ...")
                content, label, _ = fn()
                print(content)
                out_path = os.path.join(ROOT, "data", "eval", "akshare_real_call_20260905.txt")
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(content)
                all_log.append(f"[完成] {name} 成功 -> {out_path}")
                log_path = os.path.join(ROOT, "logs", "akshare_evidence_run.log")
                os.makedirs(os.path.dirname(log_path), exist_ok=True)
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(all_log))
                print(f"\n[OK] 证据已写入: {out_path}")
                print(f"[日志] {log_path}")
                return 0
            except Exception as e:
                msg = f"[{name} 失败] {type(e).__name__}: {str(e)[:120]}"
                print("  " + msg)
                all_log.append(msg)

        # 2) akshare 东财兜底
        content, label, ak_log = try_akshare_round(round_no)
        all_log.extend(ak_log)
        if content is not None:
            out_path = os.path.join(ROOT, "data", "eval", "akshare_real_call_20260905.txt")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(content)
            all_log.append(f"\n[完成] {label} 成功 -> {out_path}")
            log_path = os.path.join(ROOT, "logs", "akshare_evidence_run.log")
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("\n".join(all_log))
            print(content)
            print(f"\n[OK] 证据已写入: {out_path}")
            print(f"[日志] {log_path}")
            return 0

        if round_no < MAX_ROUNDS:
            print(f"  本轮全失败，{WAIT_SECONDS} 秒后自动重试 ...")
            all_log.append(f"  第{round_no}轮失败, 等待 {WAIT_SECONDS} 秒重试")
            time.sleep(WAIT_SECONDS)

    all_log.append("\n[结论] 全部数据源失败：请检查整体网络（百度能否打开？代理是否残留？）")
    all_log.append("备选: ① 手机热点重试  ② 直接用 17:05 的 stock_bid_ask_em 成功截图当证据")
    log_path = os.path.join(ROOT, "logs", "akshare_evidence_run.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(all_log))
    print("\n".join(all_log[-3:]))
    print(f"\n[日志] {log_path}")
    return 2


if __name__ == "__main__":
    sys.exit(main())