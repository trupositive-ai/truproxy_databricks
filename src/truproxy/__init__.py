import json
import os
import stat
import subprocess

import polars as pl

_SCHEMA = {
    "id": pl.Utf8,
    "name": pl.Utf8,
    "proxy_type": pl.Utf8,
    "total_cost": pl.Float64,
    "state": pl.Utf8,
}

# Three levels up from src/truproxy/__init__.py → project root
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _find_binary() -> str:
    candidates = [
        # 1. Bundled pre-compiled Linux binary — committed to repo for Databricks App
        os.path.join(_ROOT, "bin", "truproxy-core"),
        # 2. Local Windows dev build
        os.path.join(_ROOT, "truproxy-core", "target", "release", "truproxy-core.exe"),
        # 3. Local Linux/macOS dev build
        os.path.join(_ROOT, "truproxy-core", "target", "release", "truproxy-core"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            if os.name != "nt":
                current = os.stat(path).st_mode
                os.chmod(path, current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            return path
    raise FileNotFoundError(
        "truproxy-core binary not found.\n"
        "  Databricks App: run .\\build-linux.ps1 (needs WSL + Rust), then commit bin/truproxy-core\n"
        "  Local Windows:  cd truproxy-core && cargo build --release\n"
        "  Local Linux:    cd truproxy-core && cargo build --release && cp target/release/truproxy-core ../bin/truproxy-core"
    )


class TruProxy:
    def __init__(self, token: str, workspace_url: str):
        self._token = token
        self._workspace_url = workspace_url
        self._binary = _find_binary()

    def _run(self, tier: str, region: str, mode: str = "all") -> pl.DataFrame:
        result = subprocess.run(
            [
                self._binary,
                "--token", self._token,
                "--workspace-url", self._workspace_url,
                "--tier", tier,
                "--region", region,
                "--mode", mode,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "truproxy-core exited with a non-zero status")
        records = json.loads(result.stdout)
        if not records:
            return pl.DataFrame(schema=_SCHEMA)
        return pl.DataFrame(records, schema=_SCHEMA)

    def get(self, tier: str = "PREMIUM", region: str = "EU_WEST") -> pl.DataFrame:
        return self._run(tier, region, mode="all")

    def get_active_clusters(self, tier: str = "PREMIUM", region: str = "EU_WEST") -> pl.DataFrame:
        return self._run(tier, region, mode="clusters")
