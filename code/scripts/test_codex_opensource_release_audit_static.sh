#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
import importlib.util
import tempfile
from pathlib import Path

path = Path("code/platforms/codex/opensource_release/release_audit.py")
assert path.exists()
text = path.read_text(encoding="utf-8")
for forbidden in ["subprocess", "requests.", "urllib.request", "docker run", "codex exec"]:
    assert forbidden not in text.lower(), forbidden
spec = importlib.util.spec_from_file_location("release_audit", path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    for name in [".env", "x.pem", "x.key", "x.gz", "x.tar.gz", "token.txt", "secret.txt"]:
        (root / name).write_text("fake\n", encoding="utf-8")
    out = root / "out"
    audit = module.run_release_audit(root, out)
    paths = {item["path"] for item in audit["findings"]}
    for name in [".env", "x.pem", "x.key", "x.gz", "x.tar.gz", "token.txt", "secret.txt"]:
        assert name in paths
        assert (root / name).exists()
assert "real_api_called" in text
print("Codex open source release audit static test passed.")
PY

echo "Codex open source release audit static test passed."
