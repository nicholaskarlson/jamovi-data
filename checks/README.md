# Targets

`targets.csv` lists the numbers the two recomputation routes must reproduce.
Each row is one number in a verified record in `expected-results/`.

| Column | Meaning |
| --- | --- |
| `study` | The study, which is also the CSV file's name in `data/` |
| `record_path` | Where the number sits in the study's record, as keys joined by `/` |
| `statistic` | What to compute (see below) |
| `variable` | The CSV column, or `a-b` for column `a` minus column `b` |
| `filter` | Which rows to use: `column=value` conditions joined by `;` (blank means all rows) |
| `value` | The record's value, copied exactly |
| `tolerance` | The largest difference allowed (`0` means an exact match) |

The statistics are `rows`, `columns`, `missing` (blank cells in a column),
`missing_ids` (the first column's value for each blank cell, joined by `;`),
`count` (rows meeting the filter), and `n`, `mean`, `sd`, `se`, `median`,
`minimum`, and `maximum` of the non-missing values. `worked_case` rows are
the Study 03 test results from Chapter 18, which each route computes in its own
`worked_case` function.

The file is built from the records by `scripts/build_targets.py`, and
`scripts/verify_companion.py` rebuilds it on every run and fails if the two
differ. So every value here is the record's own value.
