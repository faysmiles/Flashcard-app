# utils.py - COMPLETELY FIXED (Emojis + Images + Wikipedia)
import streamlit as st
import re
import os
import requests
import json
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI

# ==================== EMOJI PICKERS ====================

# Topic emojis: matched against a single keyword (the LLM-provided topic_keyword
# or the card title). Order doesn't matter much here since titles are short.
_TOPIC_EMOJI_MAP = {
    'dog': '🐕', 'dogs': '🐕', 'puppy': '🐕', 'puppies': '🐕', 'canine': '🐕',
    'cat': '🐈', 'cats': '🐈', 'kitten': '🐈', 'feline': '🐈',
    'lion': '🦁', 'lioness': '🦁', 'tiger': '🐅',
    'elephant': '🐘', 'elephants': '🐘',
    'giraffe': '🦒', 'giraffes': '🦒',
    'whale': '🐋', 'whales': '🐋', 'dolphin': '🐬', 'dolphins': '🐬',
    'bird': '🐦', 'birds': '🐦', 'eagle': '🦅', 'owl': '🦉',
    'butterfly': '🦋', 'butterflies': '🦋',
    'bee': '🐝', 'bees': '🐝',
    'fish': '🐟', 'fishes': '🐟', 'shark': '🦈',
    'snake': '🐍', 'snakes': '🐍',
    'frog': '🐸', 'frogs': '🐸',
    'rabbit': '🐰', 'rabbits': '🐰', 'bunny': '🐰',
    'horse': '🐴', 'horses': '🐴', 'pony': '🐴',
    'cow': '🐄', 'cows': '🐄', 'bull': '🐂',
    'pig': '🐷', 'pigs': '🐷',
    'sheep': '🐑', 'lambs': '🐑',
    'goat': '🐐', 'goats': '🐐',
    'monkey': '🐒', 'monkeys': '🐒', 'ape': '🦍',
    'bear': '🐻', 'bears': '🐻',
    'panda': '🐼', 'pandas': '🐼',
    'kangaroo': '🦘', 'koala': '🐨',
    'fox': '🦊', 'deer': '🦌', 'moose': '🦌',
    'zebra': '🦓', 'hippo': '🦛', 'rhino': '🦏',
    'moon': '🌙', 'planet': '🪐', 'star': '⭐', 'sun': '☀️',
    'atom': '⚛️', 'molecule': '🧪', 'dna': '🧬', 'cell': '🔬',
    'brain': '🧠', 'heart': '❤️', 'bone': '🦴',
    'tree': '🌳', 'flower': '🌸', 'leaf': '🌿', 'plant': '🌱',
    'mountain': '⛰️', 'volcano': '🌋', 'ocean': '🌊', 'river': '🏞️',
    'rain': '🌧️', 'snow': '❄️', 'lightning': '⚡',
}


