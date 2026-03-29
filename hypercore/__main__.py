"""Module entrypoint for HyperCore."""

import argparse
import asyncio
import sys
import traceback

from hypercore.core.config import CORE_DEBUG
from hypercore.core.kernel import HyperCoreKernel


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m hypercore")
    parser.add_argument(
        "--runtime",
        choices=("both", "bot", "userbot"),
        default="both",
        help="Select which Telegram runtime to start.",
    )
    return parser


async def _run(runtime_mode: str) -> int:
    kernel = HyperCoreKernel(runtime_mode=runtime_mode)
    return await kernel.run()


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        return asyncio.run(_run(args.runtime))
    except KeyboardInterrupt:
        print("HyperCore stopped by keyboard interrupt.", file=sys.stderr)
        return 130
    except Exception as exc:
        if CORE_DEBUG:
            traceback.print_exc()
        else:
            print(f"HyperCore failed to start: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
