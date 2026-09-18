from decimal import Decimal as D
from exterminator import PaperAccount, reward_for


def test_signal_strength_sizes_orders_symmetrically_with_caps():
    from exterminator import order_size
    assert order_size({'side': 'HOLD', 'difference_hz': 50}) == D('0')
    assert order_size({'side': 'BUY', 'difference_hz': 2}) == D('1')
    assert order_size({'side': 'BUY', 'difference_hz': 11}) == D('125.50')
    assert order_size({'side': 'BUY', 'difference_hz': 20}) == D('250')
    assert order_size({'side': 'SELL', 'difference_hz': -11}) == D('125.50')
    assert order_size({'side': 'SELL', 'difference_hz': -200}) == D('250')
    import pytest
    with pytest.raises(ValueError):
        order_size({'side': 'BUY', 'difference_hz': float('nan')})


def test_variable_orders_report_trade_value_separately_from_costs():
    a = PaperAccount()
    small = a.execute('BUY', D('50'), D('1'))
    large = a.execute('BUY', D('50'), D('250'))
    assert a.cash == D('9749')
    assert large['shares'] > small['shares']
    assert 249 < large['trade_value'] < 250
    assert large['cost'] < .3
    assert large['cash_change'] == -250
    assert large['requested_value'] == 250
    sell = a.execute('SELL', D('50'), D('250'))
    assert sell['trade_value'] == 250
    assert sell['cash_change'] > 249
    for _ in range(50):
        a.execute('BUY', D('50'), D('250'))
    assert a.cash >= 0
    for _ in range(50):
        a.execute('SELL', D('50'), D('250'))
    assert a.shares == 0
    import pytest
    for size in ('-1', '251', 'NaN', 'Infinity'):
        with pytest.raises(ValueError):
            a.execute('BUY', D('50'), D(size))


def test_percentage_gains_scale_food_duration_and_cap():
    from exterminator import reward_pulse_ms
    assert reward_pulse_ms(D('.1'), D('100')) == 20
    assert reward_pulse_ms(D('.5'), D('100')) == 100
    assert reward_pulse_ms(D('1'), D('100')) == 200
    assert reward_pulse_ms(D('100'), D('100')) == 200
    assert reward_pulse_ms(D('.2'), D('200')) == 20
    assert reward_pulse_ms(D('-.5'), D('100')) == 0
    assert reward_pulse_ms(D('.01'), D('100')) == 0
    import pytest
    for change, equity in [('NaN', '100'), ('1', '0'), ('1', 'Infinity')]:
        with pytest.raises(ValueError):
            reward_pulse_ms(D(change), D(equity))


def test_buy_sell_is_cash_bounded_and_costs_money():
    a = PaperAccount()
    assert a.equity(D('50')) == D('10000')
    result = a.execute('BUY', D('50'))
    assert result['side'] == 'BUY'
    assert a.cash == D('9990')
    assert 0 < a.shares < D('.2')
    assert a.equity(D('50')) < D('10000')
    for _ in range(1100):
        a.execute('BUY', D('50'))
    assert a.cash >= 0
    for _ in range(1200):
        a.execute('SELL', D('50'))
    assert a.shares == 0
    assert a.cash < D('10000')
    assert a.execute('SELL', D('50')) is None
    assert reward_for(D('.02')) == 'reward'
    assert reward_for(D('-.02')) == 'none'
    assert reward_for(D('.001')) == 'none'


def test_replay_fills_at_next_open_and_future_bars_cannot_change_input():
    # An explicit test double exercises scheduling, not neural profitability.
    import copy
    import numpy as np
    from types import SimpleNamespace
    from exterminator import Replay

    class ControllerDouble:
        def __init__(self):
            self.frames = []
            self.stimuli = []
            self.durations = []
            self.brain = SimpleNamespace(reset=lambda: None, counts=np.zeros(96, dtype=np.int32))

        def observe(self, rgb, stimulus, *, pulse_ms=None):
            self.frames.append(rgb.copy())
            self.stimuli.append(stimulus)
            self.durations.append(pulse_ms)
            return {'side': 'BUY', 'difference_hz': 11}

    data = {'source': 'SYNTHETIC UNIT TEST ONLY', 'fetched_at': 'test', 'bars': [
        {'date': f'{2024 + i // 28}-01-{i % 28 + 1:02}', 'open': 50., 'close': 50.}
        for i in range(33)]}
    other = copy.deepcopy(data)
    other['bars'][31]['open'] = 90
    other['bars'][31]['close'] = 200
    c1, c2 = ControllerDouble(), ControllerDouble()
    first, second = Replay(c1, data), Replay(c2, other)
    first.step()
    second.step()
    assert np.array_equal(c1.frames[0], c2.frames[0])
    assert first.account.cash == 10000
    assert not first.trades
    assert first.pending_size == D('125.50')
    assert c1.durations[-1] == 0
    second.step()
    assert second.trades[0]['date'] == other['bars'][31]['date']
    assert second.trades[0]['signal_date'] == other['bars'][30]['date']
    assert second.trades[0]['price'] == 90 * 1.0005
    assert c2.stimuli[-1] == 'reward'
    assert c2.durations[-1] == __import__('exterminator').reward_pulse_ms(second.last['change'], 10000)
    assert second.trades[0]['requested_value'] == 125.50
    assert second.account.cash == 9874.50
    assert second.last['food_ms'] == c2.durations[-1]
    second.step()
    assert second.done
    before = second.account.cash
    second.step()
    assert second.account.cash == before
    second.reset()
    assert second.account.cash == 10000
    assert second.food == 0 and second.pending == 'HOLD'
    assert second.pending_size == 0 and second.food_ms == 0
    assert not second.trades and not second.history


def test_invalid_prices_and_no_shorting():
    import pytest
    a = PaperAccount()
    for price in ('NaN', 'Infinity', '-1', '0'):
        with pytest.raises(ValueError):
            a.execute('BUY', D(price))
    assert a.execute('SELL', D('50')) is None
    assert a.shares == 0 and a.cash == 10000