# Fact emojis: ORDERED list of (keyword-list, emoji) tuples. The picker scans
# the FULL fact text and the first match wins, so put multi-word phrases and
# more specific concepts at the top.
_FACT_EMOJI_PATTERNS = [
    # --- Multi-word phrases (must come first to beat single-word matches) ---
    (["best friend", "best friends", "man's best friend"], "🤝"),
    (["body language"], "🗣️"),
    (["sign language"], "🤟"),
    (["sense of smell"], "👃"),
    (["world war", "civil war"], "⚔️"),
    (["solar system"], "🪐"),
    (["climate change", "global warming"], "🌡️"),
    (["food chain"], "🔗"),
    (["life cycle"], "🔄"),
    (["blood pressure"], "🩺"),
    (["blood vessel", "blood vessels"], "🫀"),
    (["nerve cell", "nerve cells", "nerve ending"], "🧠"),
    (["bone marrow"], "🦴"),
    (["immune system"], "🛡️"),
    (["digestive system", "digestive tract"], "🫃"),
    (["respiratory system", "respiratory tract"], "🫁"),
    (["nervous system"], "🧠"),
    (["carbon dioxide", "co2"], "💨"),
    (["natural selection"], "🧬"),
    (["tectonic plate", "tectonic plates"], "🌍"),
    (["periodic table"], "⚗️"),
    (["black hole"], "🕳️"),
    (["big bang"], "💥"),
    (["north pole", "south pole"], "🧭"),
    (["speed of light"], "⚡"),
    (["gravitational pull", "gravitational force"], "🌍"),
    (["water cycle"], "💧"),
    (["rock cycle"], "🪨"),
    (["carbon cycle"], "🔄"),
    (["nitrogen cycle"], "🌿"),
    (["photosynthesis"], "🌱"),
    (["cell division", "cell membrane"], "🔬"),
    (["endangered species", "endangered animal"], "⚠️"),
    (["apex predator"], "🏹"),

    # --- Senses ---
    (["communicate", "communication", "language", "speak", "speech", "talk", "talking", "conversation"], "💬"),
    (["bark", "barking", "howl", "growl", "meow", "roar", "hiss", "chirp", "screech"], "🔊"),
    (["sound", "noise", "vibration", "frequency", "echo", "ultrasound"], "🔊"),
    (["listen", "hearing", "ear", "ears"], "👂"),
    (["smell", "scent", "odor", "odour", "nose", "sniff", "sniffing"], "👃"),
    (["see", "sight", "vision", "eye", "eyes", "watch", "observe", "look"], "👀"),
    (["taste", "tongue", "flavour", "flavor", "bitter", "sweet", "sour", "salty"], "👅"),
    (["touch", "feel", "feeling", "texture", "sensitive", "sensitivity"], "✋"),

    # --- Relationships & social ---
    (["friend", "friendship", "companion", "buddy", "bond", "bonding"], "🤝"),
    (["family", "parent", "mother", "father", "offspring", "young"], "👨\u200d👩\u200d👧"),
    (["child", "children", "baby", "infant", "juvenile", "cub", "pup", "calf", "foal", "chick", "kit", "lamb", "fawn", "kitten"], "🍼"),
    (["love", "affection", "romance", "mate", "mating", "partner"], "❤️"),
    (["enemy", "fight", "fighting", "attack", "war", "battle", "combat", "conflict", "clash"], "⚔️"),
    (["pack", "group", "herd", "flock", "swarm", "colony", "pod", "pride", "troop", "school"], "👥"),
    (["lead", "leader", "dominant", "alpha", "hierarchy"], "👑"),
    (["cooperate", "cooperation", "teamwork", "together", "help", "helping"], "🤜"),
    (["compete", "competition", "rival", "rivalry"], "🏆"),

    # --- Animal behaviour ---
    (["migrate", "migration", "migrating", "hibernate", "hibernation"], "🧭"),
    (["camouflage", "disguise", "blend", "blending", "hide", "hiding"], "🎭"),
    (["venom", "poison", "toxic", "sting", "stinging", "venomous"], "☠️"),
    (["mark", "marking", "territory", "territorial", "claim"], "🚩"),
    (["hunt", "hunting", "predator", "prey", "stalk", "ambush", "chase"], "🏹"),
    (["scavenge", "scavenger", "carrion", "decompose", "decomposer"], "🦴"),
    (["pollinate", "pollination", "pollinator", "pollen", "nectar"], "🌸"),
    (["shed", "shedding", "moult", "moulting", "molt"], "🍂"),

    # --- General actions ---
    (["sleep", "sleeping", "rest", "resting", "nap", "dream", "dormant"], "😴"),
    (["eat", "eating", "food", "meal", "diet", "feed", "feeding", "consume", "digest"], "🍽️"),
    (["drink", "drinking", "thirst", "swallow"], "🥤"),
    (["urinate", "urinating", "urine", "excrete", "excretion", "waste", "defecate"], "💧"),
    (["breathe", "breathing", "breath", "inhale", "exhale", "lung", "lungs"], "🫁"),
    (["run", "running", "race", "sprint", "gallop"], "🏃"),
    (["jump", "leap", "hop", "bounce", "spring", "pounce"], "🦘"),
    (["swim", "swimming", "dive", "diving", "float", "aquatic"], "🏊"),
    (["fly", "flying", "flight", "soar", "glide", "hover"], "🕊️"),
    (["climb", "climbing", "scale", "scaling"], "🧗"),
    (["dig", "digging", "burrow", "burrowing", "tunnel"], "⛏️"),
    (["play", "playing", "fun", "game", "frolic", "playful"], "🎮"),
    (["learn", "learning", "study", "school", "education", "intelligence", "smart"], "🎓"),
    (["work", "working", "job", "labour", "labor", "task"], "💼"),
    (["build", "building", "construct", "construction", "create", "make"], "🏗️"),
    (["protect", "protection", "guard", "defend", "defense", "defence", "shield"], "🛡️"),
    (["grow", "growing", "growth", "develop", "development", "mature", "maturity"], "📈"),
    (["reproduce", "reproduction", "breed", "breeding", "spawn", "lay eggs", "give birth"], "🥚"),
    (["produce", "secrete", "secretion", "release"], "🏭"),

    # --- Body: animal-specific ---
    (["tail", "wag", "wagging"], "〰️"),
    (["paw", "paws", "claw", "claws", "talon", "talons", "hoof", "hooves"], "🐾"),
    (["fur", "coat", "fleece", "wool", "pelage"], "🐑"),
    (["hair", "mane", "bristle"], "💇"),
    (["teeth", "tooth", "fang", "fangs", "bite", "tusk", "tusks", "beak", "bill"], "🦷"),
    (["wing", "wings", "feather", "feathers", "plumage"], "🪶"),
    (["scale", "scales", "scaly", "shell", "carapace", "exoskeleton"], "🐢"),
    (["horn", "horns", "antler", "antlers", "spine", "spines", "quill", "quills"], "🦌"),
    (["gland", "glands", "organ", "organs"], "🫀"),
    (["muscle", "muscles", "muscular", "strength", "strong"], "💪"),
    (["skeleton", "skeletal", "vertebrate", "invertebrate"], "🦴"),

    # --- Human body ---
    (["heart", "cardiac", "cardiovascular", "pulse"], "🫀"),
    (["brain", "neuron", "neurons", "neural", "cortex", "cerebral", "cognitive"], "🧠"),
    (["blood", "vein", "veins", "artery", "arteries", "plasma"], "🩸"),
    (["bone", "bones", "skull", "spine", "rib", "femur"], "🦴"),
    (["skin", "dermis", "epidermis", "sweat", "pore", "pores"], "🧑"),
    (["kidney", "kidneys", "liver", "stomach", "intestine", "gut", "bowel"], "🫃"),
    (["eye", "eyes", "retina", "cornea", "pupil", "iris"], "👁️"),
    (["ear", "ears", "eardrum", "cochlea"], "👂"),
    (["throat", "trachea", "windpipe", "larynx", "vocal"], "🗣️"),
    (["cell", "cells", "nucleus", "mitochondria", "chromosome", "dna", "gene", "genes", "genetic"], "🧬"),
    (["hormone", "hormones", "adrenaline", "insulin"], "⚗️"),
    (["antibody", "antibodies", "immune", "immunity", "vaccination", "vaccine"], "💉"),

    # --- Plants ---
    (["root", "roots", "stem", "stems", "leaf", "leaves", "branch", "branches"], "🌿"),
    (["seed", "seeds", "germinate", "germination", "sprout", "sprouting"], "🌱"),
    (["flower", "flowers", "bloom", "blossom", "petal", "petals"], "🌸"),
    (["fruit", "fruits", "berry", "berries"], "🍎"),
    (["bark", "trunk", "wood", "timber", "ring", "rings"], "🪵"),
    (["algae", "moss", "lichen", "fern", "fungi", "mushroom", "spore"], "🍄"),
    (["chlorophyll", "chloroplast"], "☀️"),

    # --- Geology & earth science ---
    (["rock", "rocks", "mineral", "minerals", "crystal", "crystals", "gem", "gemstone"], "🪨"),
    (["volcano", "volcanic", "lava", "magma", "eruption", "erupt"], "🌋"),
    (["earthquake", "seismic", "tremor", "fault line"], "📳"),
    (["fossil", "fossils", "fossilised", "fossilized", "prehistoric"], "🦕"),
    (["glacier", "glacial", "iceberg", "ice sheet", "ice cap"], "🧊"),
    (["erosion", "erode", "sediment", "sedimentary", "weathering"], "🏜️"),
    (["soil", "dirt", "compost", "humus", "clay"], "🌱"),
    (["cave", "cavern", "stalagmite", "stalactite"], "🕳️"),
    (["atmosphere", "ozone", "stratosphere", "troposphere"], "🌍"),

    # --- Space ---
    (["star", "stars", "stellar", "supernova", "nebula", "galaxy", "galaxies"], "⭐"),
    (["moon", "lunar", "crater", "craters"], "🌙"),
    (["planet", "planets", "orbit", "orbits", "orbiting", "revolve", "rotation"], "🪐"),
    (["sun", "solar", "sunlight", "photon"], "☀️"),
    (["comet", "asteroid", "meteor", "meteorite"], "☄️"),
    (["gravity", "gravitational", "mass", "weight"], "🌍"),
    (["telescope", "observatory", "astronomy", "astronomer"], "🔭"),
    (["rocket", "spacecraft", "satellite", "astronaut", "nasa"], "🚀"),
    (["universe", "cosmos", "cosmic", "space", "infinite"], "🌌"),

    # --- Chemistry & physics ---
    (["atom", "atoms", "atomic", "electron", "proton", "neutron"], "⚛️"),
    (["molecule", "molecules", "molecular", "compound", "compounds"], "🔬"),
    (["element", "elements", "periodic", "carbon", "hydrogen", "nitrogen"], "⚗️"),
    (["acid", "acidic", "alkaline", "ph", "base"], "🧪"),
    (["reaction", "chemical reaction", "catalyst", "combustion", "oxidation"], "🧪"),
    (["temperature", "heat", "thermal", "boiling", "melting", "evaporation"], "🌡️"),
    (["pressure", "atmospheric pressure", "force", "newton"], "📐"),
    (["magnet", "magnetic", "magnetism", "electromagnetic"], "🧲"),
    (["wave", "waves", "wavelength", "amplitude"], "〰️"),
    (["radiation", "radioactive", "nuclear", "fission", "fusion"], "☢️"),

    # --- History & society ---
    (["empire", "emperor", "empress", "kingdom", "dynasty", "reign"], "👑"),
    (["revolution", "revolt", "rebellion", "uprising", "overthrow"], "✊"),
    (["trade", "trading", "merchant", "commerce", "economy", "silk road"], "💰"),
    (["slave", "slavery", "enslaved", "abolition", "abolitionist"], "⛓️"),
    (["vote", "voting", "election", "democracy", "parliament", "government"], "🗳️"),
    (["law", "laws", "legal", "court", "justice", "judge", "punishment"], "⚖️"),
    (["religion", "religious", "god", "gods", "worship", "temple", "church", "mosque", "prayer"], "🙏"),
    (["coloni", "imperialism", "conquer", "conquest"], "🌍"),
    (["invention", "inventor", "invent", "patent", "innovate"], "💡"),
    (["publish", "published", "printing", "press", "library"], "📚"),
    (["art", "artist", "painting", "sculpture", "museum"], "🎨"),
    (["music", "musician", "instrument", "compose", "composer", "symphony"], "🎵"),
    (["explore", "explorer", "expedition", "voyage", "navigation"], "🧭"),
    (["treaty", "agreement", "alliance", "negotiate", "diplomacy"], "🤝"),
    (["plague", "epidemic", "pandemic", "famine", "drought", "flood"], "⚠️"),

    # --- Technology ---
    (["computer", "computing", "software", "hardware", "code", "program", "algorithm"], "💻"),
    (["internet", "online", "network", "wifi", "digital", "cyber"], "🌐"),
    (["robot", "robotics", "artificial intelligence", "machine learning"], "🤖"),
    (["phone", "smartphone", "telephone", "mobile"], "📱"),
    (["electricity", "circuit", "battery", "current", "voltage", "wire"], "⚡"),
    (["engine", "motor", "machine", "mechanical", "gear"], "⚙️"),
    (["vehicle", "car", "train", "plane", "ship", "boat", "transport"], "🚗"),
    (["camera", "photograph", "image", "lens", "film"], "📷"),
    (["satellite", "gps", "signal", "radar"], "📡"),

    # --- Numbers, size, scale ---
    (["million", "billion", "trillion", "thousand", "many", "numerous", "vast"], "🔢"),
    (["percent", "percentage", "ratio", "proportion"], "📊"),
    (["big", "large", "huge", "giant", "enormous", "massive", "colossal"], "📏"),
    (["small", "tiny", "little", "miniature", "microscopic", "minuscule"], "🔍"),
    (["fast", "quick", "speed", "rapid", "swift", "velocity"], "⚡"),
    (["slow", "slowly", "gradual", "gradually"], "🐢"),
    (["heavy", "weight", "weigh"], "⚖️"),

    # --- Time ---
    (["old", "ancient", "historic", "historical", "past", "ago", "prehistoric"], "📜"),
    (["new", "modern", "recent", "today", "contemporary", "current"], "✨"),
    (["year", "years", "decade", "decades", "century", "centuries", "millennium"], "📅"),
    (["day", "days", "week", "weeks", "month", "months", "hour", "hours", "minute", "minutes", "second", "seconds"], "⏰"),
    (["dawn", "sunrise", "morning", "noon", "afternoon", "dusk", "sunset", "evening", "night", "midnight"], "🌅"),
    (["season", "seasons", "spring", "summer", "autumn", "fall", "winter"], "🍂"),

    # --- Direction & motion ---
    (["north", "south", "east", "west", "compass"], "🧭"),
    (["walk", "walked", "walking", "step", "stride", "pace"], "🚶"),
    (["travel", "travels", "journey", "voyage", "trip"], "✈️"),
    (["reflect", "reflects", "reflection", "mirror"], "🪞"),
    (["discover", "discovered", "discovery", "found", "finding"], "🔭"),
    (["map", "mapping", "chart", "charting", "survey"], "🗺️"),

    # --- Habitat / environment ---
    (["rainforest", "tropical", "tropics", "canopy"], "🌴"),
    (["forest", "wood", "woods", "jungle", "woodland", "taiga"], "🌳"),
    (["grassland", "savanna", "savannah", "prairie", "meadow"], "🌾"),
    (["desert", "sand", "dune", "arid"], "🏜️"),
    (["arctic", "polar", "tundra", "frozen", "antarctica"], "🧊"),
    (["wetland", "swamp", "marsh", "bog", "estuary"], "🌿"),
    (["reef", "coral", "ocean", "sea", "marine", "underwater"], "🌊"),
    (["river", "stream", "lake", "pond", "freshwater"], "🏞️"),
    (["mountain", "hill", "highland", "alpine", "peak", "summit"], "⛰️"),
    (["sky", "cloud", "clouds", "air"], "☁️"),
    (["island", "coast", "coastal", "beach", "shore", "bay"], "🏖️"),
    (["home", "house", "shelter", "den", "nest", "burrow", "lair", "dam"], "🏠"),
    (["city", "urban", "town", "metropolis", "suburb"], "🏙️"),
    (["farm", "rural", "countryside", "agriculture", "crop", "harvest"], "🚜"),

    # --- Weather & climate ---
    (["rain", "rainfall", "raining", "shower", "flooding"], "🌧️"),
    (["snow", "snowfall", "blizzard", "hail", "sleet"], "❄️"),
    (["wind", "windy", "gust", "breeze", "tornado", "typhoon", "cyclone", "hurricane"], "🌪️"),
    (["storm", "thunder", "thunderstorm", "lightning"], "⛈️"),
    (["fog", "mist", "humid", "humidity", "dew"], "🌫️"),

    # --- Science / abstract ---
    (["energy", "power", "nuclear", "kinetic", "potential"], "⚡"),
    (["water", "liquid", "fluid", "wet", "moisture"], "💧"),
    (["fire", "flame", "burn", "burning", "combustion", "ignite", "hot"], "🔥"),
    (["ice", "cold", "freeze", "freezing", "frost"], "❄️"),
    (["light", "bright", "shine", "glow", "luminous", "bioluminescent"], "💡"),
    (["dark", "darkness", "shadow", "night", "nocturnal"], "🌑"),
    (["health", "healthy", "medicine", "medical", "doctor", "treatment", "therapy"], "🩺"),
    (["disease", "illness", "sick", "infection", "virus", "bacteria", "pathogen"], "🦠"),
    (["danger", "dangerous", "risk", "warning", "hazard", "threat"], "⚠️"),
    (["safe", "safety", "secure", "protection"], "🛡️"),
    (["money", "cost", "price", "wealth", "poor", "rich"], "💰"),
    (["important", "essential", "key", "critical", "vital", "significant"], "⭐"),
    (["idea", "thought", "concept", "theory", "hypothesis", "model"], "💡"),
    (["question", "ask", "wonder", "curious", "curiosity", "mystery"], "❓"),
    (["answer", "solve", "solution", "result", "conclusion", "proof"], "✅"),
    (["change", "changes", "transform", "transformation", "evolve", "evolution"], "🔄"),
    (["balance", "balanced", "equilibrium", "stable", "stability"], "⚖️"),
    (["measure", "measurement", "calculate", "calculation", "estimate"], "📐"),
    (["record", "records", "data", "statistic", "statistics", "evidence"], "📊"),
    (["experiment", "test", "testing", "trial", "laboratory", "lab"], "🧪"),
    (["observe", "observation", "observing", "monitor", "monitoring"], "🔬"),

    # --- Generic animal catch-all (keep at bottom) ---
    (["dog", "dogs", "puppy", "puppies", "canine"], "🐕"),
    (["cat", "cats", "kitten", "kittens", "feline"], "🐈"),
    (["horse", "horses", "pony", "equine"], "🐴"),
    (["cow", "cows", "bull", "cattle", "bovine"], "🐄"),
    (["pig", "pigs", "boar", "porcine"], "🐷"),
    (["sheep", "lamb", "lambs", "ovine"], "🐑"),
    (["rabbit", "rabbits", "bunny", "hare"], "🐰"),
    (["bear", "bears", "grizzly", "polar bear"], "🐻"),
    (["wolf", "wolves", "coyote", "jackal"], "🐺"),
    (["fox", "foxes"], "🦊"),
    (["deer", "stag", "doe", "fawn", "moose", "elk", "reindeer"], "🦌"),
    (["elephant", "elephants", "mammoth"], "🐘"),
    (["giraffe", "giraffes"], "🦒"),
    (["zebra", "zebras"], "🦓"),
    (["lion", "lions", "lioness", "cheetah", "leopard", "panther"], "🦁"),
    (["tiger", "tigers"], "🐅"),
    (["monkey", "monkeys", "ape", "gorilla", "chimpanzee", "baboon"], "🐒"),
    (["hippo", "hippopotamus", "rhino", "rhinoceros"], "🦛"),
    (["crocodile", "alligator", "reptile"], "🐊"),
    (["turtle", "tortoise"], "🐢"),
    (["frog", "frogs", "toad", "amphibian"], "🐸"),
    (["snake", "snakes", "viper", "cobra", "python"], "🐍"),
    (["shark", "sharks"], "🦈"),
    (["whale", "whales", "dolphin", "dolphins", "porpoise", "orca"], "🐋"),
    (["octopus", "squid", "jellyfish", "crab", "lobster", "shrimp", "prawn"], "🐙"),
    (["eagle", "hawk", "falcon", "kite", "buzzard", "raptor"], "🦅"),
    (["penguin", "penguins"], "🐧"),
    (["parrot", "parrots", "macaw", "cockatoo"], "🦜"),
    (["owl", "owls"], "🦉"),
    (["bee", "bees", "wasp", "hornet", "bumblebee"], "🐝"),
    (["butterfly", "butterflies", "moth", "moths"], "🦋"),
    (["spider", "spiders", "scorpion"], "🕷️"),
    (["ant", "ants", "termite", "termites"], "🐜"),
    (["human", "humans", "people", "person", "man", "woman", "homo sapien"], "🧑"),
    (["plant", "plants"], "🌿"),
    (["tree", "trees"], "🌳"),
    (["flower", "flowers"], "🌸"),
    (["bird", "birds"], "🐦"),
    (["fish", "fishes"], "🐟"),
    (["insect", "insects", "bug", "bugs"], "🐛"),
]


