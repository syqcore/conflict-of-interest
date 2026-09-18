# Conflict of Interest

A rough, working paper-trading dashboard. A simulated fly trades Rollins (ROL), owner of Orkin. Built on nftechie/stonkfly, retaining its complete MaleCNS v1.0 graph and fixed neural decoder.

## Run

From this directory:

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python numpy==2.4.6 pandas==3.0.6 pyarrow==25.0.1 Pillow==12.3.0 pytest==9.1.1 python-dotenv==1.2.3
.venv/bin/python -c 'from stonkfly.data import prepare; prepare()'
.venv/bin/python fetch_rol.py
.venv/bin/python exterminator.py --port 8767
```

Open http://localhost:8767 on the server. It binds 0.0.0.0 for a trusted LAN; there's no authentication. Don't expose publicly without access control. Downloads about 1.1 GB of checksum-locked source data and compiles the C++ brain kernel. Needs a C++17 compiler. The separate dashboard does NOT import or use any brokerage/AgentKit execution code.

## What actually happens

- 30 daily bars warm up the chart, followed by historical ROL replay.
- Real Yahoo daily bars, with dividend/split adjustment applied consistently to opens and closes. This is retrospective adjusted data, not point-in-time feed validation.
- Only the current and earlier closes reach the RGB sensory input. A decision at a day's close executes at the following open. No future bar enters that decision.
- Full 166,700-neuron / 25,582,938-edge network. Stonkfly's fixed DNp20 / DNpe017 decoder chooses BUY, SELL or HOLD.
- $10,000 paper capital, fractional shares, $1–$250 neural-strength target order, cash and inventory limits. No shorting, leverage, deposits, credentials or real-order integration.
- Target size uses the absolute DNp20 right-minus-left firing-rate gap: $1 at 2 Hz, linearly up to $250 at 20 Hz, capped beyond. HOLD is $0. Side and size are frozen at signal time, before the next open. Cash/inventory limits may reduce fills below $1. Reward does not directly set order size; it enters the brain as input. Signal strength is not calibrated confidence.
- Trade value is shares times fill price, separate from fees plus slippage. BUY targets include fees; SELL targets are gross notional.
- Assumed costs: 0.05% slippage plus 0.05% fee each side. These are illustrative, not calibrated brokerage costs.
- Net portfolio returns above 0.01% produce a proportional engineered reward pulse on the next observation: 0.1% gain = 20 ms, 0.5% = 100 ms, 1% or more = 200 ms. Current amplitude stays at 20 model units; duration varies at 0.1 ms resolution. No aversive input. Food graphics reflect delivered reward events, not actual hunger or pleasure.
- Buy-and-hold baseline starts at the first replay day's open, with identical entry costs. Both series are marked to close without exit costs.
- Chart, trade feed, spike counts and heatmap use the running simulation. Fly illustration and neuron-bin arrangement are not anatomy.
- Pause finishes the current neural step, then stops. Reset clears learned state, pending action, paper account and history, and leaves replay paused.
- Local latest telemetry: `runs/exterminator/latest.json`. Restart starts a fresh run; brain checkpoints are not resumed by this prototype.

## Tests

```bash
.venv/bin/python -m pytest tests/test_exterminator.py tests/test_variable_pulse.py tests/test_neural.py -q
STONKFLY_FULL_TEST=1 .venv/bin/python -m pytest tests/test_exterminator.py tests/test_variable_pulse.py tests/test_neural.py -q
```

The upstream exchange tests require additional Coinbase dependencies from its pyproject.toml; those aren't needed for this paper-only dashboard.

## Verdict: PARTIAL

The full brain drives real paper trades and reward feedback with a working dashboard. This does not demonstrate profitable learning, accurate fly cognition, or an investable strategy. The underlying physiology and plasticity contain explicit modeling assumptions documented upstream in docs/model.md. Prototype scope only: no durable checkpoint recovery, no formal strategy validation, no public-hosting security.
