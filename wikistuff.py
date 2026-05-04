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
ENWIKI_API_URL = "https://en.wikipedia.org/w/api.php"
WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
USER_AGENT = "wikidata-stuff/0.1"
QID_RE = re.compile(r"^Q[1-9]\d*$")


def api_get(api_url: str, params: dict[str, str]) -> dict:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{api_url}?{query}",
        headers={"User-Agent": USER_AGENT},
    )

    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)


def fetch_label(qid: str, language: str) -> str:
    payload = api_get(
        WIKIDATA_API_URL,
        {
            "action": "wbgetentities",
            "ids": qid,
            "props": "labels",
            "languages": language,
            "languagefallback": "1",
            "format": "json",
        },
    )

    entity = payload.get("entities", {}).get(qid)
    if not entity or entity.get("missing"):
        raise LookupError(f"{qid} was not found on Wikidata")

    label = entity.get("labels", {}).get(language, {}).get("value")
    if not label:
        raise LookupError(f"{qid} has no {language!r} label")

    return label


def fetch_enwiki_title(qid: str) -> str:
    payload = api_get(
        WIKIDATA_API_URL,
        {
            "action": "wbgetentities",
            "ids": qid,
            "props": "sitelinks",
            "sitefilter": "enwiki",
            "format": "json",
        },
    )

    entity = payload.get("entities", {}).get(qid)
    if not entity or entity.get("missing"):
        raise LookupError(f"{qid} was not found on Wikidata")

    title = entity.get("sitelinks", {}).get("enwiki", {}).get("title")
    if not title:
        raise LookupError(f"{qid} has no English Wikipedia article")

    return title


def fetch_enwiki_page(qid: str) -> dict:
    title = fetch_enwiki_title(qid)
    payload = api_get(
        ENWIKI_API_URL,
        {
            "action": "query",
            "titles": title,
            "redirects": "1",
            "format": "json",
        },
    )

    pages = payload.get("query", {}).get("pages", {})
    for page in pages.values():
        if "missing" in page:
            break
        return {
            "pageid": page["pageid"],
            "title": page["title"],
        }

    raise LookupError(f"{title!r} was not found on English Wikipedia")


def fetch_enwiki_categories(pageid: int, include_hidden: bool, limit: int | None) -> list[dict]:
    categories = []
    params = {
        "action": "query",
        "pageids": str(pageid),
        "prop": "categories",
        "clprop": "hidden",
        "cllimit": "max",
        "format": "json",
    }
    if not include_hidden:
        params["clshow"] = "!hidden"

    while True:
        payload = api_get(ENWIKI_API_URL, params)
        pages = payload.get("query", {}).get("pages", {})
        page = pages.get(str(pageid), {})

        for category in page.get("categories", []):
            categories.append(
                {
                    "title": category["title"],
                    "hidden": "hidden" in category,
                }
            )
            if limit is not None and len(categories) >= limit:
                return categories

        continuation = payload.get("continue")
        if not continuation:
            return categories
        params.update(continuation)


def normalize_qid(qid: str) -> str:
    normalized = qid.upper()
    if not QID_RE.fullmatch(normalized):
        raise ValueError(f"invalid QID {qid!r}; expected something like Q42")
    return normalized


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


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


def run_list_enwiki_categories(args: argparse.Namespace) -> int:
    qid = normalize_qid(args.qid)
    page = fetch_enwiki_page(qid)
    categories = fetch_enwiki_categories(page["pageid"], args.hidden, args.limit)

    if args.output_json:
        print(
            json.dumps(
                {
                    "qid": qid,
                    "pageid": page["pageid"],
                    "title": page["title"],
                    "categories": categories,
                },
                indent=2,
            )
        )
    else:
        for category in categories:
            print(category["title"])

    return 0

def run_list_example_humans(args: argparse.Namespace) -> int:
    query = """
SELECT ?item ?itemLabel WHERE {
  ?item wdt:P31 wd:Q5.
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT 10
"""

    payload = api_get(
        WIKIDATA_SPARQL_URL,
        {
            "query": query,
            "format": "json",
        },
    )

    rows = payload.get("results", {}).get("bindings", [])

    if args.output_json:
        print(json.dumps(rows, indent=2))
    else:
        for row in rows:
            label = row.get("itemLabel", {}).get("value", "")
            item = row.get("item", {}).get("value", "")
            print(f"{label}\t{item}")

    return 0

def run_help(args: argparse.Namespace) -> int:
    if args.topic:
        args.command_parsers[args.topic].print_help()
    else:
        args.parser.print_help()
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
    command_parsers = {}

    label_parser = subparsers.add_parser(
        "get-wikidata-label",
        help="print the Wikidata label for a QID",
    )
    command_parsers["get-wikidata-label"] = label_parser
    label_parser.add_argument("qid", help="Wikidata entity ID, for example Q42")
    label_parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        default=argparse.SUPPRESS,
        help="emit machine-readable JSON",
    )
    label_parser.add_argument(
        "-l",
        "--language",
        default="en",
        help="label language code to request (default: en)",
    )
    label_parser.set_defaults(func=run_get_wikidata_label)

    categories_parser = subparsers.add_parser(
        "list-enwiki-categories",
        help="list categories for the English Wikipedia article associated with a QID",
    )
    command_parsers["list-enwiki-categories"] = categories_parser
    categories_parser.add_argument("qid", help="Wikidata entity ID, for example Q4675")
    categories_parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        default=argparse.SUPPRESS,
        help="emit machine-readable JSON",
    )
    categories_parser.add_argument(
        "--hidden",
        action="store_true",
        help="include hidden maintenance categories",
    )
    categories_parser.add_argument(
        "--limit",
        type=positive_int,
        help="maximum number of categories to print",
    )
    categories_parser.set_defaults(func=run_list_enwiki_categories)

    humans_parser = subparsers.add_parser(
        "list-example-humans",
        help="list ten example human Wikidata items using SPARQL",
    )
    command_parsers["list-example-humans"] = humans_parser

    humans_parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        default=argparse.SUPPRESS,
        help="emit machine-readable JSON",
    )

    humans_parser.set_defaults(func=run_list_example_humans)

    help_parser = subparsers.add_parser(
        "help",
        help="show help for the tool or a subcommand",
    )
    help_topics = sorted([*command_parsers, "help"])
    help_parser.add_argument(
        "topic",
        nargs="?",
        choices=help_topics,
        help="subcommand to describe",
    )
    command_parsers["help"] = help_parser
    help_parser.set_defaults(
        func=run_help,
        parser=parser,
        command_parsers=command_parsers,
    )

    if len(sys.argv) == 1:
        parser.print_help()
        raise SystemExit(0)

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