def get_emoji_for_topic(text):
    """Pick an emoji for a card TOPIC (short string like 'Dogs as Pets')."""
    if not text:
        return '📚'
    text_lower = text.lower()
    for keyword, emoji in _TOPIC_EMOJI_MAP.items():
        if keyword in text_lower:
            return emoji
    return '📚'


def pick_fact_emoji(fact_text, fallback='✨'):
    """Pick an emoji based on KEYWORDS inside the fact text itself.

    Scans the full sentence for concept words (mark, communicate, friend, etc.)
    so each fact on a card gets a distinct, content-relevant icon instead of
    all sharing the topic emoji. Uses word-boundary matching so short keywords
    like 'ear' don't match inside 'Earth'.
    """
    if not fact_text:
        return fallback
    text_lower = fact_text.lower()
    for keywords, emoji in _FACT_EMOJI_PATTERNS:
        for kw in keywords:
            # Word-boundary match; supports multi-word phrases.
            pattern = r"\b" + re.escape(kw) + r"\b"
            if re.search(pattern, text_lower):
                return emoji
    return fallback


# ==================== AI IMAGE GENERATION VIA POLLINATIONS ====================

def _get_pollinations_key():
    try:
        return st.secrets.get("POLLINATIONS_API_KEY") or os.getenv("POLLINATIONS_API_KEY")
    except Exception:
        return os.getenv("POLLINATIONS_API_KEY")

