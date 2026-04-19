"""按交易日拉取 1 分钟 K 线并写入 PostgreSQL。

调用 FastAPI：`GET /api/v1/quote/test/{stock_code}`，
每次请求一天：period=1m，count=240，start_time=当日 09:30:00，end_time=当日 15:00:00。

连接参数从环境变量读取（建议 backend/.env），变量名：
  POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
表名固定为 minute_kline（需已在库中创建，脚本不负责建表）。

入库使用 PostgreSQL 的 INSERT ... ON CONFLICT ... DO UPDATE（幂等 UPSERT）：
与表 minute_kline 列一致：(stock_code, timestamp_ms, open_price, high_price,
low_price, close_price, volume, amount)；冲突键为 (stock_code, timestamp_ms)。
API 的 time 支持毫秒整数或时间字符串。

示例：
  python miniqmt_minute.py --stock-code 600000.SH --date 2024-01-02
  python miniqmt_minute.py --base-url http://127.0.0.1:8000 --stock-code 600000.SH \\
      --from-date 2024-01-02 --to-date 2024-01-05
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from zoneinfo import ZoneInfo

_CN_TZ = ZoneInfo("Asia/Shanghai")

try:
    import psycopg2
    from psycopg2.extensions import connection as PGConnection
    from psycopg2.extras import execute_values
except ImportError as e:
    raise SystemExit(
        "需要安装 psycopg2-binary：pip install psycopg2-binary"
    ) from e

from dotenv import load_dotenv

DEFAULT_BASE_URL = "http://129.211.50.62"
MINUTE_KLINE_TABLE = "minute_kline"


def _load_env() -> None:
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.is_file():
        load_dotenv(env_path)


def pg_connect() -> PGConnection:
    _load_env()
    host = os.getenv("POSTGRES_HOST", "").strip()
    user = os.getenv("POSTGRES_USER", "").strip()
    dbname = os.getenv("POSTGRES_DB", "").strip()
    password = os.getenv("POSTGRES_PASSWORD", "")
    port_s = os.getenv("POSTGRES_PORT", "5432").strip()
    missing = [
        name
        for name, val in (
            ("POSTGRES_HOST", host),
            ("POSTGRES_USER", user),
            ("POSTGRES_DB", dbname),
        )
        if not val
    ]
    if missing:
        raise SystemExit(
            "缺少数据库配置: "
            + ", ".join(missing)
            + "。请在 backend/.env 中设置（可参考 .env.example）。"
        )
    try:
        port = int(port_s)
    except ValueError as e:
        raise SystemExit(f"POSTGRES_PORT 无效: {port_s!r}") from e
    return psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=dbname,
        connect_timeout=30,
    )


def parse_date(s: str) -> date:
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Invalid date: {s!r}")


def session_time_strings(d: date) -> Tuple[str, str]:
    """A 股常用交易日时段：9:30–15:00（含午盘），约 240 根 1 分钟 K。"""
    ymd = d.strftime("%Y%m%d")
    return f"{ymd}093000", f"{ymd}150000"


def build_test_url(base: str, stock_code: str) -> str:
    base = base.rstrip("/")
    path = f"/api/v1/quote/test/{urllib.parse.quote(stock_code)}"
    return f"{base}{path}"


def fetch_minute_day(
    base_url: str,
    stock_code: str,
    day: date,
    *,
    timeout: float = 60.0,
) -> List[Dict[str, Any]]:
    start_time, end_time = session_time_strings(day)
    query = urllib.parse.urlencode(
        {
            "period": "1m",
            "count": "240",
            "start_time": start_time,
            "end_time": end_time,
        }
    )
    url = f"{build_test_url(base_url, stock_code)}?{query}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} for {url}: {body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Request failed for {url}: {e}") from e

    payload = json.loads(raw)
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise RuntimeError(f"Unexpected response (no list 'data'): {payload!r}")
    return rows


def _coerce_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _coerce_int(v: Any) -> Optional[int]:
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def bar_time_to_timestamp_ms(val: Any) -> Optional[int]:
    """API 的 time → 毫秒时间戳（与库列 timestamp_ms 一致）。"""
    if val is None:
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        x = int(val)
        if x > 10**15:
            x //= 1_000_000
        elif x > 10**12:
            pass
        elif x > 10**9:
            x *= 1000
        else:
            return None
        return x
    s = str(val).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y%m%d%H%M%S"):
        try:
            dt = datetime.strptime(s, fmt).replace(tzinfo=_CN_TZ)
            return int(dt.timestamp() * 1000)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_CN_TZ)
        return int(dt.timestamp() * 1000)
    except ValueError:
        return None


def upsert_rows(
    conn: PGConnection,
    stock_code: str,
    rows: List[Dict[str, Any]],
) -> int:
    """幂等批量 UPSERT：列与 minute_kline（stock_code + timestamp_ms 主键）一致。"""
    tbl = MINUTE_KLINE_TABLE
    batch: List[Tuple[Any, ...]] = []
    for row in rows:
        ts_ms = bar_time_to_timestamp_ms(row.get("time"))
        if ts_ms is None:
            continue
        batch.append(
            (
                stock_code,
                ts_ms,
                _coerce_float(row.get("open")),
                _coerce_float(row.get("high")),
                _coerce_float(row.get("low")),
                _coerce_float(row.get("close")),
                _coerce_int(row.get("volume")),
                _coerce_float(row.get("amount")),
            )
        )
    if not batch:
        return 0

    sql = f"""
        INSERT INTO {tbl} (
            stock_code, timestamp_ms,
            open_price, high_price, low_price, close_price,
            volume, amount
        ) VALUES %s
        ON CONFLICT (stock_code, timestamp_ms) DO UPDATE SET
            open_price = EXCLUDED.open_price,
            high_price = EXCLUDED.high_price,
            low_price = EXCLUDED.low_price,
            close_price = EXCLUDED.close_price,
            volume = EXCLUDED.volume,
            amount = EXCLUDED.amount
    """
    with conn.cursor() as cur:
        execute_values(
            cur,
            sql,
            batch,
            page_size=min(500, max(1, len(batch))),
        )
    conn.commit()
    return len(batch)


def iter_weekdays(start: date, end: date) -> Iterable[date]:
    d = start
    while d <= end:
        if d.weekday() < 5:
            yield d
        d += timedelta(days=1)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fetch 1m bars per day via /api/v1/quote/test and save to PostgreSQL."
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"API 根地址（默认 {DEFAULT_BASE_URL}）",
    )
    parser.add_argument("--stock-code", required=True, help="证券代码，如 600000.SH")
    parser.add_argument("--date", help="单日：YYYY-MM-DD 或 YYYYMMDD")
    parser.add_argument(
        "--from-date",
        dest="from_date",
        help="区间起点（与 --to-date 合用，仅周一–周五）",
    )
    parser.add_argument(
        "--to-date",
        dest="to_date",
        help="区间终点（含），仅周一–周五",
    )
    parser.add_argument("--timeout", type=float, default=60.0, help="HTTP 超时秒数")
    args = parser.parse_args(argv)

    if args.date:
        if args.from_date or args.to_date:
            parser.error("请只使用 --date，或同时使用 --from-date 与 --to-date")
        days: List[date] = [parse_date(args.date)]
    elif args.from_date and args.to_date:
        start_d = parse_date(args.from_date)
        end_d = parse_date(args.to_date)
        if end_d < start_d:
            parser.error("--to-date 不能早于 --from-date")
        days = list(iter_weekdays(start_d, end_d))
    elif args.from_date or args.to_date:
        parser.error("区间需要同时指定 --from-date 与 --to-date")
    else:
        parser.error("请指定 --date，或 --from-date 与 --to-date")

    conn = pg_connect()
    try:
        total = 0
        for day in days:
            print(f"[{day}] GET 1m {args.stock_code} ...", file=sys.stderr)
            rows = fetch_minute_day(
                args.base_url,
                args.stock_code,
                day,
                timeout=args.timeout,
            )
            written = upsert_rows(conn, args.stock_code, rows)
            print(f"[{day}] upsert {written} rows -> {MINUTE_KLINE_TABLE}", file=sys.stderr)
            total += written
        print(f"完成，累计写入/更新 {total} 条", file=sys.stderr)
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
