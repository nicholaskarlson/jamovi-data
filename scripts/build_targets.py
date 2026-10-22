#!/usr/bin/env python3
"""Build checks/targets.csv: the numbers both recomputation routes must hit.

Each row names one number in a verified record (expected-results/), copies
the record's value exactly, and says how to recompute it from the study's CSV:

    study, record_path, statistic, variable, filter, value, tolerance

statistic  rows | columns | missing | missing_ids | count | n | mean | sd |
           median | se | minimum | maximum | worked_case
variable   a CSV column, or "a-b" for the difference a minus b
filter     "column=value" conditions joined by ";" (rows kept when all hold)

Version 1.0 covers row counts, missing values, counts, n, means, and SDs for
all twelve studies, and every number in the Study 03 worked case. The other
blocks of the records (ANOVA tables, regressions, and so on) are left for
version 1.1.

Usage:
    python3 scripts/build_targets.py           # rewrite checks/targets.csv
    python3 scripts/build_targets.py --check   # fail if the file is stale
"""

import csv
import io
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TARGETS = ROOT / "checks" / "targets.csv"
FIELDS = ["study", "record_path", "statistic", "variable", "filter", "value", "tolerance"]
NMS = ("n", "mean", "sd")
ALL7 = ("n", "mean", "median", "sd", "se", "minimum", "maximum")

TOL_COUNT = "0"          # counts, row and column numbers, and case lists: exact
TOL_RECORD = "1e-09"     # values the records give to 12 decimal places
TOL_P = "1e-12"          # p values the records give to 16 significant digits
TOL_SW = "1e-08"         # Shapiro-Wilk W and p (the record's came from SciPy)

STUDIES = [
    "study_01_foundations_sleep_stress",
    "study_02_mindfulness_paired",
    "study_03_feedback_two_groups",
    "study_04_practice_spacing_anova",
    "study_05_sleep_strategy_factorial",
    "study_06_mood_repeated",
    "study_07_belonging_survey_regression",
    "study_08_help_seeking_categorical",
    "study_09_skewed_wellbeing_nonparametric",
    "study_10_developmental_emotion_recognition",
    "study_11_single_case_habit_tracking",
    "study_12_reporting_handoff_capstone",
]


def value_text(value):
    if isinstance(value, list):
        return ";".join(value)
    if isinstance(value, str):
        return value
    return json.dumps(value)


class Rows:
    def __init__(self, study, record):
        self.study = study
        self.record = record
        self.rows = []

    def get(self, path):
        node = self.record
        for part in path.split("/"):
            node = node[part]
        return node

    def add(self, path, statistic, variable="", filt="", tolerance=TOL_RECORD):
        value = self.get(path)
        if statistic in ("rows", "columns", "missing", "count", "n", "missing_ids"):
            tolerance = TOL_COUNT
        self.rows.append({
            "study": self.study, "record_path": path, "statistic": statistic,
            "variable": variable, "filter": filt, "value": value_text(value),
            "tolerance": tolerance,
        })

    def common(self):
        self.add("row_count", "rows")
        for column in self.get("missing_counts"):
            self.add(f"missing_counts/{column}", "missing", column)

    def counts(self, block, column):
        for level in self.get(block):
            self.add(f"{block}/{level}", "count", filt=f"{column}={level}")

    def by_group(self, block, variable, column, stats=NMS):
        for level, summary in self.get(block).items():
            for stat in stats:
                assert stat in summary, (self.study, block, level, stat)
                self.add(f"{block}/{level}/{stat}", stat, variable, f"{column}={level}")


