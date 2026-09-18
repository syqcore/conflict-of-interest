"""Fetch real daily ROL history; never substitutes generated market data."""
import datetime
import json
from pathlib import Path
import urllib.request


def fetch():
    url = 'https://query1.finance.yahoo.com/v8/finance/chart/ROL?range=2y&interval=1d'
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(request, timeout=45) as response:
        raw = json.load(response)
    result = raw['chart']['result'][0]
    if result['meta']['symbol'] != 'ROL':
        raise ValueError('Wrong ticker returned')
    quotes = result['indicators']['quote'][0]
    adjusted = result['indicators']['adjclose'][0]['adjclose']
    bars = []
    for i, timestamp in enumerate(result['timestamp']):
        if quotes['open'][i] and quotes['close'][i] and adjusted[i]:
            factor = adjusted[i] / quotes['close'][i]
            bars.append({'date': datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc).date().isoformat(),
                         'open': quotes['open'][i] * factor, 'close': adjusted[i]})
    if len(bars) < 32:
        raise ValueError('Insufficient real price history')
    output = Path(__file__).resolve().parent / 'data'
    output.mkdir(exist_ok=True)
    data = {'symbol': 'ROL', 'source': 'Yahoo Finance chart API; dividend/split-adjusted OHLC; historical replay, not live quotes',
            'fetched_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'bars': bars}
    temporary = output / 'rol.partial'
    temporary.write_text(json.dumps(data, allow_nan=False))
    temporary.replace(output / 'rol.json')
    print(f"Saved {len(bars)} real ROL bars: {bars[0]['date']} to {bars[-1]['date']}")


if __name__ == '__main__':
    fetch()