@st.cache_data(show_spinner=False, ttl=3600)
def search_wikipedia_image(query):
    """Generate an image via Pollinations.ai for the given topic query.
    Kept the original function name so app.py needs no changes.
    Falls back to None if the key is missing or the request fails.
    """
    if not query:
        return None

    api_key = _get_pollinations_key()
    if not api_key:
        return None

    clean_query = re.sub(r'[^\w\s-]', '', query).strip()
    if not clean_query:
        return None

    prompt = (
        f"clean educational illustration of {clean_query}, "
        "simple background, suitable for children and students, "
        "bright clear colours, no text"
    )

    try:
        import urllib.parse
        encoded = urllib.parse.quote(prompt)
        url = f"https://gen.pollinations.ai/image/{encoded}?model=flux&key={api_key}&width=500&height=500&nologo=true"
        response = requests.get(url, timeout=30)
        if response.ok and response.headers.get("content-type", "").startswith("image"):
            # Cache the image via a data URL so the caller can use it like any URL
            import base64
            b64 = base64.b64encode(response.content).decode()
            mime = response.headers.get("content-type", "image/jpeg").split(";")[0]
            return f"data:{mime};base64,{b64}"
    except Exception as e:
        print(f"Pollinations error for '{clean_query}': {e}")

    return None


