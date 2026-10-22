#!/usr/bin/env python3
"""Check that every file here is the published copy, and nothing else is here.

1. SHA256SUMS lists every file in the repository (except itself and .git),
   and every hash matches.
2. The Book 2 reader files are byte-for-byte copies of the source named in
   SOURCE.json (nicholaskarlson/data at the recorded commit): each copied
   file's hash matches the hash recorded there, and the source's own
   checksum files (data/, expected-results/, figures/) still verify.
3. Each verified record names the SHA-256 of its CSV and its dictionary;
   both must match the files here.
4. checks/targets.csv is exactly what scripts/build_targets.py builds from
   the records, so every target value is the record's own value.

Needs only Python 3.9 or later. Writes nothing.

    python3 scripts/verify_companion.py

The last line is JAMOVI_DATA_BOUNDARY_OK when every check passes.
"""

import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "scripts"))
import build_targets  # noqa: E402

SKIP_DIRS = {".git"}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tracked_files():
    files = []
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if rel.parts[0] in SKIP_DIRS or not path.is_file():
            continue
        if "__pycache__" in rel.parts:
            continue
        files.append(rel.as_posix())
    return files


def read_sums(path):
    sums = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split(None, 1)
            sums[name.lstrip("*")] = digest
    return sums


def main():
    errors = []

    # 1. Root SHA256SUMS covers every file, and only those files.
    sums = read_sums(ROOT / "SHA256SUMS")
    present = set(tracked_files()) - {"SHA256SUMS"}
    for name in sorted(present - set(sums)):
        errors.append(f"not listed in SHA256SUMS: {name}")
    for name in sorted(set(sums) - present):
        errors.append(f"listed in SHA256SUMS but missing: {name}")
    for name in sorted(present & set(sums)):
        if sha256(ROOT / name) != sums[name]:
            errors.append(f"hash differs from SHA256SUMS: {name}")

    # 2. Copies of the source files, unchanged.
    source = json.loads((ROOT / "SOURCE.json").read_text(encoding="utf-8"))
    copied = source["files"]
    for name, digest in sorted(copied.items()):
        path = ROOT / name
        if not path.is_file():
            errors.append(f"copied file missing: {name}")
        elif sha256(path) != digest:
            errors.append(f"copied file differs from the source: {name}")
    inner = 0
    for sums_file in ("data/SHA256SUMS", "expected-results/SHA256SUMS", "figures/SHA256SUMS"):
        for name, digest in read_sums(ROOT / sums_file).items():
            inner += 1
            path = ROOT / name
            if not path.is_file() or sha256(path) != digest:
                errors.append(f"{sums_file} does not verify: {name}")

    # 3. Each record points at its own CSV and dictionary.
    records = sorted((ROOT / "expected-results").glob("*_verified_results.json"))
    for path in records:
        record = json.loads(path.read_text(encoding="utf-8"))
        study = record["dataset_id"]
        csv_path = ROOT / "data" / f"{study}.csv"
        dictionary = ROOT / "data" / "dictionaries" / f"{study}_dictionary.json"
        if sha256(csv_path) != record["dataset_sha256"]:
            errors.append(f"{path.name}: dataset_sha256 does not match {csv_path.name}")
        if sha256(dictionary) != record["dictionary_sha256"]:
            errors.append(f"{path.name}: dictionary_sha256 does not match {dictionary.name}")
    if len(records) != 12:
        errors.append(f"expected 12 verified records, found {len(records)}")

    # 4. The targets are the records' own values.
    targets = build_targets.render(build_targets.build_rows(ROOT))
    if (ROOT / "checks" / "targets.csv").read_bytes() != targets:
        errors.append("checks/targets.csv differs from what scripts/build_targets.py builds")

    for error in errors:
        print(f"ERROR {error}")
    if errors:
        print(f"JAMOVI_DATA_BOUNDARY_FAILED errors={len(errors)}")
        return 1
    print(f"Source: {source['source_repository']} at {source['source_commit'][:7]}")
    print(f"Files listed in SHA256SUMS: {len(sums)}, all match")
    print(f"Copied from the source unchanged: {len(copied)}")
    print(f"Source checksum lines verified: {inner}")
    print(f"Records tied to their CSV and dictionary: {len(records)}")
    target_rows = targets.count(b"\n") - 1
    print(f"Targets taken from the records: {target_rows}")
    print("JAMOVI_DATA_BOUNDARY_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
