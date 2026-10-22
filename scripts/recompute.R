#!/usr/bin/env Rscript
# Base-R route: recompute the targets from the CSV files.
#
# Reads checks/targets.csv, recomputes every number from the twelve CSV files
# in data/, and compares each with the verified record's value. The Study 03
# worked case (Chapter 18) uses R's own t.test(), shapiro.test(), and lm(),
# so this route shares no code with the standard-library Python route.
#
# Needs only base R (any recent version); no packages. Writes nothing.
#
#     Rscript scripts/recompute.R
#
# The last line is JAMOVI_DATA_R_OK when every number matches.

args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grepl("^--file=", args)])
if (length(file_arg) != 1L) stop("Run this script with Rscript.")
root <- normalizePath(file.path(dirname(file_arg), ".."))

read_study <- function(study) {
  # Every column as text, blank cells as missing, column names unchanged.
  read.csv(file.path(root, "data", paste0(study, ".csv")),
           colClasses = "character", na.strings = "", check.names = FALSE)
}

keep <- function(d, condition) {
  # Rows meeting every "column=value" condition in a ";"-joined filter.
  if (!nzchar(condition)) return(d)
  for (part in strsplit(condition, ";", fixed = TRUE)[[1]]) {
    pair <- strsplit(part, "=", fixed = TRUE)[[1]]
    column <- d[[pair[1]]]
    d <- d[!is.na(column) & column == pair[2], , drop = FALSE]
  }
  d
}

values <- function(d, variable) {
  # Non-missing numbers in a column, or the difference "a-b" of two.
  if (grepl("-", variable, fixed = TRUE)) {
    pair <- strsplit(variable, "-", fixed = TRUE)[[1]]
    x <- as.numeric(d[[pair[1]]]) - as.numeric(d[[pair[2]]])
  } else {
    x <- as.numeric(d[[variable]])
  }
  x[!is.na(x)]
}

descriptive <- function(target, d) {
  stat <- target$statistic
  variable <- target$variable
  if (stat == "rows") return(nrow(d))
  if (stat == "columns") return(ncol(d))
  if (stat == "missing") return(sum(is.na(d[[variable]])))
  if (stat == "missing_ids") return(paste(d[[1]][is.na(d[[variable]])], collapse = ";"))
  chosen <- keep(d, target$filter)
  if (stat == "count") return(nrow(chosen))
  x <- values(chosen, variable)
  switch(stat,
         n = length(x),
         mean = mean(x),
         sd = sd(x),
         se = sd(x) / sqrt(length(x)),
         median = median(x),
         minimum = min(x),
         maximum = max(x),
         stop("unknown statistic ", stat))
}

worked_case <- function(d) {
  # Study 03, Chapter 18: motivation_score, process minus outcome feedback.
  a <- values(keep(d, "feedback_condition=process_feedback"), "motivation_score")
  b <- values(keep(d, "feedback_condition=outcome_feedback"), "motivation_score")
  n1 <- length(a)
  n2 <- length(b)
  student <- t.test(a, b, var.equal = TRUE)
  welch <- t.test(a, b, var.equal = FALSE)
  df <- n1 + n2 - 2
  pooled_sd <- sqrt(((n1 - 1) * var(a) + (n2 - 1) * var(b)) / df)
  difference <- mean(a) - mean(b)
  d_value <- difference / pooled_sd

  # Brown-Forsythe: one-way ANOVA on absolute distances from group medians.
  y <- c(a, b)
  group <- factor(rep(c("process_feedback", "outcome_feedback"), c(n1, n2)))
  distance <- abs(y - ave(y, group, FUN = median))
  bf <- anova(lm(distance ~ group))

  sw_a <- shapiro.test(a)
  sw_b <- shapiro.test(b)
  c(
    "mean_difference" = difference,
    "pooled_standard_error" = pooled_sd * sqrt(1 / n1 + 1 / n2),
    "student_t" = unname(student$statistic),
    "student_df" = unname(student$parameter),
    "student_two_sided_p" = student$p.value,
    "student_ci_95_lower" = student$conf.int[1],
    "student_ci_95_upper" = student$conf.int[2],
    "welch_t" = unname(welch$statistic),
    "welch_df" = unname(welch$parameter),
    "welch_two_sided_p" = welch$p.value,
    "welch_ci_95_lower" = welch$conf.int[1],
    "welch_ci_95_upper" = welch$conf.int[2],
    "cohens_d" = d_value,
    "hedges_g" = d_value * (1 - 3 / (4 * df - 1)),
    "levene_brown_forsythe/f" = bf[["F value"]][1],
    "levene_brown_forsythe/df1" = bf[["Df"]][1],
    "levene_brown_forsythe/df2" = bf[["Df"]][2],
    "levene_brown_forsythe/p" = bf[["Pr(>F)"]][1],
    "group_shapiro_wilk/process_feedback/w" = unname(sw_a$statistic),
    "group_shapiro_wilk/process_feedback/p" = sw_a$p.value,
    "group_shapiro_wilk/outcome_feedback/w" = unname(sw_b$statistic),
    "group_shapiro_wilk/outcome_feedback/p" = sw_b$p.value
  )
}