# ==================== DEEPSEEK FLASHCARD GENERATION ====================

@st.cache_data(show_spinner=False, ttl=3600)
def _fetch_flashcard_data_from_llm(raw_text, reading_level="intermediate"):
    """Call DeepSeek and return the raw parsed flashcard list (cached).

    Kept separate from enrichment so changing the emoji map doesn't require
    a cache flush - only the API call itself is memoised.
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets["DEEPSEEK_API_KEY"]
        except Exception:
            st.error("🔑 Missing DeepSeek API key")
            st.info("Add your key to .env or Streamlit secrets")
            return None

    # Scale card count
    n_chars = len(raw_text)
    if n_chars <= 8000:
        min_cards, max_cards = 3, 5
    elif n_chars <= 16000:
        min_cards, max_cards = 5, 8
    else:
        min_cards, max_cards = 8, 12

    # Reading level instructions
    if reading_level == "simple":
        level_text = "VERY SIMPLE: Use short words, short sentences (8-12 words max)"
    elif reading_level == "complex":
        level_text = "ADVANCED: Use precise academic language, longer sentences (up to 25 words)"
    else:
        level_text = "MEDIUM: Clear everyday language, medium sentences (12-18 words)"

    # Updated prompt: ask the LLM for a UNIQUE keyword per fact reflecting that
    # fact's content (not the card topic). Example shows varied hints.
    prompt = f"""Create {min_cards}-{max_cards} flashcards from this text.

READING LEVEL: {level_text}

IMPORTANT RULES:
- Each fact must have an "emoji_hint" which is ONE keyword describing what THAT
  specific fact is about (an action, concept, or object from the sentence).
- Do NOT just repeat the card topic in every emoji_hint - vary it per fact.
- For dog-related content, use 🐕; for cats use 🐈.
- Return ONLY valid JSON.

Example format (note how emoji_hint differs per fact):
{{
  "flashcards": [
    {{
      "title": "Dogs as Pets",
      "topic_keyword": "dog",
      "image_search": "dog",
      "facts": [
        {{"text": "Dogs mark their territory by urinating.", "emoji_hint": "territory"}},
        {{"text": "Dogs use body language to communicate.", "emoji_hint": "communicate"}},
        {{"text": "Dogs are known as man's best friend.", "emoji_hint": "best friend"}}
      ]
    }}
  ]
}}

