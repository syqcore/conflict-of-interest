"""Conflict of Interest: paper-only ROL replay with Stonkfly's full connectome."""
from decimal import Decimal
from pathlib import Path
import json

D = Decimal
ROOT = Path(__file__).resolve().parent


def order_size(neural):
    """Fixed readout scaling, not inferred confidence or a profit-based policy."""
    side = neural['side']
    difference = D(str(neural['difference_hz']))
    if side not in ('BUY', 'SELL', 'HOLD') or not difference.is_finite():
        raise ValueError('Invalid neural output')
    if side == 'HOLD':
        return D('0')
    strength = min(D('1'), max(D('0'), (abs(difference) - D('2')) / D('18')))
    return (D('1') + D('24') * strength).quantize(D('.01'))


def reward_pulse_ms(change, previous_equity):
    """0.01% deadband; 1% portfolio gain gives a capped 200 ms pulse."""
    change, previous_equity = D(str(change)), D(str(previous_equity))
    if not change.is_finite() or not previous_equity.is_finite() or previous_equity <= 0:
        raise ValueError('Finite change and positive previous equity required')
    gain = change / previous_equity
    if gain <= D('.0001'):
        return 0.0
    return float((D('200') * min(gain / D('.01'), D('1'))).quantize(D('.1')))


def reward_for(change):
    # No aversive stimulation in this prototype. Food is a visual reward metaphor.
    return 'reward' if change > D('.01') else 'none'


class PaperAccount:
    def __init__(self):
        self.cash = D('100')
        self.shares = D('0')
        self.costs = D('0')

    def equity(self, price):
        return self.cash + self.shares * price

    def execute(self, side, price, requested_value=D('10')):
        price = D(str(price))
        if not price.is_finite() or price <= 0:
            raise ValueError('Positive finite price required')
        requested_value = D(str(requested_value))
        if not requested_value.is_finite() or not 0 <= requested_value <= 25:
            raise ValueError('Order value must be finite and between $0 and $25')
        if requested_value == 0:
            return None
        before_cash = self.cash
        slip, fee = D('.0005'), D('.0005')
        if side == 'BUY' and self.cash > D('.01'):
            spend = min(requested_value, self.cash)
            fill = price * (1 + slip)
            quantity = spend / (fill * (1 + fee))
            paid_fee = quantity * fill * fee
            self.cash -= spend
            self.shares += quantity
        elif side == 'SELL' and self.shares > 0:
            fill = price * (1 - slip)
            quantity = min(self.shares, requested_value / fill)
            paid_fee = quantity * fill * fee
            self.shares -= quantity
            self.cash += quantity * fill - paid_fee
        elif side in ('BUY', 'SELL', 'HOLD'):
            return None
        else:
            raise ValueError('Unknown neural action')
        cost = abs(fill - price) * quantity + paid_fee
        self.costs += cost
        return {'side': side, 'shares': float(quantity), 'price': float(fill), 'cost': float(cost),
                'trade_value': float(quantity * fill), 'cash_change': float(self.cash - before_cash),
                'requested_value': float(requested_value)}


def load_prices(path=ROOT / 'data/rol.json'):
    data = json.loads(path.read_text())
    rows = data['bars']
    if len(rows) < 32 or data['symbol'] != 'ROL':
        raise ValueError('Need at least 32 real ROL bars')
    previous = ''
    for row in rows:
        if row['date'] <= previous:
            raise ValueError('Bars must be chronological and unique')
        previous = row['date']
        for key in ('open', 'close'):
            p = D(str(row[key]))
            if not p.is_finite() or p <= 0:
                raise ValueError('Invalid price')
    return data


