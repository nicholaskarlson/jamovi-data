#!/usr/bin/env python3
"""Maintainer tool: rewrite SHA256SUMS to list every file in the repository.

Run after adding or changing a file, then run scripts/verify_companion.py.
Readers never need this.

    python3 scripts/write_sums.py
"""

import hashlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main():
    lines = []
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if rel.parts[0] == ".git" or "__pycache__" in rel.parts or not path.is_file():
            continue
        if rel.as_posix() == "SHA256SUMS":
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {rel.as_posix()}\n")
    (ROOT / "SHA256SUMS").write_bytes("".join(lines).encode("utf-8"))
    print(f"wrote SHA256SUMS files={len(lines)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
