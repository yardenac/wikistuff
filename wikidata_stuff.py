#!/usr/bin/env python3
"""Small read-only CLI for Wikidata and English Wikipedia lookups."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request


WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"
QID_RE = re.compile(r"^Q[1-9]\d*$")


def fetch_label(qid: str, language: str) -> str:
    query = urllib.parse.urlencode(
        {
            "action": "wbgetentities",
            "ids": qid,
            "props": "labels",
            "languages": language,
            "languagefallback": "1",
            "format": "json",
        }
    )
    request = urllib.request.Request(
        f"{WIKIDATA_API_URL}?{query}",
        headers={"User-Agent": "wikidata-stuff/0.1"},
    )

    with urllib.request.urlopen(request, timeout=15) as response:
        payload = json.load(response)

    entity = payload.get("entities", {}).get(qid)
    if not entity or entity.get("missing"):
        raise LookupError(f"{qid} was not found on Wikidata")

    label = entity.get("labels", {}).get(language, {}).get("value")
    if not label:
        raise LookupError(f"{qid} has no {language!r} label")

    return label


def normalize_qid(qid: str) -> str:
    normalized = qid.upper()
    if not QID_RE.fullmatch(normalized):
        raise ValueError(f"invalid QID {qid!r}; expected something like Q42")
    return normalized


def run_get_wikidata_label(args: argparse.Namespace) -> int:
    qid = normalize_qid(args.qid)
    label = fetch_label(qid, args.language)

    if args.output_json:
        print(
            json.dumps(
                {
                    "qid": qid,
                    "language": args.language,
                    "label": label,
                },
                indent=2,
            )
        )
    else:
        print(label)

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only Wikidata and English Wikipedia lookup helpers."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="emit machine-readable JSON",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    label_parser = subparsers.add_parser(
        "get-wikidata-label",
        help="print the Wikidata label for a QID",
    )
    label_parser.add_argument("qid", help="Wikidata entity ID, for example Q42")
    label_parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="emit machine-readable JSON",
    )
    label_parser.add_argument(
        "-l",
        "--language",
        default="en",
        help="label language code to request (default: en)",
    )
    label_parser.set_defaults(func=run_get_wikidata_label)

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        return args.func(args)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except (LookupError, urllib.error.URLError, TimeoutError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
