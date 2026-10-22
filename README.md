# jamovi-data

Data, verified results, and checks for Nicholas Elliott Karlson's
*Psychology Research Methods and Statistics by Design with Jamovi: From
Scientific Questions to APA-Style Results and Reproducible Evidence*
(NEKpress Research: Proof-First Guides, 2026; paperback ISBN 979-8194435470).

The book works through twelve studies in jamovi Desktop. This repository holds
what a reader needs for them: a CSV file and a data dictionary for each study,
each study's verified result record, the analysis matrix, and the six figures
printed in the book. It also holds checks that recompute 326 of the recorded
numbers from the CSV files by two routes, standard-library Python and base R,
which share no code.

All twelve datasets are synthetic teaching data. They describe no real people.

## Start here

1. Download this repository with **Code > Download ZIP** and unzip it, or run
   `git clone https://github.com/nicholaskarlson/jamovi-data`.
2. Open jamovi Desktop, open its main menu, choose **Open**, and browse to a
   CSV file in the `data` folder. Chapter 18, for example, uses
   `data/study_03_feedback_two_groups.csv`.
3. Before analyzing, read the study's dictionary in `data/dictionaries/`. It
   gives each variable's role, measurement level, allowed values, and missing
   values.
4. Compare your jamovi output with the study's record in `expected-results/`,
   which holds the book's numbers at full precision.

No account, sign-in, or prepared jamovi file is needed.

## The twelve studies

| CSV file in `data/` | Rows | Chapters | Analyses |
| --- | ---: | --- | --- |
| `study_01_foundations_sleep_stress.csv` | 120 | 1–7 | Import, measurement levels, missing values, descriptives, plots |
| `study_02_mindfulness_paired.csv` | 72 | 8–11, 17 | Sampling variability, paired-samples t test, effect size, power |
| `study_03_feedback_two_groups.csv` | 96 | 16, 18 | Independent-samples t test (Welch and Student), effect size |
| `study_04_practice_spacing_anova.csv` | 120 | 19 | One-way ANOVA, post hoc comparisons |
| `study_05_sleep_strategy_factorial.csv` | 160 | 20 | Factorial ANOVA, interaction |
| `study_06_mood_repeated.csv` | 84 | 21 | Repeated-measures and mixed ANOVA |
| `study_07_belonging_survey_regression.csv` | 180 | 12–15 | Correlation, simple and multiple regression |
| `study_08_help_seeking_categorical.csv` | 150 | 22 | Contingency table, chi-square test |
| `study_09_skewed_wellbeing_nonparametric.csv` | 132 | 23 | Kruskal–Wallis test, Mann–Whitney comparisons with Holm correction |
| `study_10_developmental_emotion_recognition.csv` | 144 | 24 | One-way ANOVA, ANCOVA, limits of a quasi-experiment |
| `study_11_single_case_habit_tracking.csv` | 42 | 25 | Single-case phases, nonoverlap of all pairs |
| `study_12_reporting_handoff_capstone.csv` | 60 | 26–27 | Reporting audit, reproducible handoff |

`ANALYSIS_MATRIX.md` gives each study's workflows and result fields.

| Path | Contents |
| --- | --- |
| `data/` | The twelve CSV files, with `PROVENANCE.md`, `README.md`, and `SHA256SUMS` |
| `data/dictionaries/` | One JSON dictionary for each study |
| `expected-results/` | One verified result record for each study (JSON), with `SHA256SUMS` |
| `figures/generated/` | The six figures printed in the book (PNG); `figures/README.md` describes them |
| `ANALYSIS_MATRIX.md` | Which chapters use which study, and how |
| `checks/targets.csv` | The 326 recorded numbers the checks recompute, with how to compute each |
| `scripts/` | The checks |
| `SOURCE.json` | Where the book's files were copied from, with each file's SHA-256 hash |

## Check the files and recompute the numbers

You need Python 3.9 or later, and R for the third command. Nothing else is
installed: the checks use no packages. From the repository's folder:

```bash
python3 scripts/verify_companion.py
python3 scripts/recompute.py
Rscript scripts/recompute.R
```

On Windows, type `py` (or `python`) in place of `python3`. None of the commands
writes a file.

