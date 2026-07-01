"""Self-contained news classifier (rule-based, India-tuned).

Primary: weighted keyword scoring over title + description across 9 channels.
Title matches count double. Matching is suffix-tolerant (launch/launches/launched).
Safety net: if NOTHING scores, fall back to the API's own category tag (mapped),
and only then to 'society'. So classification is our-logic-first, but messy
headlines with no keyword still land sensibly instead of all piling into society.
"""

import re

DEFAULT = "society"

# Tie-break order: earlier wins on equal score.
PRIORITY = ["politics", "economy", "technology", "science", "health",
            "environment", "sports", "culture", "society"]

KEYWORDS = {
    "politics": {
        "election": 2, "parliament": 3, "lok sabha": 3, "rajya sabha": 3, "assembly": 1,
        "minister": 2, "prime minister": 3, "chief minister": 3, "president": 2, "governor": 2,
        "government": 1, "sarkar": 2, "policy": 1, "bill": 1, "ordinance": 2, "vote": 2,
        "ballot": 2, "poll": 2, "constituency": 2, "cabinet": 2, "coalition": 2, "manifesto": 2,
        "campaign": 1, "bjp": 3, "congress party": 3, "opposition": 2, "mla": 2, "mp": 1,
        "pmo": 3, "ministry": 1, "diplomat": 2, "diplomacy": 2, "bilateral": 2, "summit": 1,
        "border": 1, "treaty": 2, "sanction": 2, "supreme court": 2, "verdict": 1, "petition": 1,
        "law": 1, "legislation": 2, "protest": 1, "modi": 3, "geopolitics": 2, "referendum": 2,
        "parliamentary": 2, "foreign policy": 2, "defence deal": 2,
    },
    "economy": {
        "economy": 2, "economic": 2, "gdp": 3, "inflation": 3, "deflation": 2, "recession": 2,
        "repo rate": 3, "interest rate": 2, "monetary": 2, "fiscal": 2, "sensex": 3, "nifty": 3,
        "bse": 2, "nse": 2, "stock market": 3, "stock": 1, "share": 1, "rupee": 3, "dollar": 1,
        "forex": 2, "rbi": 3, "ipo": 3, "gst": 3, "income tax": 2, "tax": 1, "budget": 2,
        "subsidy": 1, "fdi": 2, "export": 1, "import": 1, "manufacturing": 1, "msme": 2,
        "unemployment": 2, "layoff": 2, "hiring": 1, "wage": 1, "salary": 1, "revenue": 1,
        "turnover": 1, "profit": 1, "quarterly result": 2, "earnings": 2, "merger": 2,
        "acquisition": 2, "funding": 2, "valuation": 2, "unicorn": 2, "bond": 1, "trade": 1,
        "tariff": 2, "crude oil": 2, "gold price": 2, "market": 1, "investment": 1, "economy slump": 2,
    },
    "technology": {
        "artificial intelligence": 3, "machine learning": 3, "generative ai": 3, "chatgpt": 3,
        "openai": 3, "llm": 3, "software": 2, "hardware": 2, "app": 1, "application": 1,
        "smartphone": 2, "iphone": 2, "android": 2, "laptop": 1, "gadget": 2, "chip": 2,
        "semiconductor": 3, "processor": 2, "gpu": 2, "startup": 1, "saas": 2, "cloud computing": 2,
        "server": 1, "cybersecurity": 3, "hacking": 2, "malware": 3, "data breach": 3,
        "encryption": 2, "blockchain": 2, "crypto": 2, "bitcoin": 3, "ethereum": 3, "5g": 2,
        "iot": 2, "robotics": 2, "automation": 1, "drone": 2, "coding": 2, "programming": 2,
        "developer": 1, "google": 2, "apple": 2, "microsoft": 2, "meta": 1, "nvidia": 3,
        "internet": 1, "cyber": 2, "tech": 1, "algorithm": 2,
    },
    "science": {
        "research": 1, "study": 1, "scientist": 2, "discovery": 2, "experiment": 2, "space": 2,
        "isro": 3, "nasa": 3, "spacex": 3, "satellite": 2, "rocket": 2, "space mission": 3,
        "mars": 2, "moon mission": 3, "chandrayaan": 3, "gaganyaan": 3, "galaxy": 2, "universe": 2,
        "physics": 2, "chemistry": 2, "biology": 2, "genetics": 2, "genome": 2, "dna": 2,
        "telescope": 2, "particle": 2, "quantum": 2, "fusion": 2, "breakthrough": 1,
        "peer-reviewed": 2, "astronomy": 3, "spacecraft": 2, "lab": 1, "molecule": 2,
    },
    "health": {
        "health": 2, "healthcare": 2, "hospital": 2, "clinic": 2, "doctor": 2, "nurse": 1,
        "patient": 2, "disease": 2, "illness": 2, "virus": 2, "infection": 2, "covid": 3,
        "coronavirus": 3, "flu": 2, "dengue": 3, "malaria": 3, "cancer": 3, "tumor": 3,
        "diabetes": 3, "cardiac": 2, "heart attack": 3, "stroke": 2, "vaccine": 3, "vaccination": 3,
        "immunity": 2, "medicine": 2, "drug": 1, "pharma": 2, "treatment": 1, "therapy": 1,
        "surgery": 2, "mental health": 3, "depression": 2, "anxiety": 2, "wellness": 1,
        "obesity": 2, "nutrition": 2, "outbreak": 2, "epidemic": 2, "pandemic": 2, "icu": 2,
    },
    "environment": {
        "climate": 3, "climate change": 3, "global warming": 3, "carbon": 2, "emission": 2,
        "greenhouse": 2, "renewable": 2, "solar": 2, "wind energy": 2, "clean energy": 2,
        "pollution": 3, "air quality": 2, "aqi": 3, "smog": 2, "plastic waste": 2, "recycling": 2,
        "wildlife": 2, "forest": 2, "deforestation": 3, "biodiversity": 2, "endangered": 2,
        "flood": 2, "drought": 2, "cyclone": 3, "heatwave": 2, "monsoon": 2, "rainfall": 1,
        "glacier": 2, "sea level": 2, "sustainability": 2, "ecosystem": 2, "conservation": 2,
        "environment": 2, "electric vehicle": 1, "climate crisis": 3,
    },
    "sports": {
        "cricket": 3, "ipl": 3, "t20": 3, "odi": 3, "test match": 3, "world cup": 3, "wicket": 3,
        "batsman": 3, "batter": 2, "bowler": 3, "century": 1, "innings": 3, "kohli": 3, "rohit": 2,
        "dhoni": 3, "bumrah": 3, "football": 2, "fifa": 3, "premier league": 3, "isl": 2,
        "goal": 1, "striker": 2, "messi": 3, "ronaldo": 3, "olympics": 3, "medal": 2,
        "gold medal": 3, "athlete": 2, "tennis": 3, "wimbledon": 3, "grand slam": 3,
        "badminton": 3, "hockey": 2, "kabaddi": 3, "chess": 2, "tournament": 2, "championship": 2,
        "league": 1, "match": 1, "final": 1, "stadium": 1, "captain": 1, "squad": 1,
    },
    "culture": {
        "film": 2, "movie": 2, "cinema": 2, "bollywood": 3, "hollywood": 2, "tollywood": 3,
        "box office": 3, "actor": 2, "actress": 2, "director": 1, "producer": 1, "trailer": 2,
        "teaser": 2, "ott": 2, "netflix": 2, "prime video": 2, "web series": 2, "music": 2,
        "song": 2, "album": 2, "singer": 2, "concert": 2, "art": 1, "painting": 2, "exhibition": 2,
        "museum": 2, "book": 1, "novel": 2, "author": 1, "literature": 2, "festival": 1,
        "diwali": 2, "holi": 2, "fashion": 2, "award": 1, "oscar": 3, "filmfare": 3, "celebrity": 2,
    },
    "society": {
        "education": 2, "school": 1, "college": 1, "university": 1, "student": 1, "exam": 1,
        "cbse": 2, "admission": 1, "scholarship": 2, "housing": 2, "real estate": 2,
        "community": 1, "welfare": 2, "scheme": 1, "poverty": 2, "migration": 2, "refugee": 2,
        "labour": 1, "worker": 1, "women": 1, "gender": 1, "caste": 2, "dalit": 2, "tribal": 2,
        "religion": 1, "temple": 1, "crime": 1, "murder": 2, "theft": 1, "assault": 1,
        "arrest": 1, "police": 1, "accident": 1, "road accident": 2, "fire": 1, "rescue": 1,
        "strike": 1, "rally": 1, "human rights": 2, "ngo": 1, "railway": 1, "metro": 1, "traffic": 1,
    },
}

