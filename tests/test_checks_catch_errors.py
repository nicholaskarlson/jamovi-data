#!/usr/bin/env python3
"""Show that the checks fail when they should.

Copies the repository to a temporary folder (the original is not touched),
then makes three small changes, one at a time, and confirms each is caught:

1. one motivation score in the Study 03 CSV moves by 0.1;
2. one value in checks/targets.csv is altered;
3. one byte is added to a figure.

With --with-r, the base-R route is also run on the altered Study 03 CSV.

    python3 tests/test_checks_catch_errors.py [--with-r]

The last line is TESTS_OK when every change was caught.
"""

import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
STUDY03 = "data/study_03_feedback_two_groups.csv"


def run(args, cwd):
    done = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    return done.returncode, done.stdout + done.stderr


def fresh_copy(base):
    target = pathlib.Path(base) / "copy"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    return target


def main():
    with_r = "--with-r" in sys.argv[1:]
    python = sys.executable
    failures = []

    def expect(label, args, cwd, status_ok, token):
        code, out = run(args, cwd)
        caught = (code == 0) == status_ok and token in out
        print(f"{'ok  ' if caught else 'FAIL'} {label}")
        if not caught:
            failures.append(label)
            print(out)

    with tempfile.TemporaryDirectory() as base:
        # The unaltered copy passes everything.
        copy = fresh_copy(base)
        expect("unaltered copy: files verify", [python, "scripts/verify_companion.py"],
               copy, True, "JAMOVI_DATA_BOUNDARY_OK")
        expect("unaltered copy: Python route passes", [python, "scripts/recompute.py"],
               copy, True, "JAMOVI_DATA_PYTHON_OK")

        # 1. Move one motivation score by 0.1.
        copy = fresh_copy(base)
        path = copy / STUDY03
        text = path.read_bytes().decode("utf-8")
        lines = text.split("\n")
        fields = lines[1].split(",")
        fields[2] = f"{float(fields[2]) + 0.1:.1f}"
        lines[1] = ",".join(fields)
        path.write_bytes("\n".join(lines).encode("utf-8"))
        expect("changed score: files fail to verify", [python, "scripts/verify_companion.py"],
               copy, False, "copied file differs from the source: " + STUDY03)
        expect("changed score: Python route reports mismatches", [python, "scripts/recompute.py"],
               copy, False, "independent_samples_t_test/welch_t")
        if with_r:
            expect("changed score: R route reports mismatches", ["Rscript", "scripts/recompute.R"],
                   copy, False, "independent_samples_t_test/welch_t")

        # 2. Alter one target value.
        copy = fresh_copy(base)
        path = copy / "checks" / "targets.csv"
        text = path.read_bytes().decode("utf-8")
        assert ",5.389583333333,1e-09\n" in text
        path.write_bytes(text.replace(",5.389583333333,1e-09\n", ",5.389583333334,1e-09\n")
                         .encode("utf-8"))
        expect("changed target: files fail to verify", [python, "scripts/verify_companion.py"],
               copy, False, "checks/targets.csv differs")

        # 3. Add one byte to a figure.
        copy = fresh_copy(base)
        path = copy / "figures" / "generated" / "fig12_belonging_exam.png"
        path.write_bytes(path.read_bytes() + b"\0")
        expect("changed figure: files fail to verify", [python, "scripts/verify_companion.py"],
               copy, False, "figures/SHA256SUMS does not verify")

    if failures:
        print(f"TESTS_FAILED count={len(failures)}")
        return 1
    print("TESTS_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
