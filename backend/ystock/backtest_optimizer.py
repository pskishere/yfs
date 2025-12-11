"""
基于现有 SQLite 数据做简易指标组合回测，输出一周/一月内
命中止盈或止损表现最佳的指标组合。
"""

from __future__ import annotations

import itertools
import json
import sqlite3
import statistics
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

# 默认数据库路径，按当前项目结构计算
DB_PATH = Path(__file__).resolve().parents[2] / "data" / "db.sqlite3"

# 回测参数，可按需调整
TAKE_PROFIT_PCT = 0.04  # 止盈阈值（4%）
STOP_LOSS_PCT = 0.02    # 止损阈值（2%）
MAX_COMBO_SIZE = 3
MIN_TRADES = 3

FIB_NEAR_PCT = 0.01     # 价格距离斐波那契位的相对阈值
SEGMENT_SPLITS = [0.0, 0.33, 0.66, 1.0]  # 数据分段比例（可用于不同阶段验证）
VOL_SURGE_RATIO = 1.5   # 放量阈值（当前/20日均量）
BREAKOUT_TOLERANCE = 0.01  # 突破近高的容差（1%内）
PULLBACK_TOLERANCE = 0.01  # 回踩中轨/均线的容差

FEATURE_KEYS = [
    "ma_bull",
    "ma_bear",
    "rsi_overbought",
    "rsi_oversold",
    "macd_positive",
    "macd_negative",
    "close_above_bb_mid",
    "close_below_bb_mid",
    "near_fib_382",
    "near_fib_618",
    "above_fib_382",
    "above_fib_618",
    "below_fib_382",
    "below_fib_618",
    "vol_surge",
    "rsi_mid_band",
    "bb_pullback",
    "breakout_20_high",
]

CONFLICT_PAIRS = {
    frozenset(("ma_bull", "ma_bear")),
    frozenset(("macd_positive", "macd_negative")),
    frozenset(("close_above_bb_mid", "close_below_bb_mid")),
    frozenset(("rsi_overbought", "rsi_oversold")),
    frozenset(("breakout_20_high", "close_below_bb_mid")),
}