# When our engine scores 0, map the API's raw tag to a channel (last resort).
FALLBACK_MAP = {
    "business": "economy", "finance": "economy", "economy_business_finance": "economy",
    "entertainment": "culture", "arts_culture_entertainment": "culture", "lifestyle": "culture",
    "lifestyle_leisure": "culture", "food": "culture", "technology": "technology",
    "tech": "technology", "science_technology": "technology", "science": "science",
    "health": "health", "sport": "sports", "sports": "sports", "politics": "politics",
    "politics_government": "politics", "environment": "environment", "world": "society",
    "general": "society", "top": "society", "nation": "politics", "education": "society",
    "crime_law_justice": "society", "human_interest": "society", "labour": "society",
}


def _compile(term: str):
    # suffix-tolerant for plain single words; exact-ish for multiword / has digit
    if term.isalpha() and " " not in term:
        return re.compile(r"\b" + re.escape(term) + r"(?:s|es|ed|ing)?\b")
    return re.compile(r"\b" + re.escape(term) + r"s?\b")


_PATTERNS = {ch: [(_compile(t), w) for t, w in terms.items()] for ch, terms in KEYWORDS.items()}


def classify(title: str, description: str = "", fallback=None) -> str:
    t = (title or "").lower()
    d = (description or "").lower()
    scores = {ch: 0 for ch in KEYWORDS}
    for ch, pats in _PATTERNS.items():
        for pat, w in pats:
            if pat.search(t):
                scores[ch] += w * 2
            elif pat.search(d):
                scores[ch] += w
    best = max(PRIORITY, key=lambda c: (scores[c], -PRIORITY.index(c)))
    if scores[best] > 0:
        return best
    # zero score -> consult the API's own tag, then default
    if fallback:
        if isinstance(fallback, (list, tuple)):
            fallback = fallback[0] if fallback else None
        if fallback:
            key = str(fallback).strip().lower()
            if key in KEYWORDS:
                return key
            if key in FALLBACK_MAP:
                return FALLBACK_MAP[key]
    return DEFAULT
