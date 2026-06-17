"""
Fetch the full tradeable stock universe: S&P 500 + NASDAQ 100.
Uses Wikipedia via BeautifulSoup — no API key needed.
"""

import requests
import pandas as pd
from io import StringIO
from bs4 import BeautifulSoup
from functools import lru_cache

_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


def _wiki_table(url: str, table_id: str | None = None) -> pd.DataFrame:
    resp = requests.get(url, headers=_HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    table = soup.find("table", {"id": table_id}) if table_id else soup.find("table", {"class": "wikitable"})
    if table is None:
        raise ValueError(f"Table not found at {url}")
    return pd.read_html(StringIO(str(table)))[0]


@lru_cache(maxsize=1)
def sp500_tickers() -> list[str]:
    df = _wiki_table(
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        table_id="constituents",
    )
    return [t.replace(".", "-") for t in df["Symbol"].tolist()]


@lru_cache(maxsize=1)
def nasdaq100_tickers() -> list[str]:
    df = _wiki_table("https://en.wikipedia.org/wiki/Nasdaq-100")
    # find column named Ticker or Symbol
    for col in df.columns:
        if str(col).lower() in ("ticker", "symbol"):
            return [str(t).replace(".", "-") for t in df[col].tolist()]
    raise ValueError("Ticker column not found in NASDAQ-100 table")


def full_universe() -> list[str]:
    """Deduplicated union of S&P 500 + NASDAQ 100 tickers."""
    sp, nq = [], []
    try:
        sp = sp500_tickers()
        print(f"      S&P 500  : {len(sp)} tickers")
    except Exception as e:
        print(f"  [WARN] S&P 500 fetch failed: {e}")
    try:
        nq = nasdaq100_tickers()
        print(f"      NASDAQ 100: {len(nq)} tickers")
    except Exception as e:
        print(f"  [WARN] NASDAQ 100 fetch failed: {e}")
    combined = list(dict.fromkeys(sp + nq))
    return combined