def load_records(db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    """读取 StockAnalysis 中的蜡烛数据与标识信息。"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT symbol, candles FROM ystock_stockanalysis ORDER BY updated_at DESC"
    )
    records: List[Dict[str, Any]] = []
    for symbol, candles_json in cur.fetchall():
        candles = json.loads(candles_json)
        if not isinstance(candles, list):
            continue
        records.append({"symbol": symbol, "candles": candles})
    conn.close()
    return records


def rolling_mean(values: Sequence[float], window: int) -> List[float | None]:
    """计算简单滑动均值序列。"""
    out: List[float | None] = [None] * len(values)
    if len(values) < window:
        return out
    running = sum(values[:window])
    out[window - 1] = running / window
    for i in range(window, len(values)):
        running += values[i] - values[i - window]
        out[i] = running / window
    return out


def calc_ema_series(values: Sequence[float], period: int) -> List[float | None]:
    """计算 EMA 序列。"""
    if not values:
        return []
    alpha = 2 / (period + 1)
    ema: List[float | None] = [None] * len(values)
    ema[0] = values[0]
    for i in range(1, len(values)):
        prev = ema[i - 1]
        ema[i] = values[i] * alpha + (prev if prev is not None else values[i]) * (
            1 - alpha
        )
    return ema


def calc_rsi_series(closes: Sequence[float], period: int = 14) -> List[float | None]:
    """计算 RSI 序列。"""
    if len(closes) < period + 1:
        return [None] * len(closes)
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(delta, 0) for delta in deltas]
    losses = [abs(min(delta, 0)) for delta in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    rsi: List[float | None] = [None] * len(closes)
    rsi[period] = 100 - (100 / (1 + (avg_gain / avg_loss if avg_loss else 1e9)))

    for i in range(period + 1, len(closes)):
        gain = gains[i - 1]
        loss = losses[i - 1]
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        rs = avg_gain / avg_loss if avg_loss else 1e9
        rsi[i] = 100 - (100 / (1 + rs))
    return rsi


def calc_macd_hist(closes: Sequence[float]) -> List[float | None]:
    """计算 MACD 柱状图序列。"""
    ema12 = calc_ema_series(closes, 12)
    ema26 = calc_ema_series(closes, 26)
    macd_line: List[float | None] = [None] * len(closes)
    for i in range(len(closes)):
        if ema12[i] is not None and ema26[i] is not None:
            macd_line[i] = ema12[i] - ema26[i]
    signal = calc_ema_series(
        [v if v is not None else 0 for v in macd_line], 9
    )
    hist: List[float | None] = [None] * len(closes)
    for i in range(len(closes)):
        if macd_line[i] is not None and signal[i] is not None:
            hist[i] = macd_line[i] - signal[i]
    return hist


def calc_bollinger(closes: Sequence[float], period: int = 20, num_std: float = 2.0) -> Tuple[List[float | None], List[float | None], List[float | None]]:
    """计算布林带序列。"""
    mid = rolling_mean(closes, period)
    upper: List[float | None] = [None] * len(closes)
    lower: List[float | None] = [None] * len(closes)
    if len(closes) < period:
        return mid, upper, lower
    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1 : i + 1]
        mean = mid[i]
        if mean is None:
            continue
        variance = sum((v - mean) ** 2 for v in window) / period
        std = variance**0.5
        upper[i] = mean + num_std * std
        lower[i] = mean - num_std * std
    return mid, upper, lower


def calc_fib_levels(highs: Sequence[float], lows: Sequence[float], lookback: int = 20) -> Tuple[List[float | None], List[float | None]]:
    """计算最近区间的斐波那契 38.2 与 61.8 水平。"""
    if len(highs) < 2 or len(lows) < 2:
        return [None] * len(highs), [None] * len(highs)
    fib382: List[float | None] = [None] * len(highs)
    fib618: List[float | None] = [None] * len(highs)
    for i in range(len(highs)):
        if i < 1:
            continue
        start = max(0, i - lookback + 1)
        recent_high = max(highs[start : i + 1])
        recent_low = min(lows[start : i + 1])
        price_range = recent_high - recent_low
        fib382[i] = recent_high - price_range * 0.382
        fib618[i] = recent_high - price_range * 0.618
    return fib382, fib618


def has_conflict(combo: Tuple[str, ...]) -> bool:
    """检查组合是否存在互斥特征。"""
    combo_set = frozenset(combo)
    return any(pair.issubset(combo_set) for pair in CONFLICT_PAIRS)


def build_feature_rows(symbol: str, candles: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[float], List[float], List[float]]:
    """基于蜡烛序列生成特征行。"""
    if not candles:
        return [], [], [], []
    closes = [float(c["close"]) for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    times = [c.get("time") for c in candles]
    volumes = [float(c.get("volume", 0)) for c in candles]

    ma5 = rolling_mean(closes, 5)
    ma20 = rolling_mean(closes, 20)
    rsi = calc_rsi_series(closes, 14)
    macd_hist = calc_macd_hist(closes)
    bb_mid, bb_upper, bb_lower = calc_bollinger(closes, 20, 2.0)
    fib_382, fib_618 = calc_fib_levels(highs, lows, 20)
    vol_avg20 = rolling_mean(volumes, 20)

    rows: List[Dict[str, Any]] = []
    for idx in range(len(closes)):
        # 需要至少 26 日数据以稳定主要指标
        if idx < 26:
            continue
        row_features = {
            "ma_bull": ma5[idx] is not None and ma20[idx] is not None and ma5[idx] > ma20[idx],
            "ma_bear": ma5[idx] is not None and ma20[idx] is not None and ma5[idx] < ma20[idx],
            "rsi_overbought": rsi[idx] is not None and rsi[idx] > 65,
            "rsi_oversold": rsi[idx] is not None and rsi[idx] < 35,
            "rsi_mid_band": rsi[idx] is not None and 40 <= rsi[idx] <= 55,
            "macd_positive": macd_hist[idx] is not None and macd_hist[idx] > 0,
            "macd_negative": macd_hist[idx] is not None and macd_hist[idx] < 0,
            "close_above_bb_mid": bb_mid[idx] is not None and closes[idx] > bb_mid[idx],
            "close_below_bb_mid": bb_mid[idx] is not None and closes[idx] < bb_mid[idx],
            "bb_pullback": bb_mid[idx] is not None and abs(closes[idx] - bb_mid[idx]) / closes[idx] < PULLBACK_TOLERANCE,
            "near_fib_382": fib_382[idx] is not None and abs(closes[idx] - fib_382[idx]) / closes[idx] < FIB_NEAR_PCT,
            "near_fib_618": fib_618[idx] is not None and abs(closes[idx] - fib_618[idx]) / closes[idx] < FIB_NEAR_PCT,
            "above_fib_382": fib_382[idx] is not None and closes[idx] > fib_382[idx],
            "above_fib_618": fib_618[idx] is not None and closes[idx] > fib_618[idx],
            "below_fib_382": fib_382[idx] is not None and closes[idx] < fib_382[idx],
            "below_fib_618": fib_618[idx] is not None and closes[idx] < fib_618[idx],
            "vol_surge": vol_avg20[idx] is not None and volumes[idx] / vol_avg20[idx] >= VOL_SURGE_RATIO,
            "breakout_20_high": closes[idx] >= max(highs[max(0, idx - 19): idx + 1]) * (1 - BREAKOUT_TOLERANCE),
        }
        if not any(row_features.values()):
            continue
        rows.append(
            {
                "symbol": symbol,
                "time": times[idx],
                "index": idx,
                "close": closes[idx],
                "features": row_features,
                "outcomes": {},
            }
        )
    return rows, closes, highs, lows


def label_outcomes(
    rows: List[Dict[str, Any]],
    closes: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    horizons: Iterable[int] = (5, 20),
    tp_pct: float = TAKE_PROFIT_PCT,
    sl_pct: float = STOP_LOSS_PCT,
) -> None:
    """为每个特征行计算未来窗口的收益与触发情况。"""
    for row in rows:
        idx = row["index"]
        for horizon in horizons:
            if idx + horizon >= len(closes):
                continue
            entry = closes[idx]
            tp_price = entry * (1 + tp_pct)
            sl_price = entry * (1 - sl_pct)

            window_high = max(highs[idx + 1 : idx + horizon + 1])
            window_low = min(lows[idx + 1 : idx + horizon + 1])

            outcome = "hold"
            if window_low <= sl_price and window_high >= tp_price:
                outcome = "hit_both"
            elif window_low <= sl_price:
                outcome = "stop"
            elif window_high >= tp_price:
                outcome = "take"

            final_return = (closes[idx + horizon] - entry) / entry
            row["outcomes"][horizon] = {
                "outcome": outcome,
                "final_return": final_return,
            }


def evaluate_combos(
    rows: List[Dict[str, Any]],
    horizon: int,
    min_trades: int = MIN_TRADES,
) -> List[Dict[str, Any]]:
    """统计各指标组合在指定周期的表现。"""
    combos_stats: List[Dict[str, Any]] = []
    for size in range(1, MAX_COMBO_SIZE + 1):
        for combo in itertools.combinations(FEATURE_KEYS, size):
            if has_conflict(combo):
                continue
            matched = []
            for row in rows:
                outcome = row["outcomes"].get(horizon)
                if not outcome:
                    continue
                features = row["features"]
                if all(features.get(key) for key in combo):
                    matched.append(outcome)
            if len(matched) < min_trades:
                continue
            tp_count = sum(1 for m in matched if m["outcome"] == "take")
            sl_count = sum(1 for m in matched if m["outcome"] == "stop")
            both_count = sum(1 for m in matched if m["outcome"] == "hit_both")
            avg_return = statistics.mean(m["final_return"] for m in matched)
            median_return = statistics.median(m["final_return"] for m in matched)
            combos_stats.append(
                {
                    "combo": combo,
                    "trades": len(matched),
                    "tp_rate": tp_count / len(matched),
                    "sl_rate": sl_count / len(matched),
                    "both_rate": both_count / len(matched),
                    "avg_return": avg_return,
                    "median_return": median_return,
                }
            )
    combos_stats.sort(key=lambda m: (m["tp_rate"], m["avg_return"]), reverse=True)
    return combos_stats


# 预设策略组合（可避免组合爆炸）
PRESET_COMBOS = {
    "trend_pullback_vol": ["ma_bull", "rsi_mid_band", "bb_pullback", "vol_surge"],
    "breakout_volume": ["breakout_20_high", "macd_positive", "vol_surge"],
    "fib_reversal": ["rsi_oversold", "macd_positive", "near_fib_618"],
    "fib_overbought_trim": ["rsi_overbought", "near_fib_382", "above_fib_382"],
}


def evaluate_presets(
    rows: List[Dict[str, Any]],
    horizon: int,
    min_trades: int = MIN_TRADES,
) -> List[Dict[str, Any]]:
    """评估预设策略组合，避免盲目暴力组合。"""
    stats: List[Dict[str, Any]] = []
    for name, combo in PRESET_COMBOS.items():
        matched = []
        for row in rows:
            outcome = row["outcomes"].get(horizon)
            if not outcome:
                continue
            feats = row["features"]
            if all(feats.get(k) for k in combo):
                matched.append(outcome)
        if len(matched) < min_trades:
            continue
        tp = sum(1 for m in matched if m["outcome"] == "take")
        sl = sum(1 for m in matched if m["outcome"] == "stop")
        both = sum(1 for m in matched if m["outcome"] == "hit_both")
        avg_ret = statistics.mean(m["final_return"] for m in matched)
        med_ret = statistics.median(m["final_return"] for m in matched)
        stats.append(
            {
                "name": name,
                "combo": combo,
                "trades": len(matched),
                "tp_rate": tp / len(matched),
                "sl_rate": sl / len(matched),
                "both_rate": both / len(matched),
                "avg_return": avg_ret,
                "median_return": med_ret,
            }
        )
    stats.sort(key=lambda m: (m["tp_rate"], m["avg_return"]), reverse=True)
    return stats


def collect_trade_points(
    rows: List[Dict[str, Any]],
    combo: List[str],
    horizon: int,
    max_points: int = 30,
) -> List[Dict[str, Any]]:
    """收集满足组合的买入点及未来结果。"""
    points: List[Dict[str, Any]] = []
    for row in sorted(rows, key=lambda r: r["index"]):
        outcome = row["outcomes"].get(horizon)
        if not outcome:
            continue
        feats = row["features"]
        if all(feats.get(k) for k in combo):
            points.append(
                {
                    "symbol": row["symbol"],
                    "time": row["time"],
                    "price": row["close"],
                    "outcome": outcome["outcome"],
                    "return": outcome["final_return"],
                }
            )
        if len(points) >= max_points:
            break
    return points


def split_rows(rows: List[Dict[str, Any]], splits: List[float]) -> List[List[Dict[str, Any]]]:
    """按比例切分时间序列，便于多区间验证。"""
    if not rows or not splits or len(splits) < 2:
        return [rows]
    # 按时间索引排序
    rows_sorted = sorted(rows, key=lambda r: r["index"])
    n = len(rows_sorted)
    segments: List[List[Dict[str, Any]]] = []
    for i in range(len(splits) - 1):
        start = int(splits[i] * n)
        end = int(splits[i + 1] * n)
        segment = rows_sorted[start:end]
        if segment:
            segments.append(segment)
    return segments


def summarize_and_print(name: str, combos: List[Dict[str, Any]], top_k: int = 10) -> None:
    """打印组合统计结果。"""
    print(f"\n====== {name} ======")
    if not combos:
        print("没有满足最小样本数的组合")
        return
    for item in combos[:top_k]:
        combo_str = " + ".join(item["combo"])
        print(
            f"{combo_str:60s} | 次数 {item['trades']:4d} "
            f"| 止盈率 {item['tp_rate']:.1%} 止损率 {item['sl_rate']:.1%} 同时触发 {item['both_rate']:.1%} "
            f"| 平均收益 {item['avg_return']:.2%} 中位数 {item['median_return']:.2%}"
        )


def summarize_presets(name: str, stats: List[Dict[str, Any]]) -> None:
    """打印预设策略表现。"""
    print(f"\n------ {name} (预设策略) ------")
    if not stats:
        print("预设策略无满足样本数的结果")
        return
    for item in stats:
        combo_str = " + ".join(item["combo"])
        print(
            f"{item['name']:22s} | {combo_str:60s} | 次数 {item['trades']:4d} "
            f"| 止盈率 {item['tp_rate']:.1%} 止损率 {item['sl_rate']:.1%} "
            f"同时触发 {item['both_rate']:.1%} | 平均收益 {item['avg_return']:.2%} 中位数 {item['median_return']:.2%}"
        )


def print_trade_points(title: str, points: List[Dict[str, Any]]) -> None:
    """打印买入点示例。"""
    if not points:
        print(f"{title}: 无买入点样本")
        return
    print(f"{title}: 前 {len(points)} 个买入点示例")
    for p in points:
        print(
            f"- {p['symbol']} {p['time']} @ {p['price']:.2f} -> {p['outcome']} 回报 {p['return']:.2%}"
        )


def run(horizons: Iterable[int] = (5, 20), segment_splits: List[float] | None = None) -> None:
    """主入口：加载数据、回测并输出最优组合，支持分段验证。"""
    segment_splits = segment_splits or SEGMENT_SPLITS
    records = load_records()
    if not records:
        print("未找到可用记录")
        return

    all_rows: List[Dict[str, Any]] = []
    for record in records:
        rows, closes, highs, lows = build_feature_rows(record["symbol"], record["candles"])
        label_outcomes(rows, closes, highs, lows, horizons=horizons)
        all_rows.extend(rows)

    if not all_rows:
        print("数据不足，无法生成特征行")
        return

    segments = split_rows(all_rows, segment_splits)
    for seg_idx, segment in enumerate(segments):
        seg_name = f"全量" if len(segments) == 1 else f"分段 {seg_idx + 1}/{len(segments)}"
        for horizon in horizons:
            combos = evaluate_combos(segment, horizon)
            summarize_and_print(f"{seg_name} | 周期: {horizon} 日", combos)
            preset_stats = evaluate_presets(segment, horizon)
            summarize_presets(f"{seg_name} | 周期: {horizon} 日", preset_stats)
            for preset in preset_stats[:2]:  # 仅展示前2个预设的样本点，避免输出过长
                points = collect_trade_points(segment, preset["combo"], horizon, max_points=10)
                print_trade_points(f"{seg_name} | 周期 {horizon} 日 | 预设 {preset['name']}", points)


if __name__ == "__main__":
    run()