class Replay:
    def __init__(self, controller, data):
        self.controller = controller
        self.data = data
        self.reset()

    def reset(self):
        self.controller.brain.reset()
        self.account = PaperAccount()
        self.index = 30
        self.pending = 'HOLD'
        self.pending_size = D('0')
        self.previous_equity = D('100')
        self.food = 0
        self.food_ms = 0.0
        self.history = []
        self.trades = []
        self.last = {}
        self.baseline_shares = D('100') / (D(str(self.data['bars'][30]['open'])) * D('1.0005') * D('1.0005'))

    @property
    def done(self):
        return self.index >= len(self.data['bars'])

    def step(self):
        if self.done:
            return
        from stonkfly.display import market_frame
        import numpy as np
        rows = self.data['bars']
        row = rows[self.index]
        trade = self.account.execute(self.pending, D(str(row['open'])), self.pending_size)
        if trade:
            trade.update(date=row['date'], signal_date=rows[self.index - 1]['date'])
            self.trades.append(trade)
        equity = self.account.equity(D(str(row['close'])))
        change = equity - self.previous_equity
        pulse_ms = reward_pulse_ms(change, self.previous_equity)
        stimulus = 'reward' if pulse_ms else 'none'
        frame = market_frame('ROL / ORKIN', [r['close'] for r in rows[:self.index + 1]],
                             round(row['close'] * .9995, 3), round(row['close'] * 1.0005, 3))
        neural = self.controller.observe(frame, stimulus, pulse_ms=pulse_ms)
        self.food += int(stimulus == 'reward')
        self.food_ms = round(self.food_ms + pulse_ms, 1)
        # Only neural output chooses actions. Execution is delayed to the next open.
        self.pending = neural['side']
        self.pending_size = order_size(neural)
        activity = [int(c.sum()) for c in np.array_split(self.controller.brain.counts, 96)]
        self.last = {'date': row['date'], 'price': row['close'], 'equity': float(equity),
                     'cash': float(self.account.cash), 'shares': float(self.account.shares),
                     'costs': float(self.account.costs), 'change': float(change),
                     'baseline': float(self.baseline_shares * D(str(row['close']))),
                     'food': self.food, 'food_ms': self.food_ms, 'reward_ms': pulse_ms,
                     'return_pct': float(change / self.previous_equity * 100),
                     'neural': neural, 'activity': activity,
                     'next_order_value': float(self.pending_size) if self.index + 1 < len(rows) else 0,
                     'next_action': self.pending if self.index + 1 < len(rows) else 'END',
                     'step': self.index - 29, 'steps': len(rows) - 30}
        self.history.append({k: self.last[k] for k in ('date', 'price', 'equity', 'baseline')})
        self.previous_equity = equity
        self.index += 1
        return self.last

    def snapshot(self):
        return {**self.last, 'history': self.history.copy(), 'trades': self.trades[-100:],
                'trade_count': len(self.trades), 'done': self.done,
                'source': self.data['source'], 'fetched_at': self.data['fetched_at'],
                'range': [self.data['bars'][30]['date'], self.data['bars'][-1]['date']]}


def serve(port=8767):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from types import SimpleNamespace
    import threading
    import time
    import traceback
    from stonkfly.neural.controller import FlyController
    from stonkfly.data import verify

    state = {'status': 'loading', 'message': 'Verifying and loading the full fly connectome...',
             'running': True, 'delay': .2}
    lock = threading.Lock()
    wake = threading.Event()
    commands = []

    def worker():
        try:
            provenance = verify()
            controller = FlyController(SimpleNamespace(learning=True, decoder_threshold_hz=2,
                neural_ms=500, neural_bin_ms=10, pulse_ms=200, pulse_current=20))
            replay = Replay(controller, load_prices())
            while True:
                with lock:
                    batch = commands[:]
                    commands.clear()
                    for command in batch:
                        if command == 'reset':
                            replay.reset()
                            state.clear()
                            state.update(status='ready', running=False, delay=.2)
                        elif command in ('pause', 'play'):
                            state['running'] = command == 'play'
                        elif command.startswith('speed:'):
                            state['delay'] = float(command.split(':')[1])
                    running, delay = state['running'], state['delay']
                    state.update(provenance=provenance)
                if running and not replay.done:
                    replay.step()
                    snapshot = replay.snapshot()
                    with lock:
                        state.update(snapshot, status='ready', message='')
                        if replay.done:
                            state['running'] = False
                    # The only persisted output is local paper-replay telemetry.
                    output = ROOT / 'runs/exterminator'
                    output.mkdir(parents=True, exist_ok=True)
                    temp = output / 'latest.partial'
                    temp.write_text(json.dumps(snapshot, allow_nan=False))
                    temp.replace(output / 'latest.json')
                wake.wait(delay if running else .2)
                wake.clear()
        except Exception as exc:
            traceback.print_exc()
            with lock:
                state.update(status='error', message=str(exc), running=False)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            if self.path == '/api/state':
                with lock:
                    body = json.dumps(state, allow_nan=False).encode()
                kind = 'application/json'
            elif self.path in ('/', '/index.html'):
                body = (ROOT / 'dashboard.html').read_bytes()
                kind = 'text/html; charset=utf-8'
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', kind)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            # Only same-origin browser commands. No accounts, credentials or trading API.
            origin = self.headers.get('Origin')
            if origin and origin != 'http://' + self.headers.get('Host', ''):
                self.send_error(403)
                return
            command = self.path.removeprefix('/api/')
            if command not in ('play', 'pause', 'reset', 'speed:0.2', 'speed:1', 'speed:3'):
                self.send_error(400)
                return
            with lock:
                commands.append(command)
            wake.set()
            self.send_response(202)
            self.send_header('Content-Length', '0')
            self.end_headers()

    threading.Thread(target=worker, daemon=True).start()
    print(f'Conflict of Interest: http://localhost:{port} (paper only)', flush=True)
    ThreadingHTTPServer(('0.0.0.0', port), Handler).serve_forever()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8767)
    serve(parser.parse_args().port)
