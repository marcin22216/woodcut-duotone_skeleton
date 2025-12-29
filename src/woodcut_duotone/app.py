"""Application entry point."""

from __future__ import annotations

import argparse
import logging
import os
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Woodcut Duotone application")
    parser.add_argument("--gui", action="store_true", help="Launch the GUI")
    args = parser.parse_args(argv)

    if args.gui:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
        import woodcut_duotone

        logging.getLogger(__name__).info(
            "GUI started (pid=%s exe=%s pkg_path=%s)",
            os.getpid(),
            sys.executable,
            woodcut_duotone.__file__,
        )
        from woodcut_duotone.gui.main_window import run_gui

        return run_gui()

    print("Woodcut Duotone App – bootstrap OK")
    if argv is None and len(sys.argv) == 1:
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
