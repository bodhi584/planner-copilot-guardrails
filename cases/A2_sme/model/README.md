# A2 model files (Zenodo 23229885)

Source: Jurczyk-Bunkowska, M. (2026). *JaamSim models, order portfolios, and replication results for capacity planning in an SME manufacturing system*. Zenodo v1. DOI 10.5281/zenodo.23229885. Licence **CC BY 4.0** (attribution required; redistribution allowed).

Files copied unchanged from https://zenodo.org/records/23229885 (CC BY 4.0). MD5 checksums as listed on the record:

| File | MD5 (as on the Zenodo record, re-checked) |
|---|---|
| M3_weekly_backlog.cfg | f4fc73696ac4ec9cba944ba4b67e0fde |
| portf_norm_clean.tsv | 8196e508e9998827b6a4f2c756fb795b |
| portf_over20_clean.tsv | 3e8caad85102e228bf1771b890919024 |
| M3_norm_30replikacji.rep | 4eec163221cf56ed643ca19f020117f3 |
| M3_over20_30replikacji.rep | eccbe8e883b993874a5903b6f35cffa3 |

The `.rep` files are the published 30-replication results of the authors; the case uses them as the expert reference (mean and spread). The simpler model variants M1 and M2 are not used and not included.

Headless run: `bash ../run.sh M3 norm` (after `bash ../setup.sh`). Reproduction: `python ../reproduce.py`.
