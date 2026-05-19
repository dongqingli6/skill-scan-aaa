#!/usr/bin/env bash
set -euo pipefail

# Synthetic archive safety tests only.
# No Docker, Codex, strace, samples, network, real HOME, or real token reads.

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

python3 - "$tmp_dir" <<'PY'
from __future__ import annotations

import io
import sys
import tarfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path("web_ui").resolve()))
from safe_extract import SafeExtractError, safe_extract_archive

tmp = Path(sys.argv[1])

benign_zip = tmp / "benign.zip"
with zipfile.ZipFile(benign_zip, "w") as archive:
    archive.writestr("safe_skill/SKILL.md", "# Safe Skill\n")
    archive.writestr("safe_skill/README.md", "local synthetic package\n")

result = safe_extract_archive(benign_zip, tmp / "benign_out")
assert result.file_count == 2
assert (tmp / "benign_out" / "safe_skill" / "SKILL.md").exists()

traversal_zip = tmp / "traversal.zip"
with zipfile.ZipFile(traversal_zip, "w") as archive:
    archive.writestr("../evil.txt", "blocked\n")
try:
    safe_extract_archive(traversal_zip, tmp / "traversal_out")
except SafeExtractError:
    pass
else:
    raise AssertionError("zip traversal archive was not rejected")

absolute_tar = tmp / "absolute.tar.gz"
with tarfile.open(absolute_tar, "w:gz") as archive:
    data = b"blocked\n"
    info = tarfile.TarInfo("/tmp/evil.txt")
    info.size = len(data)
    archive.addfile(info, io.BytesIO(data))
try:
    safe_extract_archive(absolute_tar, tmp / "absolute_out")
except SafeExtractError:
    pass
else:
    raise AssertionError("absolute tar path was not rejected")

symlink_tar = tmp / "symlink.tar.gz"
with tarfile.open(symlink_tar, "w:gz") as archive:
    info = tarfile.TarInfo("safe/link")
    info.type = tarfile.SYMTYPE
    info.linkname = "../../outside"
    archive.addfile(info)
try:
    safe_extract_archive(symlink_tar, tmp / "symlink_out")
except SafeExtractError:
    pass
else:
    raise AssertionError("symlink escape tar was not rejected")

print("Codex Web UI safe extract synthetic tests passed.")
PY
