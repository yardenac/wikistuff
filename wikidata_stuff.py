#!/usr/bin/env python3
"""Print the Wikidata label for a QID."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request


API_URL = "https://www.wikidata.org/w/api.php"
QID_RE = re.compile(r"^Q[1-9]\d*$")


def fetch_label(qid: str, language: str) -> str:
    query = urllib.parse.urlencode(
        {
            "action": "wbgetentities",
            "ids": qid,
            "props": "labels",
            "languages": language,
            "format": "json",
            "origin": "*",
        }
    )
    request = urllib.request.Request(
        f"{API_URL}?{query}",
        headers={"User-Agent": "qid-label-cli/1.0"},
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print the Wikidata label for a QID.")
    parser.add_argument("qid", help="Wikidata entity ID, for example Q42")
    parser.add_argument(
        "-l",
        "--language",
        default="en",
        help="label language code to request (default: en)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    qid = args.qid.upper()

    if not QID_RE.fullmatch(qid):
        print(f"error: invalid QID {args.qid!r}; expected something like Q42", file=sys.stderr)
        return 2

    try:
        print(fetch_label(qid, args.language))
    except (LookupError, urllib.error.URLError, TimeoutError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
