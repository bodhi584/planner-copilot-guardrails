# Third-party models and data

The MIT licence above covers the code written for this project. The simulation models and data below belong to their authors and keep their own licences.

| Case | Material | Author | Licence | In this repository |
|---|---|---|---|---|
| A1 | SMT2020 simulator (RL4SemiconductorFabSched, commit `89467c6`) | Tassel et al. | MIT | downloaded by `setup.sh`; stored run results in `precomputed/` |
| A1 | Published results, Table 1 | Tassel et al. (2023), Proc. WSC | — | values in `paper_table1.json` |
| A2 | JaamSim models, order portfolios, replication results (Zenodo 10.5281/zenodo.23229885) | M. Jurczyk-Bunkowska | CC BY 4.0 | `cases/A2_sme/model/`, unchanged |
| A2 | JaamSim simulation software | JaamSim Software Inc. | Apache 2.0 | downloaded and built by `setup.sh` |
| A3 | Warehouse model and results (Zenodo 10.5281/zenodo.21469786) | Saengphueng (2026) | MIT | `cases/A3_warehouse/model/` with its `LICENSE.txt` |
| A5 | Model description and published results | M. S. Seppanen (2005), Proc. WSC | — | rebuilt from the paper in `cases/A5_operator_line/model.py` |
