"""The business each video is a website for.

The component is not the subject. A local business is: an auto shop, a
gardener, a dentist. The component is chosen because it fits that business's
one memorable moment -- a marquee of number plates for a garage, a globe for a
firm that ships, a beam diagram for a workflow -- and the video sells the
website, not the library.

Names are invented. These are concept sites for fictional businesses, so
nothing here should match a real trading name; the generator combines a made-up
word with the trade rather than using anything recognisable.
"""
import random

# `fits` are substrings matched against component file names. A business gets a
# component whose idea suits its one big moment; when nothing matches we fall
# back to any component rather than skipping the business.
NICHES = [
    {
        "trade": "auto repair shop",
        "services": ["Diagnostics", "Brakes & suspension", "MOT prep", "Engine rebuilds"],
        "moment": "a before/after of a car brought back to life",
        "tone": "industrial, confident, high-contrast, oil-and-steel",
        "fits": ["marquee", "beam", "ticker", "scroll", "reveal", "compare", "progress"],
        "photo_query": "car repair garage mechanic",
    },
    {
        "trade": "garden design studio",
        "services": ["Planting plans", "Hard landscaping", "Maintenance", "Lighting"],
        "moment": "the same garden through four seasons",
        "tone": "calm, editorial, deep greens, generous white space",
        "fits": ["blur", "fade", "parallax", "grid", "reveal", "marquee", "text"],
        "photo_query": "garden landscaping green plants",
    },
    {
        "trade": "artisan bakery",
        "services": ["Sourdough", "Pastry", "Wholesale", "Celebration cakes"],
        "moment": "dough proving, shot close and warm",
        "tone": "warm, tactile, cream and burnt orange, serif headlines",
        "fits": ["marquee", "text", "reveal", "grid", "orbit", "ripple"],
        "photo_query": "artisan bakery bread pastry",
    },
    {
        "trade": "dental practice",
        "services": ["Check-ups", "Implants", "Whitening", "Emergency care"],
        "moment": "a calm, reassuring booking flow",
        "tone": "clean, clinical but human, soft blues, lots of air",
        "fits": ["beam", "progress", "grid", "fade", "orbit", "border"],
        "photo_query": "modern dental clinic interior",
    },
    {
        "trade": "roofing contractor",
        "services": ["Flat roofs", "Slate & tile", "Guttering", "Emergency repairs"],
        "moment": "a drone shot climbing a finished roofline",
        "tone": "solid, weatherproof, slate greys, big plain numbers",
        "fits": ["scroll", "reveal", "marquee", "grid", "beam", "globe"],
        "photo_query": "roofer roofing house construction",
    },
    {
        "trade": "coffee roastery",
        "services": ["Single origin", "Subscriptions", "Wholesale", "Barista training"],
        "moment": "beans falling in slow motion as you scroll",
        "tone": "dark, rich, editorial, tight type, one accent colour",
        "fits": ["marquee", "text", "ripple", "orbit", "reveal", "particles"],
        "photo_query": "coffee roastery beans espresso",
    },
    {
        "trade": "yoga studio",
        "services": ["Vinyasa", "Beginners", "Prenatal", "Teacher training"],
        "moment": "a timetable that breathes as it scrolls",
        "tone": "soft, warm neutrals, unhurried motion, thin type",
        "fits": ["fade", "blur", "text", "grid", "orbit", "ripple"],
        "photo_query": "yoga studio interior calm",
    },
    {
        "trade": "electrical contractor",
        "services": ["Rewiring", "EV chargers", "Fault finding", "Commercial fit-out"],
        "moment": "current tracing along a circuit as you scroll",
        "tone": "technical, dark, one electric accent, precise grid",
        "fits": ["beam", "ripple", "grid", "pattern", "progress", "particles"],
        "photo_query": "electrician working wiring",
    },
]

# Invented brand words: nothing that reads as an existing chain.
_WORDS = ["Kestrel", "Halden", "Ironwood", "Marlow", "Thistle", "Verrick", "Brackley",
          "Norwood", "Fenwick", "Ashgrove", "Calder", "Rowan", "Petrichor", "Larkspur"]
_SUFFIX = {
    "auto repair shop": ["Motor Works", "Auto", "Garage"],
    "garden design studio": ["Gardens", "Landscapes", "Green"],
    "artisan bakery": ["Bakehouse", "Bakery", "& Crumb"],
    "dental practice": ["Dental", "Dental Care", "Smile Studio"],
    "roofing contractor": ["Roofing", "Roofworks", "Contracts"],
    "coffee roastery": ["Coffee Roasters", "Roastery", "Coffee Co."],
    "yoga studio": ["Yoga", "Studio", "Movement"],
    "electrical contractor": ["Electrical", "Electrics", "Power"],
}
_CITIES = ["Bristol", "Leeds", "Cluj", "Porto", "Ghent", "Aarhus", "Utrecht", "Cork"]


def dress(niche, rng=None):
    """Give a niche a name and a city. Separate from pick() so forcing a trade
    still gets a name from THAT trade's suffixes -- taking the name from a
    second pick() produced 'Halden Crumb', a bakery name, on an auto shop."""
    rng = rng or random.Random()
    return {
        **niche,
        "name": f"{rng.choice(_WORDS)} {rng.choice(_SUFFIX[niche['trade']])}",
        "city": rng.choice(_CITIES),
    }


def pick(used_trades=(), seed=None):
    rng = random.Random(seed)
    fresh = [n for n in NICHES if n["trade"] not in used_trades] or NICHES
    return dress(rng.choice(fresh), rng)


def choose_component(business, candidates, seed=None):
    """The component that suits this business, not whatever came first."""
    rng = random.Random(seed)
    matches = [c for c in candidates
               if any(f in c["name"].lower() for f in business["fits"])]
    return rng.choice(matches or candidates)
