"""Browser edge CLI — generic command surface from the shared uri_control.edge.cli
builder. The browser pack (uribrowserdocker) is composed onto the runtime here."""

from __future__ import annotations

import argparse

from uri_control.edge.cli import build_edge_cli

from .runtime import Runtime, load_json


def _add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--packs", default="browser")
    parser.add_argument("--config", default="config/browser-profile.json")
    parser.add_argument("--events", default="data/events.jsonl")


def _runtime(args: argparse.Namespace):
    config = load_json(getattr(args, "config", None))
    rt = Runtime(events_path=getattr(args, "events", "data/events.jsonl"), config=config)
    if "browser" in getattr(args, "packs", "browser").split(","):
        import uribrowserdocker

        uribrowserdocker.register(rt)
    return rt


main = build_edge_cli(
    "urisys-browser",
    _runtime,
    service="uribrowser",
    default_port=8792,
    allow_real=True,
    add_arguments=_add_arguments,
)


if __name__ == "__main__":
    raise SystemExit(main())
