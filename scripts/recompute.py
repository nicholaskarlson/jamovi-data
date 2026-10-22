#!/usr/bin/env python3
"""Standard-library Python route: recompute the targets from the CSV files.

Reads checks/targets.csv, recomputes every number from the twelve CSV files
in data/, and compares each with the verified record's value. The Study 03
worked case (Chapter 18) is recomputed step by step in worked_case() below.

Needs only Python 3.9 or later; nothing to install. Writes nothing.

    python3 scripts/recompute.py

The last line is JAMOVI_DATA_PYTHON_OK when every number matches.
"""

import csv
import math
import pathlib
import platform
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import stdlib_stats as st  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames, list(reader)


def keep(rows, condition):
    """Rows meeting every "column=value" condition in a ";"-joined filter."""
    for part in condition.split(";") if condition else []:
        column, level = part.split("=", 1)
        rows = [row for row in rows if row[column] == level]
    return rows


def values(rows, variable):
    """Non-missing numbers in a column, or the difference "a-b" of two."""
    if "-" in variable:
        first, second = variable.split("-")
        return [float(r[first]) - float(r[second]) for r in rows
                if r[first] != "" and r[second] != ""]
    return [float(r[variable]) for r in rows if r[variable] != ""]


def descriptive(target, header, rows):
    stat, variable = target["statistic"], target["variable"]
    if stat == "rows":
        return len(rows)
    if stat == "columns":
        return len(header)
    if stat == "missing":
        return sum(1 for r in rows if r[variable] == "")
    if stat == "missing_ids":
        return ";".join(r[header[0]] for r in rows if r[variable] == "")
    chosen = keep(rows, target["filter"])
    if stat == "count":
        return len(chosen)
    x = values(chosen, variable)
    if stat == "n":
        return len(x)
    if stat == "mean":
        return st.mean(x)
    if stat == "sd":
        return st.sample_sd(x)
    if stat == "se":
        return st.sample_sd(x) / math.sqrt(len(x))
    if stat == "median":
        return st.median(x)
    if stat == "minimum":
        return min(x)
    if stat == "maximum":
        return max(x)
    raise ValueError(f"unknown statistic {stat}")


def worked_case(rows):
    """Study 03, Chapter 18: motivation_score, process minus outcome feedback."""
    a = values(keep(rows, "feedback_condition=process_feedback"), "motivation_score")
    b = values(keep(rows, "feedback_condition=outcome_feedback"), "motivation_score")
    n1, n2 = len(a), len(b)
    m1, m2 = st.mean(a), st.mean(b)
    v1, v2 = st.sample_sd(a) ** 2, st.sample_sd(b) ** 2
    diff = m1 - m2

    # Student's t: one pooled variance for both groups.
    df = n1 + n2 - 2
    pooled_sd = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / df)
    se = pooled_sd * math.sqrt(1 / n1 + 1 / n2)
    t_student = diff / se
    q_student = st.t_quantile(0.975, df)

    # Welch's t: each group keeps its own variance; Welch-Satterthwaite df.
    se_welch = math.sqrt(v1 / n1 + v2 / n2)
    t_welch = diff / se_welch
    df_welch = (v1 / n1 + v2 / n2) ** 2 / ((v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1))
    q_welch = st.t_quantile(0.975, df_welch)

    # Effect sizes: d uses the pooled SD; g applies the small-sample factor.
    d = diff / pooled_sd
    g = d * (1 - 3 / (4 * df - 1))

    # Brown-Forsythe test of equal variances: a one-way ANOVA on the
    # absolute distances from each group's median.
    groups = [[abs(x - st.median(grp)) for x in grp] for grp in (a, b)]
    grand = st.mean(groups[0] + groups[1])
    ss_between = math.fsum(len(z) * (st.mean(z) - grand) ** 2 for z in groups)
    ss_within = math.fsum((x - st.mean(z)) ** 2 for z in groups for x in z)
    df1, df2 = len(groups) - 1, n1 + n2 - len(groups)
    f = (ss_between / df1) / (ss_within / df2)

    w_a, p_a = st.shapiro_wilk(a)
    w_b, p_b = st.shapiro_wilk(b)
    return {
        "mean_difference": diff,
        "pooled_standard_error": se,
        "student_t": t_student,
        "student_df": df,
        "student_two_sided_p": st.t_two_sided_p(t_student, df),
        "student_ci_95_lower": diff - q_student * se,
        "student_ci_95_upper": diff + q_student * se,
        "welch_t": t_welch,
        "welch_df": df_welch,
        "welch_two_sided_p": st.t_two_sided_p(t_welch, df_welch),
        "welch_ci_95_lower": diff - q_welch * se_welch,
        "welch_ci_95_upper": diff + q_welch * se_welch,
        "cohens_d": d,
        "hedges_g": g,
        "levene_brown_forsythe/f": f,
        "levene_brown_forsythe/df1": df1,
        "levene_brown_forsythe/df2": df2,
        "levene_brown_forsythe/p": st.f_upper_p(f, df1, df2),
        "group_shapiro_wilk/process_feedback/w": w_a,
        "group_shapiro_wilk/process_feedback/p": p_a,
        "group_shapiro_wilk/outcome_feedback/w": w_b,
        "group_shapiro_wilk/outcome_feedback/p": p_b,
    }


