# Corrected E03 diagnostic — 2026-10-05

100 seeds; 6,000 paired tasks; 30,000 episodes; zero failures.
Seven tests passed. The trajectory audit verified completeness, candidate filtering, source hashes, summaries and exact adaptive/static_mix query equivalence.

| Condition | uniform | fixed | static_mix | adaptive | discounting |
|---|---:|---:|---:|---:|---:|
| matched | 8.92 | 8.668 | 8.6665 | 8.6665 | 8.644 |
| shifted | 9.1315 | 9.7585 | 9.6545 | 9.6545 | 9.516 |
| neutral | 8.8665 | 9.0945 | 9.0495 | 9.0495 | 8.934 |

Adaptive is equivalent to the static initial mixture; no added capability is demonstrated. Discounting mitigates negative transfer but still requires more queries than uniform on shifted and neutral tasks. These are descriptive results on previously examined seeds, not a fresh confirmatory study.

Raw trajectories are losslessly gzip-compressed. From experiments/e03 run: `python3 verify_corrected.py results_corrected_20261005`.