def build_rows(root=ROOT):
    out = []
    for study in STUDIES:
        record = json.loads((root / "expected-results" / f"{study}_verified_results.json")
                            .read_text(encoding="utf-8"))
        r = Rows(study, record)
        r.common()
        sid = study[:8]
        if sid == "study_01":
            r.add("column_count", "columns")
            for column in r.get("missing_case_ids"):
                r.add(f"missing_case_ids/{column}", "missing_ids", column)
            for variable in r.get("continuous_descriptives"):
                for stat in NMS:
                    r.add(f"continuous_descriptives/{variable}/{stat}", stat, variable)
            for variable in r.get("categorical_frequencies"):
                r.counts(f"categorical_frequencies/{variable}", variable)
        elif sid == "study_02":
            for variable in r.get("descriptives"):
                source = ("mindfulness_post-mindfulness_pre"
                          if variable == "difference_post_minus_pre" else variable)
                for stat in NMS:
                    r.add(f"descriptives/{variable}/{stat}", stat, source)
        elif sid == "study_03":
            r.counts("group_counts", "feedback_condition")
            for variable in r.get("grouped_descriptives"):
                r.by_group(f"grouped_descriptives/{variable}", variable,
                           "feedback_condition", ALL7)
            add_worked_case(r)
        elif sid == "study_04":
            r.counts("group_counts", "spacing_condition")
            for variable in r.get("grouped_descriptives"):
                r.by_group(f"grouped_descriptives/{variable}", variable, "spacing_condition")
        elif sid == "study_05":
            for cell in r.get("cell_counts"):
                reminder, strategy = cell.split("__")
                cell_filter = f"sleep_reminder={reminder};study_strategy={strategy}"
                r.add(f"cell_counts/{cell}", "count", filt=cell_filter)
                for stat in NMS:
                    r.add(f"cell_descriptives/{cell}/{stat}", stat, "recall_score", cell_filter)
            for factor, levels in r.get("marginal_means").items():
                for level in levels:
                    r.add(f"marginal_means/{factor}/{level}", "mean", "recall_score",
                          f"{factor}={level}")
        elif sid == "study_06":
            r.counts("group_counts", "support_group")
            for group, weeks in r.get("group_week_descriptives").items():
                for week in weeks:
                    for stat in NMS:
                        r.add(f"group_week_descriptives/{group}/{week}/{stat}", stat, week,
                              f"support_group={group}")
            for week in r.get("overall_time_means"):
                r.add(f"overall_time_means/{week}", "mean", week)
        elif sid == "study_07":
            for variable in r.get("descriptives"):
                for stat in NMS:
                    r.add(f"descriptives/{variable}/{stat}", stat, variable)
        elif sid == "study_08":
            r.counts("message_counts", "message_condition")
            r.counts("resource_counts", "resource_choice")
            for message, cells in r.get("contingency_table").items():
                for resource in cells:
                    r.add(f"contingency_table/{message}/{resource}/observed", "count",
                          filt=f"message_condition={message};resource_choice={resource}")
        elif sid == "study_09":
            r.counts("group_counts", "app_use_group")
            r.by_group("grouped_descriptives", "wellbeing_score", "app_use_group")
            for group in r.get("flagged_outliers"):
                r.add(f"flagged_outliers/{group}", "count",
                      filt=f"app_use_group={group};outlier_flag=yes")
        elif sid == "study_10":
            r.counts("group_counts", "age_group")
            r.by_group("grouped_descriptives", "emotion_accuracy", "age_group")
        elif sid == "study_11":
            r.counts("phase_counts", "phase")
            for variable in r.get("phase_descriptives"):
                r.by_group(f"phase_descriptives/{variable}", variable, "phase")
            for phase, ratings in r.get("stress_rating_phase_frequencies").items():
                for rating in ratings:
                    r.add(f"stress_rating_phase_frequencies/{phase}/{rating}", "count",
                          filt=f"phase={phase};stress_rating={rating}")
        elif sid == "study_12":
            r.counts("project_stage_counts", "project_stage")
            r.counts("report_decision_counts", "report_decision")
            r.counts("quality_rating_distribution", "evidence_quality_rating")
            for stat in NMS:
                r.add(f"quality_rating_overall/{stat}", stat, "evidence_quality_rating")
            r.by_group("quality_rating_by_stage", "evidence_quality_rating", "project_stage")
            for stage, decisions in r.get("stage_by_decision").items():
                for decision in decisions:
                    r.add(f"stage_by_decision/{stage}/{decision}/count", "count",
                          filt=f"project_stage={stage};report_decision={decision}")
        out.extend(r.rows)
    return out


def add_worked_case(r):
    """Every number in the Study 03 test block (Chapter 18)."""
    block = "independent_samples_t_test"
    test = r.get(block)
    for key, value in test.items():
        if key == "direction":
            continue
        if key == "levene_brown_forsythe":
            for part in ("f", "df1", "df2", "p"):
                tol = TOL_P if part == "p" else TOL_RECORD
                r.add(f"{block}/{key}/{part}", "worked_case", f"{key}/{part}", tolerance=tol)
        elif key == "group_shapiro_wilk":
            for group in ("process_feedback", "outcome_feedback"):
                for part in ("w", "p"):
                    r.add(f"{block}/{key}/{group}/{part}", "worked_case",
                          f"{key}/{group}/{part}", tolerance=TOL_SW)
        else:
            tol = TOL_P if isinstance(value, str) else TOL_RECORD
            r.add(f"{block}/{key}", "worked_case", key, tolerance=tol)


def render(rows):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def main(argv):
    data = render(build_rows())
    count = data.count(b"\n") - 1
    if "--check" in argv:
        if not TARGETS.exists() or TARGETS.read_bytes() != data:
            print("checks/targets.csv is stale: run python3 scripts/build_targets.py")
            return 1
        print(f"TARGETS_CURRENT rows={count}")
        return 0
    TARGETS.parent.mkdir(exist_ok=True)
    TARGETS.write_bytes(data)
    print(f"wrote checks/targets.csv rows={count}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
