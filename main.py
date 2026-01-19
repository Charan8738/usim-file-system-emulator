# main.py
from __future__ import annotations

from pathlib import Path

from filesystem.loader import load_profile
from card.context import CardContext
from transport.tcp_server import run_server


def main() -> None:
    """
    Entry point for the USIM file system emulator.

    Workflow:
    1) Load the file system tree (MF/DF/EF) from data/profile.json
    2) Create CardContext (start with MF selected)
    3) Start TCP server to accept APDU commands (hex per line)
    """
    project_root = Path(__file__).resolve().parent
    data_dir = project_root / "data"
    profile_path = data_dir / "profile.json"

    mf = load_profile(profile_path, data_dir=data_dir)
    ctx = CardContext.from_mf(mf)

    run_server(ctx, host="127.0.0.1", port=9999)


if __name__ == "__main__":
    main()
