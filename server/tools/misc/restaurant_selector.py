"""Restaurant Selector — filter and pick a restaurant from the Restaurants MongoDB.

Reads the collection specified below (defaults to the "Restaurants-DB" database,
"Restaurants-Collection" collection). Connection string comes from the MONGO_URI
environment variable so no credentials live in the code — set it on the container
(docker-compose `environment:` / the /opt/tools/.env file).
"""

import os
import random

from toolkit import Result, Tool, ToolError, fields

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://192.168.0.18:27017")
DB_NAME = os.environ.get("MONGO_DB", "Restaurants-DB")
COLLECTION_NAME = os.environ.get("MONGO_COLLECTION", "Restaurants-Collection")

# sort_by value -> MongoDB sort spec (None means "no server sort; pick at random")
SORTS = {
    "rating": [("rating", -1)],
    "price": [("price-rating", 1)],
    "name": [("name", 1)],
    "random": None,
}


# region: code
def build_query(name="", rtype="", cuisine="", city="", min_rating=0, max_price=0):
    """Turn the filter inputs into a MongoDB query document.

    Text fields match as case-insensitive substrings; blank text and non-positive
    numbers are treated as "don't filter on this field".
    """
    query = {}

    def like(value):                       # case-insensitive "contains"
        return {"$regex": value.strip(), "$options": "i"}

    if name.strip():
        query["name"] = like(name)
    if rtype.strip():
        query["type"] = like(rtype)
    if cuisine.strip():
        query["cuisine"] = like(cuisine)
    if city.strip():
        query["location"] = like(city)         # "location" holds the city
    if min_rating > 0:
        query["rating"] = {"$gte": min_rating}
    if max_price > 0:
        query["price-rating"] = {"$lte": max_price}

    return query


def fetch_restaurants(query, sort=None, limit=25):
    """Run the query against MongoDB and return the matching documents as a list.

    The client is short-lived and closed before returning. A 3s server-selection
    timeout keeps an unreachable database from hanging the tool.
    """
    from pymongo import MongoClient

    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    try:
        collection = client[DB_NAME][COLLECTION_NAME]
        cursor = collection.find(query)
        if sort:
            cursor = cursor.sort(sort)
        return list(cursor.limit(limit))
    finally:
        client.close()
# endregion: code


def _price_bar(value):
    """3 -> '$$$'. Anything non-numeric renders as a dash."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return "—"
    return "$" * n if n > 0 else "—"


def _cell(doc, key, default="—"):
    value = doc.get(key, default)
    return default if value in (None, "") else value


def run(p):
    query = build_query(
        p["name"], p["type"], p["cuisine"], p["city"], p["min_rating"], p["max_price"]
    )
    sort = SORTS.get(p["sort_by"])

    try:
        docs = fetch_restaurants(query, sort, p["limit"])
    except ImportError:
        raise ToolError(
            "The pymongo driver isn't installed.",
            "Add 'pymongo' to server/requirements.txt and rebuild the image "
            "(or `pip install pymongo` in the venv for local runs).",
        ) from None
    except Exception as exc:
        raise ToolError(
            f"Couldn't reach MongoDB at {MONGO_URI}.",
            f"{type(exc).__name__}: {exc}\n\n"
            "Check that MONGO_URI points at the database and that this container "
            "can reach it on the network.",
        ) from None

    out = Result()

    if not docs:
        out.notice("No restaurants match those filters.", "warn")
        out.json(query or {"note": "no filters set — this would return everything"},
                 title="MongoDB query")
        return out

    total = len(docs)

    # --- the "selector": surface one pick up top -----------------------
    if p["pick_one"]:
        pick = random.choice(docs) if sort is None else docs[0]
        how = "random pick" if sort is None else f"top by {p['sort_by']}"
        out.metric("Selected", _cell(pick, "name"), emphasis=True,
                   hint=_cell(pick, "cuisine"))
        out.metric("Type", _cell(pick, "type"))
        out.metric("Rating", _cell(pick, "rating"), hint="of 5")
        out.metric("Price", _price_bar(_cell(pick, "price-rating")))
        out.metric("City", _cell(pick, "location"))
        out.metric("Matches", total, hint=how)
        out.notice(
            f"🍴 Tonight: {_cell(pick, 'name')} — {_cell(pick, 'type')}, "
            f"{_cell(pick, 'cuisine')} in {_cell(pick, 'location')} "
            f"({how} of {total} match{'es' if total != 1 else ''}).",
            "ok")

    # --- the full match list -------------------------------------------
    rows = [
        [
            _cell(d, "name"),
            _cell(d, "type"),
            _cell(d, "cuisine"),
            _cell(d, "location"),
            _cell(d, "rating"),
            _price_bar(_cell(d, "price-rating")),
        ]
        for d in docs
    ]
    out.table(
        [
            {"label": "NAME", "align": "left"},
            {"label": "TYPE", "align": "left"},
            {"label": "CUISINE", "align": "left"},
            {"label": "CITY", "align": "left"},
            {"label": "RATING"},
            {"label": "PRICE"},
        ],
        rows,
        title=f"{total} match{'es' if total != 1 else ''}"
              + (f" (capped at {p['limit']})" if total == p["limit"] else ""),
    )

    out.json(query or {"note": "no filters — all restaurants"}, title="MongoDB query")
    return out


TOOL = Tool(
    id="restaurant-selector",
    name="Restaurant Selector",
    summary="Filter the Restaurants MongoDB by name, type, rating, price, cuisine "
            "and city — and let it pick one for you.",
    description=(
        "Queries the MongoDB collection set by MONGO_URI / MONGO_DB / MONGO_COLLECTION "
        "(defaults: Restaurants-DB / Restaurants-Collection). Text filters match "
        "case-insensitive substrings; leave a field blank or a number at 0 to ignore "
        "it. With “Pick one for me” on, it highlights a single choice — the best by "
        "your sort, or a random one when sort is set to Random."
    ),
    category="misc",
    tag="py",
    autorun=False,     # don't hit the database until the user runs it
    inputs=[
        fields.text("name", "Name", "", required=False, group="Filters",
                    placeholder="contains…", help="Substring of the restaurant name."),
        fields.text("type", "Type", "", required=False, group="Filters",
                    placeholder="fast-food, sit-down…",
                    help="Service type. Matches a substring, e.g. “sit” finds sit-down."),
        fields.text("cuisine", "Cuisine", "", required=False, group="Filters",
                    placeholder="italian, thai…"),
        fields.text("city", "City", "", required=False, group="Filters",
                    placeholder="city name", help="Matches the location field."),
        fields.number("min_rating", "Min rating", 0, min=0, max=5, step=0.1,
                      required=False, group="Filters",
                      help="Only restaurants rated at least this (0 = any)."),
        fields.number("max_price", "Max price", 0, min=0, max=5, step=1,
                      required=False, group="Filters",
                      help="Highest price-rating to allow, 1–4 style (0 = any)."),
        fields.select("sort_by", "Sort by",
                      [("rating", "Rating (high → low)"), ("price", "Price (low → high)"),
                       ("name", "Name (A → Z)"), ("random", "Random")],
                      "rating", group="Options"),
        fields.integer("limit", "Max results", 25, min=1, max=200, group="Options"),
        fields.boolean("pick_one", "Pick one for me", True, group="Options",
                       help="Highlight a single restaurant above the full list."),
    ],
    notes=[
        "Connection string is read from the MONGO_URI environment variable; no "
        "credentials are stored in the tool.",
        "Reads the fields: name, type, rating, price-rating, cuisine, location (city).",
        "Text filters are case-insensitive substring matches.",
    ],
    run=run,
)