TEXT:
{raw_text[:30000]}"""

    try:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You create flashcards. Each fact's emoji_hint is a unique keyword reflecting that fact's specific content - never just the topic. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=8000
        )
        content = response.choices[0].message.content
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        result = json.loads(content)
        return result.get("flashcards", [])

    except json.JSONDecodeError as e:
        st.error(f"JSON parsing error: {str(e)}")
        return None
    except Exception as e:
        st.error(f"API error: {str(e)}")
        return None


def generate_flashcards_from_llm(raw_text, reading_level="intermediate"):
    """Generate flashcards: cached LLM call + fresh emoji enrichment per fact.

    The emoji for each fact is picked from the FACT TEXT (not just the LLM's
    hint), so each bullet on a card reflects its own content.
    """
    raw_data = _fetch_flashcard_data_from_llm(raw_text, reading_level)
    if not raw_data:
        if raw_data is None:
            return None
        st.error("No flashcards generated")
        return None

    flashcards = []
    for card in raw_data:
        topic = card.get("title", "")
        topic_keyword = card.get("topic_keyword", topic)
        topic_emoji = get_emoji_for_topic(topic_keyword or topic)

        facts = []
        for fact in card.get("facts", [])[:4]:
            if isinstance(fact, dict):
                fact_text = fact.get("text", "")
                emoji_hint = fact.get("emoji_hint", "")
                # 1) Try the fact text itself (most accurate - matches concept words).
                # 2) Try the LLM's hint if the text didn't match.
                # 3) Fall back to the topic emoji (always relevant, never just '📚').
                fact_emoji = pick_fact_emoji(fact_text, fallback=None)
                if fact_emoji is None and emoji_hint:
                    fact_emoji = pick_fact_emoji(emoji_hint, fallback=None)
                if fact_emoji is None:
                    fact_emoji = topic_emoji
                facts.append({"emoji": fact_emoji, "text": fact_text})
            elif isinstance(fact, str):
                fact_emoji = pick_fact_emoji(fact, fallback=topic_emoji)
                facts.append({"emoji": fact_emoji, "text": fact})

        flashcards.append({
            'title': topic,
            'facts': facts,
            'emoji': topic_emoji,
            'image_search': card.get('image_search', topic_keyword),
        })

    return flashcards


# ==================== EXISTING HELPER FUNCTIONS (keep these) ====================

def get_card_colors(colour_scheme):
    """Derive card colours (text/label/accent) from the shared COLOR_SCHEMES table.

    Single source of truth: config.COLOR_SCHEMES. Adding a new scheme there
    automatically makes it work here.
    """
    palette = _get_scheme_palette(colour_scheme)
    return {
        "text": palette["text"],
        "label": palette["accent"],
        "accent": palette["accent"],
        "card_bg": palette["card_bg"],
    }


def extract_text_from_file(uploaded_file):
    try:
        if uploaded_file.type == "text/plain":
            return uploaded_file.read().decode('utf-8')
        elif uploaded_file.type == "application/pdf":
            import PyPDF2
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        elif "wordprocessingml" in uploaded_file.type:
            from docx import Document
            doc = Document(uploaded_file)
            return "\n".join([para.text for para in doc.paragraphs])
        else:
            return "Unsupported file type"
    except Exception as e:
        return f"Error: {str(e)}"


def fetch_image_bytes(url):
    if not url:
        return None
    try:
        if url.startswith("data:"):
            import base64
            header, data = url.split(",", 1)
            return base64.b64decode(data)
        r = requests.get(url, headers={"User-Agent": "FlashcardMagic/1.0"}, timeout=10)
        if r.ok:
            return r.content
    except:
        pass
    return None


def render_card_to_png(card, colors, idx, total, wiki_image_bytes=None, page_bg_hex="#F5F1E8"):
    """Simple PNG render that respects the chosen colour scheme."""
    W = 700
    MARGIN = 30

    card_bg = colors.get("card_bg", "#FFFFFF")

    img = Image.new("RGB", (W, 500), page_bg_hex)
    draw = ImageDraw.Draw(img)

    # Card background (respects dark/high-contrast schemes)
    draw.rectangle([MARGIN, MARGIN, W-MARGIN, 470], fill=card_bg, outline=colors['accent'], width=3)
    
    # Title
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
        small_font = ImageFont.truetype("DejaVuSans.ttf", 18)
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Center title
    bbox = draw.textbbox((0, 0), card['title'], font=font)
    text_width = bbox[2] - bbox[0]
    draw.text(((W - text_width) // 2, 100), card['title'], fill=colors['text'], font=font)
    
    # Draw facts
    y = 180
    for fact in card['facts'][:3]:
        text = fact.get('text', '')[:100]
        emoji = fact.get('emoji', '•')
        draw.text((MARGIN + 20, y), f"{emoji} {text}", fill=colors['text'], font=small_font)
        y += 45
    
    out = BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def build_cards_zip(flashcards, card_images, colors, page_bg_hex, cache_key):
    import zipfile
    zip_buf = BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, card in enumerate(flashcards[:10]):
            img_bytes = fetch_image_bytes(card_images.get(i))
            png = render_card_to_png(card, colors, i, len(flashcards), img_bytes, page_bg_hex)
            safe_title = re.sub(r'[^a-zA-Z0-9_-]+', '_', card['title'])[:30]
            zf.writestr(f"card_{i+1}_{safe_title}.png", png)
    return zip_buf.getvalue()


# ==================== COLOUR / THEME HELPERS ====================

def _get_scheme_palette(colour_scheme):
    """Look up a scheme by name across all groups in COLOR_SCHEMES."""
    from config import COLOR_SCHEMES
    for group in COLOR_SCHEMES.values():
        if colour_scheme in group:
            return group[colour_scheme]
    # Fallback - Soft Blue
    return COLOR_SCHEMES["Accessibility"]["Soft Blue"]


def _hex_to_rgb(hex_color):
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _relative_luminance(hex_color):
    """WCAG relative luminance (0 = black, 1 = white)."""
    def chan(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = _hex_to_rgb(hex_color)
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def _is_dark(hex_color):
    """True if a colour is dark enough to need light text on top of it."""
    return _relative_luminance(hex_color) < 0.4


def _contrast_ratio(fg_hex, bg_hex):
    """WCAG contrast ratio between two colours (1 = none, 21 = max)."""
    l1 = _relative_luminance(fg_hex)
    l2 = _relative_luminance(bg_hex)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def _on_color(bg_hex):
    """Return black or white - whichever has the HIGHER contrast on bg_hex.

    Uses true contrast ratios, not a luminance threshold, so mid-tone colours
    (orange, teal, yellow) correctly get black text instead of low-contrast white.
    """
    return "#000000" if _contrast_ratio("#000000", bg_hex) >= _contrast_ratio("#FFFFFF", bg_hex) else "#FFFFFF"


def _best_text_color(*bg_hexes):
    """Pick black or white maximising the WORST-CASE contrast across all bgs.

    For a gradient banner, pass both gradient stops so the chosen text colour
    stays readable along the entire banner, not just at one end.
    """
    black_min = min(_contrast_ratio("#000000", bg) for bg in bg_hexes)
    white_min = min(_contrast_ratio("#FFFFFF", bg) for bg in bg_hexes)
    return "#000000" if black_min >= white_min else "#FFFFFF"


def _mix(hex_color, target_hex, amount):
    """Blend hex_color toward target_hex by `amount` (0-1). Used for shading."""
    r1, g1, b1 = _hex_to_rgb(hex_color)
    r2, g2, b2 = _hex_to_rgb(target_hex)
    r = round(r1 + (r2 - r1) * amount)
    g = round(g1 + (g2 - g1) * amount)
    b = round(b1 + (b2 - b1) * amount)
    return f"#{r:02X}{g:02X}{b:02X}"


def _header_colors(colour_scheme):
    """Single source of truth for the header banner colours.

    Returns (accent, grad_end, title_color, subtitle_color). The gradient is
    shaded AWAY from the chosen text colour so contrast stays high across the
    whole banner. Used by both render_header (to draw the banner) and
    apply_styles (to emit the high-specificity colour rules that actually win).
    """
    palette = _get_scheme_palette(colour_scheme)
    accent = palette["accent"]
    title_color = _on_color(accent)
    if title_color == "#000000":
        grad_end = _mix(accent, "#FFFFFF", 0.14)   # lighten -> black text stays dark-on-light
        subtitle_color = "rgba(0,0,0,0.82)"
    else:
        grad_end = _mix(accent, "#000000", 0.22)   # darken  -> white text stays light-on-dark
        subtitle_color = "rgba(255,255,255,0.92)"
    return accent, grad_end, title_color, subtitle_color


def _star_color(colour_scheme):
    """A colourful star tone that 'suits' the scheme: a lightness-shifted tint
    of the scheme's own accent (same hue family). Paired with a title-colour
    outline in CSS so it stays visible on any banner. Low Stimulation gets none.
    """
    accent, _grad_end, title_color, _sub = _header_colors(colour_scheme)
    if title_color == "#FFFFFF":          # dark/saturated banner -> light tint pops
        return _mix(accent, "#FFFFFF", 0.55)
    return _mix(accent, "#000000", 0.42)  # lighter banner -> deeper shade pops


def render_header(app_title, app_subtitle, text_size, colour_scheme):
    """Header banner tinted to match the active scheme's accent colour.

    NOTE: the title/subtitle/star colours are NOT set reliably inline here.
    Streamlit's HTML sanitizer strips `!important` from inline style attributes,
    so an inline colour loses to the global `.stApp h1 { color: text !important }`
    rule - which paints the title in the body-text colour. On the High Contrast
    schemes that colour equals the banner background, making the title invisible.
    The real colours are applied by apply_styles() via `.fcm-header` class
    selectors inside a <style> block (where !important IS preserved) with higher
    specificity than the blanket rule. The inline colours below are a harmless
    fallback for the brief moment before the stylesheet loads.

    Decorative stars flank the title on every scheme EXCEPT Low Stimulation,
    which stays clean to reduce visual clutter for sensory-sensitive users.
    """
    accent, grad_end, title_color, subtitle_color = _header_colors(colour_scheme)
    star_color = _star_color(colour_scheme)

    if colour_scheme == "Low Stimulation":
        left_stars = right_stars = ""
    else:
        left_stars = (
            f"<span class='fcm-star fcm-star-sm' style='color:{star_color};'>✦</span>"
            f"<span class='fcm-star' style='color:{star_color};'>★</span> "
        )
        right_stars = (
            f" <span class='fcm-star' style='color:{star_color};'>★</span>"
            f"<span class='fcm-star fcm-star-sm' style='color:{star_color};'>✦</span>"
        )

    st.markdown(f"""
    <div class="fcm-header" style='text-align:center; padding:24px 20px;
                background:linear-gradient(135deg, {accent}, {grad_end});
                border-radius:14px; margin-bottom:20px;'>
        <h1 style='color:{title_color}; margin:0;
                   font-size:{text_size * 2}px;'>{left_stars}{app_title}{right_stars}</h1>
        <p style='color:{subtitle_color}; margin:12px 0 0 0;
                  font-size:{text_size}px;'>{app_subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