labels <- c(
  "mean_difference" = "Mean difference",
  "pooled_standard_error" = "Standard error",
  "welch_t" = "Welch t",
  "welch_df" = "Welch df",
  "welch_two_sided_p" = "Welch p",
  "welch_ci_95_lower" = "Welch 95% CI lower",
  "welch_ci_95_upper" = "Welch 95% CI upper",
  "student_t" = "Student t",
  "student_df" = "Student df",
  "student_two_sided_p" = "Student p",
  "cohens_d" = "Cohen's d",
  "hedges_g" = "Hedges' g",
  "levene_brown_forsythe/f" = "Brown-Forsythe F",
  "levene_brown_forsythe/p" = "Brown-Forsythe p",
  "group_shapiro_wilk/process_feedback/w" = "Shapiro-Wilk W, process",
  "group_shapiro_wilk/process_feedback/p" = "Shapiro-Wilk p, process",
  "group_shapiro_wilk/outcome_feedback/w" = "Shapiro-Wilk W, outcome",
  "group_shapiro_wilk/outcome_feedback/p" = "Shapiro-Wilk p, outcome"
)

matches <- function(target, computed) {
  if (target$statistic == "missing_ids") return(identical(computed, target$value))
  abs(as.numeric(computed) - as.numeric(target$value)) <= as.numeric(target$tolerance)
}

cat(sprintf("Base-R route (%s)\n", R.version.string))
targets <- read.csv(file.path(root, "checks", "targets.csv"),
                    colClasses = "character", check.names = FALSE)
failures <- character(0)
worked <- c()
for (study in unique(targets$study)) {
  d <- read_study(study)
  mine <- targets[targets$study == study, , drop = FALSE]
  case <- if (any(mine$statistic == "worked_case")) worked_case(d) else c()
  good <- 0L
  for (i in seq_len(nrow(mine))) {
    target <- mine[i, , drop = FALSE]
    if (target$statistic == "worked_case") {
      computed <- case[[target$variable]]
      worked[target$variable] <- computed
    } else {
      computed <- descriptive(target, d)
    }
    if (isTRUE(matches(target, computed))) {
      good <- good + 1L
    } else {
      failures <- c(failures, sprintf("MISMATCH %s %s: recomputed %s, record %s",
                                      study, target$record_path,
                                      format(computed, digits = 17), target$value))
    }
  }
  cat(sprintf("%-44s %3d of %3d match\n", study, good, nrow(mine)))
}

cat("Worked case, Study 03 (Chapter 18): motivation_score, process minus outcome feedback\n")
for (key in names(labels)) {
  cat(sprintf("  %-26s %12.6f\n", labels[[key]], worked[[key]]))
}
if (length(failures)) {
  cat(paste0(failures, "\n"), sep = "")
  cat(sprintf("JAMOVI_DATA_R_FAILED mismatches=%d\n", length(failures)))
  quit(status = 1)
}
cat(sprintf("JAMOVI_DATA_R_OK targets=%d worked_case=%d\n", nrow(targets), length(worked)))
