#!/usr/bin/env bash
set -euo pipefail

python3 -m py_compile \
  code/platforms/codex/sandbox/filesystem_snapshot.py \
  code/platforms/codex/sandbox/filesystem_diff.py

base="/tmp/codex_fs_diff_unit"
rm -rf "$base"
mkdir -p "$base/tree"
echo "old" > "$base/tree/modified.txt"
echo "delete" > "$base/tree/deleted.txt"

python3 code/platforms/codex/sandbox/filesystem_snapshot.py \
  --root "$base/tree" \
  --output "$base/before_snapshot.json" \
  --label before

echo "new" > "$base/tree/modified.txt"
echo "created" > "$base/tree/created.txt"
rm "$base/tree/deleted.txt"

python3 code/platforms/codex/sandbox/filesystem_snapshot.py \
  --root "$base/tree" \
  --output "$base/after_snapshot.json" \
  --label after

python3 code/platforms/codex/sandbox/filesystem_diff.py \
  --before "$base/before_snapshot.json" \
  --after "$base/after_snapshot.json" \
  --output "$base/filesystem_diff.json"

python3 - <<'PY'
import json
from pathlib import Path
path = Path('/tmp/codex_fs_diff_unit/filesystem_diff.json')
data = json.loads(path.read_text(encoding='utf-8'))
assert 'created.txt' in data['created_files'], data
assert 'deleted.txt' in data['deleted_files'], data
assert 'modified.txt' in data['modified_files'], data
assert data['summary']['total_created'] >= 1, data
assert data['summary']['total_deleted'] >= 1, data
assert data['summary']['total_modified'] >= 1, data
print('Filesystem snapshot/diff unit test passed.')
PY
