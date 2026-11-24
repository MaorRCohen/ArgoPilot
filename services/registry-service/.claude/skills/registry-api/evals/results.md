# registry-api evals: results

Date: 2026-11-15. Runs: 3 per eval per config, 24 in total.

| Eval | With skill: runs passed | With skill: checks passed | Without skill: runs passed | Without skill: checks passed |
|---|---|---|---|---|
| 1 farm-plot-count | 3/3 | 18/18 | 3/3 | 18/18 |
| 2 crop-plot-list | 3/3 | 21/21 | 3/3 | 21/21 |
| 3 plot-location-patch | 3/3 | 36/36 | 3/3 | 36/36 |
| 4 negative-soil-water-meaning | 3/3 | 6/6 | 3/3 | 6/6 |
| **Total** | **12/12** | **81/81 (100%)** | **12/12** | **81/81 (100%)** |

Isolation: each run works in its own copy under `/tmp/registry-evals/<run-id>/`, outside the repo, with its own seeded DB, its own uvicorn port, and `claude -p` limited to scoped Read, Edit, Write and Bash (`.venv/bin/python`, `curl`) permissions; the real `registry.db` was checked by `stat` and `git status` before and after the batch, and was unchanged.
