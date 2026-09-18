"""Check real live telemetry; never injects trades or stimuli."""
import json
import math
from pathlib import Path
import time
import urllib.request

root = Path(__file__).resolve().parent
records = []
seen = set()
deadline = time.monotonic() + 240
while time.monotonic() < deadline:
    with urllib.request.urlopen('http://127.0.0.1:8767/api/state', timeout=5) as response:
        s = json.load(response)
    assert s['status'] != 'error', s.get('message')
    if s.get('step') and s['step'] not in seen:
        seen.add(s['step'])
        from exterminator import order_size, reward_pulse_ms, D
        assert s['next_order_value'] == float(order_size(s['neural'])) or s['done']
        assert math.isclose(s['reward_ms'], s['neural']['stimulus_ms'], abs_tol=1e-7)
        assert 0 <= s['reward_ms'] <= 200
        assert s['cash'] >= 0 and s['shares'] >= 0
        assert sum(s['activity']) == s['neural']['total_spikes']
        for t in s['trades']:
            assert 1 <= t['requested_value'] <= 25
            assert t['signal_date'] < t['date']
            assert math.isclose(t['trade_value'], t['shares'] * t['price'], rel_tol=1e-9)
        records.append(s)
        path = root / 'runs/exterminator/variable-sizing-verification.json'
        path.write_text(json.dumps(records))
        sizes = sorted({t['requested_value'] for t in s['trades']})
        pulses = sorted({r['reward_ms'] for r in records if r['reward_ms'] > 0})
        if len(sizes) >= 2 and len(pulses) >= 2:
            print(json.dumps({'verified': True, 'step': s['step'], 'trade_count': s['trade_count'],
                'actual_order_targets': sizes, 'actual_delivered_pulses_ms': pulses,
                'neurons': s['provenance']['neurons'], 'records': len(records)}), flush=True)
            break
    time.sleep(1)
else:
    raise RuntimeError('Did not observe enough genuine varied trades/rewards within 240 seconds')
