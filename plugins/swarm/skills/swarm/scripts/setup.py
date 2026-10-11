"""Creates (or updates) the swarm's Python environment and installs swarm_kit into it.

Run with any Python 3.10+:  python setup.py [--force] [--quiet]
Prints the environment's Python path on its last line. Idempotent: does nothing when the
installed swarm_kit already matches this plugin's version.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import venv
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent / "kit"


def home() -> Path:
    return Path(os.environ.get("SWARM_HOME") or Path.home() / ".claude" / "swarm")


def venv_python(root: Path) -> Path:
    return root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def wanted_version() -> str:
    text = (KIT / "pyproject.toml").read_text(encoding="utf-8")
    return re.search(r'^version\s*=\s*"([^"]+)"', text, re.M).group(1)


def installed_version(py: Path) -> str | None:
    if not py.exists():
        return None
    proc = subprocess.run([str(py), "-c", "import swarm_kit; print(swarm_kit.__version__)"], capture_output=True, text=True)
    return proc.stdout.strip() if proc.returncode == 0 else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="reinstall even when versions match")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    root = home()
    py = venv_python(root)
    say = (lambda *a: None) if args.quiet else print
    if not py.exists():
        say(f"Creating the swarm environment at {root / '.venv'} ...")
        root.mkdir(parents=True, exist_ok=True)
        venv.EnvBuilder(with_pip=True, upgrade_deps=False).create(root / ".venv")

    want, have = wanted_version(), installed_version(py)
    if args.force or have != want:
        say(f"Installing swarm_kit {want} (was {have or 'not installed'}) ...")
        proc = subprocess.run([str(py), "-m", "pip", "install", "--disable-pip-version-check", "-q", "--upgrade", str(KIT)],
                              capture_output=True, text=True)
        if proc.returncode != 0:
            print(proc.stderr[-3000:], file=sys.stderr)
            return 1
    else:
        say(f"swarm_kit {have} is up to date.")
    print(py)
    return 0


if __name__ == "__main__":
    sys.exit(main())
