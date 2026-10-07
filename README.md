# NOESIS

Experimental code for active queries, transfer, persistent memory and adaptive
reasoning. Python standard library. These are finite synthetic experiments, not
a general AI or a validated model of the human brain.

| Experiment | Question | Finding / status |
|---|---|---|
| E01 | Choose informative queries? | 18.51% fewer queries than random on the declared benchmark; higher internal compute. |
| E02 | Transfer a learned prior? | Benefit on matched tasks; harm on shifted and neutral tasks. |
| E03 | Adapt trust within a task? | Corrected Bayesian implementation equals a static initial mixture; no extra capability demonstrated. |
| E04 | Retain and discount experience across tasks? | Recency beats accumulation on changing streams; accumulation wins on stable streams. |
| E05 | Learn weights across memory timescales and persist the engine? | 16 tests; 96,000 episodes. Beats static mixing, but not clearly recency; overall research gate failed. |

## Current milestone

[E05 instructions, API and demo](experiments/e05/README_GR.md) ·
[Protocol](experiments/e05/PROTOCOL.md) ·
[Results](experiments/e05/results_01/REPORT_GR.md) ·
[Research roadmap in Greek](docs/ROADMAP_GR.md)

```bash
cd experiments/e05
python3 -m unittest discover -s tests -v
python3 -m noesis --demo --tasks 20 --state-out my_memory.json
python3 -m noesis --demo --tasks 20 --state-in my_memory.json --state-out my_memory.json
```

Each experiment is isolated and keeps its own code, protocol and results.
Run commands from its directory. No API keys, pip dependencies or GPU required.
All research claims are limited to the tested grammar and sampling procedure.