LABELS = [
    ("mean_difference", "Mean difference"),
    ("pooled_standard_error", "Standard error"),
    ("welch_t", "Welch t"),
    ("welch_df", "Welch df"),
    ("welch_two_sided_p", "Welch p"),
    ("welch_ci_95_lower", "Welch 95% CI lower"),
    ("welch_ci_95_upper", "Welch 95% CI upper"),
    ("student_t", "Student t"),
    ("student_df", "Student df"),
    ("student_two_sided_p", "Student p"),
    ("cohens_d", "Cohen's d"),
    ("hedges_g", "Hedges' g"),
    ("levene_brown_forsythe/f", "Brown-Forsythe F"),
    ("levene_brown_forsythe/p", "Brown-Forsythe p"),
    ("group_shapiro_wilk/process_feedback/w", "Shapiro-Wilk W, process"),
    ("group_shapiro_wilk/process_feedback/p", "Shapiro-Wilk p, process"),
    ("group_shapiro_wilk/outcome_feedback/w", "Shapiro-Wilk W, outcome"),
    ("group_shapiro_wilk/outcome_feedback/p", "Shapiro-Wilk p, outcome"),
]


def matches(target, computed):
    if target["statistic"] == "missing_ids":
        return computed == target["value"]
    return abs(float(computed) - float(target["value"])) <= float(target["tolerance"])


def main():
    print(f"Standard-library Python route (Python {platform.python_version()})")
    _, targets = read_csv(ROOT / "checks" / "targets.csv")
    studies = list(dict.fromkeys(t["study"] for t in targets))
    failures, worked = [], {}
    for study in studies:
        header, rows = read_csv(ROOT / "data" / f"{study}.csv")
        mine = [t for t in targets if t["study"] == study]
        case = worked_case(rows) if any(t["statistic"] == "worked_case" for t in mine) else {}
        good = 0
        for target in mine:
            if target["statistic"] == "worked_case":
                computed = case[target["variable"]]
                worked[target["variable"]] = computed
            else:
                computed = descriptive(target, header, rows)
            if matches(target, computed):
                good += 1
            else:
                failures.append((study, target["record_path"], computed, target["value"]))
        print(f"{study:<44s} {good:>3d} of {len(mine):>3d} match")

    print("Worked case, Study 03 (Chapter 18): motivation_score, process minus outcome feedback")
    for key, label in LABELS:
        print(f"  {label:<26s} {worked[key]:>12.6f}")
    for study, path, computed, expected in failures:
        print(f"MISMATCH {study} {path}: recomputed {computed!r}, record {expected}")
    if failures:
        print(f"JAMOVI_DATA_PYTHON_FAILED mismatches={len(failures)}")
        return 1
    print(f"JAMOVI_DATA_PYTHON_OK targets={len(targets)} worked_case={len(worked)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