def render_feedback_box(feedback_url, colour_scheme):
    """Footer feedback box tinted to match the active scheme."""
    palette = _get_scheme_palette(colour_scheme)
    text = palette["text"]
    accent = palette["accent"]
    border = _mix(palette["bg"], text, 0.18)

    st.markdown(f"""
    <div style='text-align:center; padding:20px; margin-top:40px;
                border-top:1px solid {border};'>
        <p style='color:{text};'>💬 Help improve this app!
        <a href='{feedback_url}' target='_blank'
           style='color:{accent}; font-weight:700;'>Take Survey</a></p>
    </div>
    """, unsafe_allow_html=True)


def render_mobile_settings_hint(colour_scheme="Soft Blue"):
    """Settings hint banner tinted to match the active scheme."""
    palette = _get_scheme_palette(colour_scheme)
    text = palette["text"]
    accent = palette["accent"]
    # Soft tinted background derived from the accent so it never clashes.
    box_bg = _mix(palette["bg"], accent, 0.12)
    border = _mix(palette["bg"], accent, 0.30)

    st.markdown(f"""
    <div style='background:{box_bg}; padding:10px 14px; border-radius:8px;
                margin-bottom:15px; text-align:center; font-size:14px;
                border:1px solid {border}; color:{text};'>
        ⚙️ Tap the <strong style='color:{accent};'>arrow icon</strong> in the top-left corner to open settings!
    </div>
    """, unsafe_allow_html=True)


