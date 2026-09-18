"""Tests for stimulus delivery, using a recording brain double (not trading evidence)."""
from types import SimpleNamespace
import numpy as np
import pytest
from stonkfly.config import Settings
from stonkfly.neural.controller import FlyController


class RecordingBrain:
    def __init__(self):
        self.n, self.dt, self.sim_ms = 3, .1, 0
        self.counts = np.zeros(3, dtype=np.int32)
        self.circuit = {'reward': np.array([0]), 'aversive': np.array([1]), 'kc': np.array([2])}
        self.pulses = []

    def rgb_step(self, rgb, duration, learning, stimulation):
        self.sim_ms += duration
        if stimulation is not None:
            self.pulses.append((duration, stimulation[1]))
        return np.zeros(3, dtype=np.int32), 0

    def memory(self):
        return {}


def controller():
    c = FlyController.__new__(FlyController)
    c.s = Settings()
    c.brain = RecordingBrain()
    c.decoder = SimpleNamespace(decode=lambda counts, seconds: {'side': 'HOLD'})
    return c


def test_variable_pulses_reach_the_brain_without_changing_observation_duration():
    frame = np.zeros((2, 2, 3), dtype=np.uint8)
    for duration in (20., 37.1, 100., 200.):
        c = controller()
        result = c.observe(frame, 'reward', pulse_ms=duration)
        assert result['stimulus_ms'] == duration
        assert sum(p[0] for p in c.brain.pulses) == pytest.approx(duration)
        assert all(p[1] == 20 for p in c.brain.pulses)
        assert c.brain.sim_ms == pytest.approx(500)
    c = controller()
    assert c.observe(frame, 'none', pulse_ms=0)['stimulus_ms'] == 0
    assert not c.brain.pulses
    assert controller().observe(frame, 'reward')['stimulus_ms'] == 200
    for duration in (-1, 201, .15, float('nan'), float('inf')):
        with pytest.raises(ValueError):
            controller().observe(frame, 'reward', pulse_ms=duration)
    with pytest.raises(ValueError):
        controller().observe(frame, 'none', pulse_ms=20)


@pytest.mark.skipif(__import__('os').environ.get('STONKFLY_FULL_TEST') != '1', reason='Full connectome integration')
def test_real_brain_delivers_variable_duration_reward():
    c = FlyController(Settings())
    frame = np.full((180, 320, 3), 255, dtype=np.uint8)
    for duration in (20., 100.):
        result = c.observe(frame, 'reward', pulse_ms=duration)
        assert result['stimulus_ms'] == duration
        assert result['reward_spikes'] > 0
        assert result['total_spikes'] == int(c.brain.counts.sum())
        assert len(c.brain.ids) == 166700
    assert c.brain.sim_ms == 1000
