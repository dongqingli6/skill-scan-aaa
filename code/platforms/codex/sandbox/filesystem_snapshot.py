"""Filesystem snapshot utilities for safe_skill-only smoke tests.

This module only walks local filesystem trees passed explicitly by the caller.
It records symlinks without following them and caps file hashing by size.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any, Dict, List

DEFAULT_MAX_HASH_BYTES = 10 * 1024 * 1024


def hash_file(path: str | Path, max_bytes: int = DEFAULT_MAX_HASH_BYTES) -> tuple[str | None, str | None]:
    p = Path(path)
    try:
        st = p.lstat()
        if st.st_size > max_bytes:
            return None, f"file larger than {max_bytes} bytes"
        digest = hashlib.sha256()
        with p.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest(), None
    except Exception as exc:  # pragma: no cover - defensive for odd files
        return None, f"hash error: {exc}"


def safe_stat(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    st = p.lstat()
    mode = st.st_mode
    if stat.S_ISREG(mode):
        kind = "file"
    elif stat.S_ISDIR(mode):
        kind = "dir"
    elif stat.S_ISLNK(mode):
        kind = "symlink"
    else:
        kind = "other"
    return {
        "type": kind,
        "size": st.st_size,
        "mode": oct(stat.S_IMODE(mode)),
        "uid": st.st_uid,
        "gid": st.st_gid,
        "mtime": st.st_mtime,
    }


def _record_path(path: Path, root: Path) -> Dict[str, Any]:
    item = safe_stat(path)
    item["path"] = str(path)
    item["relative_path"] = "." if path == root else str(path.relative_to(root))
    if item["type"] == "symlink":
        try:
            item["symlink_target"] = os.readlink(path)
        except OSError as exc:
            item["symlink_target"] = f"readlink error: {exc}"
    elif item["type"] == "file":
        digest, skipped = hash_file(path)
        item["sha256"] = digest
        if skipped:
            item["skipped_hash_reason"] = skipped
    return item


def snapshot_tree(root_path: str | Path, label: str) -> Dict[str, Any]:
    root = Path(root_path).resolve()
    entries: List[Dict[str, Any]] = []
    if not root.exists():
        return {"label": label, "root": str(root), "exists": False, "entries": []}

    entries.append(_record_path(root, root))
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current = Path(dirpath)
        kept_dirnames = []
        for dirname in sorted(dirnames):
            child = current / dirname
            entries.append(_record_path(child, root))
            if not child.is_symlink():
                kept_dirnames.append(dirname)
        dirnames[:] = kept_dirnames
        for filename in sorted(filenames):
            entries.append(_record_path(current / filename, root))
    entries.sort(key=lambda item: item["relative_path"])
    return {"label": label, "root": str(root), "exists": True, "entries": entries}


def write_snapshot(root_path: str | Path, output_json: str | Path, label: str) -> Dict[str, Any]:
    snapshot = snapshot_tree(root_path, label)
    out = Path(output_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a filesystem snapshot JSON")
    parser.add_argument("--root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    write_snapshot(args.root, args.output, args.label)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
