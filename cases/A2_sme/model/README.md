# A2 model files (Zenodo 23229885)

Source: Jurczyk-Bunkowska, M. (2026). *JaamSim models, order portfolios, and replication results for capacity planning in an SME manufacturing system*. Zenodo v1. DOI 10.5281/zenodo.23229885. Licence **CC BY 4.0** (attribution required; redistribution allowed).

Put these files here (download from https://zenodo.org/records/23229885, or run the download cell in `../reproduce.ipynb`, which also checks the MD5):

| File | MD5 (from the Zenodo page; all 7 re-checked after download on 14 Oct) |
|---|---|
| M1_weekly_backlog.cfg | 997a4fcf1fc123eafe8fbeecb64353d8 |
| M2_reference_for_M3.cfg | af62baa3183b4307e6bb9956f68a6c76 |
| M3_weekly_backlog.cfg | f4fc73696ac4ec9cba944ba4b67e0fde |
| portf_norm_clean.tsv | 8196e508e9998827b6a4f2c756fb795b |
| portf_over20_clean.tsv | 3e8caad85102e228bf1771b890919024 |
| M3_norm_30replikacji.rep | 4eec163221cf56ed643ca19f020117f3 |
| M3_over20_30replikacji.rep | eccbe8e883b993874a5903b6f35cffa3 |

The `.rep` files are the published 30-replication results of the authors; the case uses them as the expert reference (mean and spread). M1/M2 `.rep` files are not needed for the case.

Headless run: `bash ../run.sh M3 norm` (after `bash ../setup.sh`).
