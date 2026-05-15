from __future__ import annotations

import argparse
import sys

from .app_factory import build_pipeline
from .config import Settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the AlphaMedia news pipeline locally.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    search = subparsers.add_parser("search", help="Search and summarize a topic")
    search.add_argument("topic")
    search.add_argument("--fresh-only", action="store_true")

    article = subparsers.add_parser("article", help="Search and generate an article draft")
    article.add_argument("topic")

    args = parser.parse_args(argv)
    settings = Settings.from_env()
    pipeline = build_pipeline(settings)

    if args.command == "search":
        run = pipeline.run(args.topic, fresh_only=args.fresh_only)
        print(run.insight.summary)
        for insight in run.insight.insights:
            print(f"- {insight}")
        return 0

    if args.command == "article":
        run = pipeline.run(args.topic)
        draft = pipeline.generate_article(run)
        print(draft.title)
        print()
        print(draft.body)
        print()
        print("X thread:")
        for index, post in enumerate(draft.x_thread, start=1):
            print(f"{index}. {post}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
