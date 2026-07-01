"""
Single source of truth for the news taxonomy.

The frontend asks the backend for its channels (/api/categories) so the colour
coding and labels live in ONE place. Each external provider has its own
category vocabulary, so we keep:
  * <PROVIDER>_PARAM : canonical key -> the category string that provider expects
  * KEYWORDS         : fallback classifier when a provider returns a category we
                       don't map (or none at all)
"""

CATEGORIES = [
    {"key": "politics",    "label": "Politics",    "color": "#D6453D"},
    {"key": "economy",     "label": "Economy",     "color": "#1FA47A"},
    {"key": "society",     "label": "Society",     "color": "#7C5CFC"},
    {"key": "culture",     "label": "Culture",     "color": "#E0A82E"},
    {"key": "technology",  "label": "Technology",  "color": "#2D6FF0"},
    {"key": "environment", "label": "Environment", "color": "#3DA35D"},
    {"key": "health",      "label": "Health",      "color": "#E2557B"},
    {"key": "science",     "label": "Science",     "color": "#16A8B8"},
    {"key": "sports",      "label": "Sports",      "color": "#F2792E"},
]

CANON = {c["key"] for c in CATEGORIES}
DEFAULT_CAT = "society"

# canonical -> provider's own category param
NEWSAPI_PARAM = {
    "economy": "business", "technology": "technology", "health": "health",
    "science": "science", "sports": "sports", "culture": "entertainment",
    # politics / society / environment fall back to general
}
GNEWS_PARAM = {
    "politics": "nation", "economy": "business", "technology": "technology",
    "health": "health", "science": "science", "sports": "sports",
    "culture": "entertainment", "society": "general",
    # environment -> general
}
NEWSDATA_PARAM = {
    "politics": "politics", "economy": "business", "society": "top",
    "culture": "entertainment", "technology": "technology",
    "environment": "environment", "health": "health", "science": "science",
    "sports": "sports",
}
CURRENTS_PARAM = {
    "politics": "politics", "economy": "business", "society": "general",
    "culture": "entertainment", "technology": "technology",
    "environment": "environment", "health": "health", "science": "science",
    "sports": "sports",
}

# reverse hint: map a provider category string back to a canonical key
PROVIDER_CAT_TO_CANON = {
    "business": "economy", "entertainment": "culture", "technology": "technology",
    "tech": "technology", "health": "health", "science": "science",
    "sports": "sports", "sport": "sports", "politics": "politics",
    "environment": "environment", "nation": "politics", "world": "society",
    "general": "society", "top": "society", "food": "culture",
    # Currents v2 canonical taxonomy
    "science_technology": "technology", "politics_government": "politics",
    "economy_business_finance": "economy", "arts_culture_entertainment": "culture",
    "sport": "sports", "crime_law_justice": "politics", "labour": "economy",
    "lifestyle_leisure": "culture", "human_interest": "society",
}

# keyword classifier (lowercased substring match against title + description)
KEYWORDS = {
    "politics":    ["election", "parliament", "senate", "minister", "policy", "government", "vote", "bill", "diplomat", "border", "treaty"],
    "economy":     ["inflation", "market", "stocks", "trade", "gdp", "bank", "economy", "interest rate", "jobs", "tariff", "currency", "shipping"],
    "society":     ["community", "housing", "education", "workers", "social", "city", "welfare", "migration", "volunteer"],
    "culture":     ["film", "music", "art", "book", "festival", "museum", "theatre", "fashion", "celebrity"],
    "technology":  ["ai", "software", "startup", "chip", "app", "robot", "model", "data", "cyber", "device", "search"],
    "environment": ["climate", "carbon", "renewable", "wetland", "emissions", "solar", "wildlife", "pollution", "grid"],
    "health":      ["health", "clinic", "vaccine", "disease", "mental", "sleep", "patient", "hospital", "heart"],
    "science":     ["galaxy", "research", "study", "physics", "lab", "astronom", "particle", "experiment", "material"],
    "sports":      ["match", "league", "team", "title", "player", "tournament", "season", "coach", "championship"],
}


from .classifier import classify  # noqa: F401  (re-exported for adapters)


def param_for(provider: str, canon_key: str | None, default: str = "general") -> str | None:
    """Translate a canonical channel into the provider's category param."""
    if not canon_key or canon_key == "all":
        return None
    table = {
        "newsapi": NEWSAPI_PARAM,
        "gnews": GNEWS_PARAM,
        "newsdata": NEWSDATA_PARAM,
        "currents": CURRENTS_PARAM,
    }.get(provider, {})
    return table.get(canon_key, default)
