#!/usr/bin/env bash
# Sets up the SMT2020 simulator with Python 3.9 next to this file. Works on Google Colab and Linux.
set -e
cd "$(dirname "$0")"
if [ ! -d RL4SemiconductorFabSched ]; then
  git clone https://github.com/ingambe/RL4SemiconductorFabSched
  (cd RL4SemiconductorFabSched && git checkout 89467c6a14931a8e9e33f66af29b91b1ed72f929)
fi
(cd RL4SemiconductorFabSched/simulation/es && for z in 365days_*.pkl.zip; do [ -f "${z%.zip}" ] || unzip -o -q "$z"; done)
pip -q install uv
uv python install 3.9
uv venv --python 3.9 .venv
uv pip install --python .venv/bin/python numpy==1.22.4 cloudpickle==2.1.0
echo "Setup done. Test: .venv/bin/python run_static.py --dataset HVLM --rule fifo --days 30"
