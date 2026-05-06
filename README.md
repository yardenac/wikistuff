# wikistuff

A tiny read-only command-line tool for poking at Wikidata and English Wikipedia.

This is a "hello world"-style example — it exists to show what a small,
self-contained Wikidata/Wikipedia client looks like, not to be a full-featured
library. If you're looking for inspiration to build your own scripts against
the MediaWiki APIs, this is a reasonable starting point.

It was created at the **WikiMediaWiki Workshop in May 2026**, presented by
[BAWUG](https://meta.wikimedia.org/wiki/Bay_Area_Wikipedians_User_Group) (the Bay Area Wikipedians User Group).

## Running it

The script uses only the Python standard library, so there's nothing to install:

```sh
python3 wikistuff.py --help
```

## Examples

Get the English label for a Wikidata item:

```sh
python3 wikistuff.py get-wikidata-label Q42
# Douglas Adams
```

Same thing, in another language:

```sh
python3 wikistuff.py get-wikidata-label Q42 -l de
```

JSON output:

```sh
python3 wikistuff.py get-wikidata-label Q4675 --json
```

List the English Wikipedia categories for the article behind a QID:

```sh
python3 wikistuff.py list-enwiki-categories Q4675 --limit 5
```

Include hidden maintenance categories:

```sh
python3 wikistuff.py list-enwiki-categories Q4675 --hidden
```

Run a tiny example SPARQL query against the Wikidata Query Service:

```sh
python3 wikistuff.py list-example-humans
```

## Subcommands

- `get-wikidata-label QID` — print the Wikidata label for a QID
- `list-enwiki-categories QID` — list categories on the linked English Wikipedia article
- `list-example-humans` — run a sample SPARQL query (10 instances of `wd:Q5`)
- `help [SUBCOMMAND]` — show help

That's the whole tool. Read the source — it's one file.