| Command | What it does | Last line when all is well |
| --- | --- | --- |
| `verify_companion.py` | Confirms that every file matches `SHA256SUMS`, that the book's files are unchanged copies of the source in `SOURCE.json`, that each record names its own CSV and dictionary, and that every target is the record's own value. | `JAMOVI_DATA_BOUNDARY_OK` |
| `recompute.py` | Recomputes all 326 targets from the CSV files with new standard-library Python code, including the incomplete beta function and the Shapiro–Wilk test. | `JAMOVI_DATA_PYTHON_OK targets=326 worked_case=22` |
| `recompute.R` | Recomputes the same targets with base R's own `t.test()`, `shapiro.test()`, and `lm()`. | `JAMOVI_DATA_R_OK targets=326 worked_case=22` |

In version 1.0 the targets cover:

- **All twelve studies:** row counts; missing values in every column, with
  Study 01's missing case IDs; group, cell, and category counts; and n, mean,
  and SD for every summarized variable and group.
- **The Study 03 worked case (Chapter 18), in full:** group summaries (n,
  mean, median, SD, SE, minimum, maximum) for both outcomes; Welch's and
  Student's t tests with p values and 95% confidence intervals; Cohen's d and
  Hedges' g; the Brown–Forsythe test of equal variances; and a Shapiro–Wilk
  test in each group.

The other parts of the records (ANOVA tables, regressions, chi-square and rank
tests, single-case summaries) are planned for version 1.1.

Both routes print the worked case the same way:

```text
Worked case, Study 03 (Chapter 18): motivation_score, process minus outcome feedback
  Mean difference                5.389583
  Standard error                 1.596200
  Welch t                        3.376510
  Welch df                      93.998158
  Welch p                        0.001069
  Welch 95% CI lower             2.220291
  Welch 95% CI upper             8.558876
  Student t                      3.376510
  Student df                    94.000000
  Student p                      0.001069
  Cohen's d                      0.689227
  Hedges' g                      0.683713
  Brown-Forsythe F               0.821105
  Brown-Forsythe p               0.367174
  Shapiro-Wilk W, process        0.963748
  Shapiro-Wilk p, process        0.143035
  Shapiro-Wilk W, outcome        0.970024
  Shapiro-Wilk p, outcome        0.253874
```

Counts must match exactly. Values the records give to 12 decimal places must
match within 1e-9, and p values given to 16 significant digits within 1e-12.
The records' Shapiro–Wilk values were computed with SciPy, and other
implementations of the same algorithm can differ from them around the tenth
decimal place, so those four values must match within 1e-8. `checks/README.md` explains the targets file.

`python3 tests/test_checks_catch_errors.py` shows that the checks fail when
they should: it alters a copy of the repository (a score moved by 0.1, a target
changed, a byte added to a figure) and confirms each change is caught.

## This repository and github.com/nicholaskarlson/data

The book prints `github.com/nicholaskarlson/data`, and that address keeps
working unchanged. It also carries companions for other books. This repository
holds only Book 2's reader files, as byte-for-byte copies of `data` at commit
`0cd74cb` (release line `reader-assets-v1.0.3`), and adds the checks above.
`SOURCE.json` lists each copied file with its SHA-256 hash, and
`verify_companion.py` confirms them on every run. The copies are never edited
here; if a file changes at the source, the new file is copied in a new tagged
version.

Corrections to the book are recorded in the
[errata](https://github.com/nicholaskarlson/data/blob/main/ERRATA.md), where you
can also report one. For a problem with the checks here, open an issue in this
repository.

## Software

The records were checked against jamovi Desktop 28.2 with the bundled jmv
module 28.2.0; each record's `software_provenance` gives the details. The name
jamovi is a trademark of the jamovi project. This repository, like the book, is
an independent educational work and is not affiliated with or endorsed by the
jamovi project.

## License and citation

The data, dictionaries, records, figures, and documentation are licensed under
CC BY 4.0, and the scripts under the MIT License (`LICENSE-CODE`). See
`LICENSES.md`. The book's text is not covered.

Please cite the book when you use these files. `CITATION.cff` gives the
details for the book and for this repository.