def apply_styles(font_style, text_size, colour_scheme, line_spacing=1.8):
    """Re-theme the whole Streamlit app to the chosen scheme.

    Streamlit applies its boot-time theme (from config.toml) via CSS custom
    properties on :root and high-specificity data-testid rules. To beat that
    we (1) override those custom properties and (2) restate the key surfaces
    with matching selectors + !important. This runs on every rerun, so the
    dropdown re-paints the entire page, not just the cards.
    """
    palette = _get_scheme_palette(colour_scheme)
    bg = palette["bg"]
    text = palette["text"]
    accent = palette["accent"]
    card_bg = palette["card_bg"]

    dark = _is_dark(bg)
    # Panels (sidebar, inputs) sit slightly off the page bg so they read as
    # distinct surfaces. Lighten on dark schemes, use white on light schemes.
    panel_bg = _mix(bg, "#FFFFFF", 0.10) if dark else "#FFFFFF"
    input_bg = panel_bg
    # Subtle borders derived from the text colour so they're visible on any bg.
    border_col = _mix(bg, text, 0.22)
    muted_text = _mix(bg, text, 0.65)
    on_accent = _on_color(accent)
    placeholder_col = _mix(input_bg, text, 0.45)

    # Header banner colours (shared source of truth with render_header).
    _, _, header_title_col, header_subtitle_col = _header_colors(colour_scheme)
    star_col = _star_color(colour_scheme)

    st.markdown(f"""
    <style>
    /* ---- Hide anchor link icons Streamlit adds to headings ---- */
    h1 a, h2 a, h3 a {{ display: none !important; }}

    /* ---- Override Streamlit's theme variables at the root ---- */
    :root, .stApp {{
        --background-color: {bg} !important;
        --default-background-color: {bg} !important;
        --secondary-background-color: {panel_bg} !important;
        --text-color: {text} !important;
        --primary-color: {accent} !important;
        --font: '{font_style}', sans-serif !important;
    }}

    /* ---- Fonts + base text ---- */
    html, body, [class*="css"], .stApp, [data-testid="stMarkdownContainer"] {{
        font-family: '{font_style}', sans-serif !important;
    }}
    .stApp p, .stApp li, .stApp label, .stApp span, .stMarkdown {{
        font-size: {text_size}px !important;
        line-height: {line_spacing} !important;
        color: {text} !important;
    }}
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {{
        color: {text} !important;
        font-family: '{font_style}', sans-serif !important;
    }}

    /* ---- Page background (multiple containers for reliability) ---- */
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    .main, .block-container {{
        background-color: {bg} !important;
        color: {text} !important;
    }}
    [data-testid="stHeader"], header[data-testid="stHeader"] {{
        background: {bg} !important;
    }}

    /* ---- Sidebar ---- */
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] > div {{
        background-color: {panel_bg} !important;
    }}
    [data-testid="stSidebar"] *,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span {{
        color: {text} !important;
    }}

    /* ---- Captions / hints ---- */
    .stApp [data-testid="stCaptionContainer"],
    .stApp small {{
        color: {muted_text} !important;
    }}

    /* ---- Text inputs / textareas ---- */
    .stTextInput input, .stTextArea textarea, .stNumberInput input {{
        background-color: {input_bg} !important;
        color: {text} !important;
        border: 1px solid {border_col} !important;
        border-radius: 8px !important;
    }}
    .stTextInput input::placeholder, .stTextArea textarea::placeholder {{
        color: {placeholder_col} !important;
        opacity: 1 !important;
    }}

    /* ---- Selectboxes (BaseWeb) ---- */
    div[data-baseweb="select"] > div {{
        background-color: {input_bg} !important;
        color: {text} !important;
        border: 1px solid {border_col} !important;
        border-radius: 8px !important;
    }}
    div[data-baseweb="select"] svg {{ fill: {text} !important; }}
    /* dropdown menu popover */
    div[data-baseweb="popover"] li,
    ul[role="listbox"] li {{
        background-color: {input_bg} !important;
        color: {text} !important;
    }}
    div[data-baseweb="popover"] li:hover,
    ul[role="listbox"] li:hover {{
        background-color: {_mix(input_bg, accent, 0.20)} !important;
    }}

    /* ---- Radio + checkbox ---- */
    .stRadio label, .stCheckbox label,
    [data-testid="stWidgetLabel"] label,
    [data-testid="stWidgetLabel"] p {{
        color: {text} !important;
    }}

    /* ---- Buttons (cover old + new Streamlit testids) ---- */
    .stButton > button,
    .stDownloadButton > button,
    [data-testid="stBaseButton-secondary"],
    [data-testid="stBaseButton-primary"],
    [data-testid="baseButton-secondary"],
    [data-testid="baseButton-primary"] {{
        background-color: {accent} !important;
        color: {on_accent} !important;
        border: 1px solid {accent} !important;
        border-radius: 10px !important;
        padding: 10px 20px !important;
        font-weight: 700 !important;
    }}
    .stButton > button *, .stDownloadButton > button * {{
        color: {on_accent} !important;
    }}
    .stButton > button:hover,
    .stDownloadButton > button:hover {{
        filter: brightness(1.08) !important;
    }}
    .stButton > button:disabled,
    .stDownloadButton > button:disabled {{
        opacity: 0.4 !important;
    }}

    /* ---- File uploader ---- */
    [data-testid="stFileUploader"] section,
    [data-testid="stFileUploaderDropzone"] {{
        background-color: {input_bg} !important;
        border: 1px dashed {border_col} !important;
        color: {text} !important;
    }}
    [data-testid="stFileUploader"] section * {{ color: {text} !important; }}

    /* ---- Slider ---- */
    .stSlider [data-baseweb="slider"] div[role="slider"] {{
        background-color: {accent} !important;
    }}
    .stSlider [data-testid="stTickBar"] {{ color: {muted_text} !important; }}

    /* ---- Links ---- */
    .stApp a {{ color: {accent} !important; }}

    /* ---- Header banner (HIGHER specificity than the blanket h1/p rules) ---- */
    /* These win because `.stApp .fcm-header h1` (0,2,1) beats `.stApp h1`     */
    /* (0,1,1). Set here in a <style> block - not inline - because Streamlit   */
    /* strips !important from inline style attributes.                         */
    .stApp .fcm-header h1 {{
        color: {header_title_col} !important;
    }}
    .stApp .fcm-header p {{
        color: {header_subtitle_col} !important;
    }}
    .stApp .fcm-header h1 * {{
        color: {header_title_col} !important;
    }}
    /* Decorative stars: themed colour + a crisp 1px outline in the title    */
    /* colour so they pop on any banner. Higher specificity (0,3,0) than the  */
    /* `.fcm-header h1 *` rule (0,2,1) so the star colour wins.               */
    .stApp .fcm-header .fcm-star {{
        color: {star_col} !important;
        display: inline-block;
        text-shadow: -1px -1px 0 {header_title_col}, 1px -1px 0 {header_title_col},
                     -1px 1px 0 {header_title_col}, 1px 1px 0 {header_title_col};
    }}
    .stApp .fcm-header .fcm-star-sm {{
        font-size: 0.6em;
        vertical-align: 0.25em;
        opacity: 0.9;
    }}
    </style>
    """, unsafe_allow_html=True)
