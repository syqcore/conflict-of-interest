# Conflict of Interest

**A fly trading the company paid to kill it.**

A rough, paper-only Rollins (ROL / Orkin) trading dashboard powered by the full MaleCNS v1.0 fly-connectome simulation. Based on [Alex Wormuth's Stonkfly](https://github.com/nftechie/stonkfly), with its MIT license and attribution retained.

- 166,700 simulated neurons and 25,582,938 retained connections.
- Real historical ROL prices, $10,000 fake money, next-open fills.
- Neural-output strength sets $1–$250 order targets, limited by cash and shares.
- Percentage portfolio gains trigger proportional dopamine pulses, up to 200 ms.
- Dashboard: portfolio versus buy-and-hold, neural activity, food pulses, trade values, pause/reset.

## Run

Python 3.11+, a C++17 compiler, and several GB of disk space. 16 GB RAM recommended.

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements-paper.txt
.venv/bin/python -c 'from stonkfly.data import prepare; prepare()'
.venv/bin/python fetch_rol.py
.venv/bin/python exterminator.py --port 8767
```

Open **http://localhost:8767**. The first preparation downloads about 1.1 GB of checksum-locked connectome sources. Prices and all run output stay local and are Git-ignored. The dashboard binds all interfaces for trusted-LAN use; don't expose it publicly without access control.

## Verify

```bash
.venv/bin/python -m pytest tests/test_exterminator.py tests/test_variable_pulse.py tests/test_neural.py -q
# Includes actual full-connectome tests after preparing the dataset:
STONKFLY_FULL_TEST=1 .venv/bin/python -m pytest tests/test_exterminator.py tests/test_variable_pulse.py tests/test_neural.py -q
```

This isn't evidence of profitable learning, faithful fly cognition, consciousness, or experienced hunger. "Food" is a graphical representation of engineered reinforcement. Signal strength isn't calibrated confidence.

See [prototype details](PROTOTYPE.md), [model assumptions](docs/model.md), and [third-party credits](THIRD_PARTY.md). The upstream Coinbase modules remain for provenance; **this dashboard never imports or invokes the broker execution path**. Original Stonkfly documentation is preserved [here](docs/upstream-readme.md).
