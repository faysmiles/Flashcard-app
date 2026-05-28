# config.py - Complete app configuration

APP_TITLE = "Iconic Flashcard app"
APP_SUBTITLE = "Turn your pages of notes into visual flashcards for easier, faster learning"

# Reading levels
READING_LEVELS = {
    "📖 Easy (Ages 4-11)": "simple",
    "📚 Medium (Ages 11-18)": "intermediate",
    "🎓 Advanced (Ages 18+)": "complex"
}

# Font options - expanded!
FONT_OPTIONS = [
    "OpenDyslexic", "Lexend", "Verdana", "Arial", "Calibri", 
    "Tahoma", "Georgia", "Trebuchet MS", "Poppins", "Nunito", 
    "Montserrat", "Lato", "Roboto", "Inter", "Comic Sans MS", 
    "Caveat", "Pacifico", "Merriweather", "Fira Code"
]

# Color schemes
COLOR_SCHEMES = {
    "Accessibility": {
        "Soft Blue": {"bg": "#E8F1F5", "text": "#1C3A42", "accent": "#3A7CA5", "card_bg": "#FFFEF9"},
        "Pale Lavender": {"bg": "#F5E8F5", "text": "#3C2C42", "accent": "#7C3C9C", "card_bg": "#FFFEF9"},
        "Pale Mint": {"bg": "#E8F5F1", "text": "#1C3C32", "accent": "#2F7A55", "card_bg": "#FFFEF9"},
        "Low Stimulation": {"bg": "#F2F2EC", "text": "#2E2E2E", "accent": "#7A7A7A", "card_bg": "#F9F9F5"},
    },
    "Vibrant": {
        "Sunset Orange": {"bg": "#FFF3E0", "text": "#4A2400", "accent": "#FF6F00", "card_bg": "#FFFFFF"},
        "Ocean Teal": {"bg": "#E0F7FA", "text": "#004D40", "accent": "#00ACC1", "card_bg": "#FFFFFF"},
        "Forest Green": {"bg": "#E8F5E9", "text": "#1B5E20", "accent": "#43A047", "card_bg": "#FFFFFF"},
        "Royal Purple": {"bg": "#F3E5F5", "text": "#4A148C", "accent": "#AB47BC", "card_bg": "#FFFFFF"},
        "Cherry Red": {"bg": "#FFEBEE", "text": "#B71C1C", "accent": "#EF5350", "card_bg": "#FFFFFF"},
        "Sunshine Yellow": {"bg": "#FFFDE7", "text": "#5C4500", "accent": "#F9A825", "card_bg": "#FFFFFF"},
    },
    "High Contrast": {
        # Classic accessibility pairings - WCAG AAA at all sizes (21:1 contrast)
        "Black on White": {"bg": "#FFFFFF", "text": "#000000", "accent": "#000000", "card_bg": "#FFFFFF"},
        "White on Black": {"bg": "#000000", "text": "#FFFFFF", "accent": "#FFFFFF", "card_bg": "#0A0A0A"},
        "Yellow on Black": {"bg": "#000000", "text": "#FFEB3B", "accent": "#FFEB3B", "card_bg": "#0A0A0A"},
        "Cream on Navy": {"bg": "#0D1B2A", "text": "#FFF8E7", "accent": "#FFB703", "card_bg": "#1B263B"},
    },
}

MIN_FONT_SIZE = 12
MAX_FONT_SIZE = 40
DEFAULT_FONT_SIZE = 18

# DeepSeek settings
DEEPSEEK_MODEL = "deepseek-chat"
MAX_TOKENS = 4000
TEMPERATURE = 0.7

# Emoji database (200+)
EMOJI_CATEGORIES = {
    "lion|tiger|leopard|cheetah|cougar": "🦁",
    "elephant|mammoth": "🐘",
    "giraffe": "🦒",
    "monkey|ape|gorilla|chimp|chimpanzee": "🐵",
    "whale|dolphin|porpoise|orca": "🐋",
    "shark": "🦈",
    "fish|fishing|swim": "🐟",
    "bird|eagle|hawk|owl|falcon": "🦅",
    "penguin": "🐧",
    "butterfly|caterpillar": "🦋",
    "bee|wasp|honey": "🐝",
    "spider|web": "🕷️",
    "snake|reptile|lizard": "🐍",
    "dinosaur|fossil|trex": "🦕",
    "tree|forest|wood|timber|oak": "🌳",
    "flower|rose|daisy|bloom|garden": "🌸",
    "leaf|plant|herb|green": "🌿",
    "mountain|hill|peak|summit": "⛰️",
    "volcano|lava|eruption": "🌋",
    "ocean|sea|wave|water|marine": "🌊",
    "river|stream|lake|pond": "🏞️",
    "rain|storm|thunder|lightning|hurricane": "⛈️",
    "snow|ice|glacier|frost|arctic": "❄️",
    "sun|sunlight|sunshine|solar": "☀️",
    "moon|lunar|moonlight|crescent": "🌙",
    "star|space|galaxy|universe|cosmic": "⭐",
    "planet|orbit|solar system|mars|jupiter": "🪐",
    "atom|molecule|particle|quantum": "⚛️",
    "dna|gene|genetic|chromosome|heredity": "🧬",
    "cell|biology|microscope|cellular": "🔬",
    "chemistry|chemical|reaction|beaker": "🧪",
    "physics|gravity|force|motion|newton": "⚡",
    "electricity|circuit|energy|battery": "⚡",
    "robot|ai|artificial intelligence|android": "🤖",
    "computer|code|software|programming|algorithm": "💻",
    "internet|wifi|network|online|web": "🌐",
    "data|statistic|graph|chart|analytics": "📊",
    "rocket|spacecraft|astronaut|launch": "🚀",
    "alien|extraterrestrial|ufo|mars": "👽",
    "telescope|observatory|astronomy": "🔭",
    "heart|cardiac|blood|vein|artery": "❤️",
    "brain|neuron|mind|thought|intelligence": "🧠",
    "medicine|drug|pill|tablet|vaccine": "💊",
    "hospital|clinic|doctor|nurse|medical": "🏥",
    "virus|bacteria|germ|infection|disease": "🦠",
    "king|queen|royal|crown|throne|monarchy": "👑",
    "castle|fortress|fort|palace": "🏰",
    "sword|knight|medieval|battle|warrior": "⚔️",
    "pyramid|egypt|pharaoh|tomb": "🔺",
    "ancient|ruin|archaeology|artifact": "🏛️",
    "music|song|melody|rhythm|concert": "🎵",
    "guitar|instrument|band|orchestra": "🎸",
    "paint|draw|art|artist|canvas|painting": "🎨",
    "book|story|novel|author|literature": "📖",
    "poem|poetry|rhyme|verse": "📝",
    "apple|fruit|orchard|orchard": "🍎",
    "vegetable|carrot|broccoli|salad": "🥕",
    "bread|bake|flour|dough|bakery": "🍞",
    "cake|dessert|sweet|chocolate": "🍰",
    "coffee|tea|drink|beverage|latte": "☕",
    "soccer|football|goal|world cup": "⚽",
    "basketball|hoop|nba": "🏀",
    "tennis|racket|grand slam": "🎾",
    "swim|swimming|pool|olympic": "🏊",
    "run|running|sprint|marathon": "🏃",
    "phone|smartphone|mobile|cell": "📱",
    "camera|photography|photo|lens": "📷",
    "video|film|movie|cinema|hollywood": "🎬",
    "game|gaming|play|fun|video game": "🎮",
    "happy|joy|excited|delighted|glad": "😊",
    "sad|sorrow|depressed|grief|mourn": "😢",
    "love|affection|romance|heart|like": "😍",
    "angry|mad|furious|rage|upset": "😠",
    "scary|fear|terrified|horror|haunted": "😨",
    "surprise|shock|astonished|wow": "😲",
    "idea|thought|concept|brainstorm|innovation": "💡",
    "question|doubt|confused|wonder": "❓",
    "answer|solution|solve|correct": "✅",
    "time|clock|hour|minute|second": "⏰",
    "money|wealth|rich|poor|finance": "💰",
    "peace|calm|serene|quiet|zen": "🕊️",
    "war|conflict|fight|battle|combat": "⚔️",
    "friendship|friend|buddy|companion": "🤝",
    "family|home|house|shelter": "🏠",
    "school|education|learn|study|college": "🎓",
    "work|job|career|business|office": "💼",
    "travel|journey|trip|vacation|adventure": "✈️",
    "magic|wizard|spell|fantasy|sorcery": "🔮",
    "secret|mystery|hidden|classified": "🤫",
    "sunset|dusk|evening|twilight": "🌅",
    "rainbow|colorful|spectrum": "🌈",
    "christmas|santa|gift|present|holiday": "🎄",
    "birthday|party|celebration": "🎂",
    "science|scientist|research|lab": "🔬",
    "history|historian|past|timeline": "📜",
    "geography|map|globe|world": "🗺️",
    "language|words|dictionary|vocabulary": "🔤",
    "mathematics|math|algebra|calculus": "🔢",
}

def get_emoji_for_text(text):
    """Smart emoji selection based on text content"""
    text_lower = text.lower()
    
    # Check each category
    for keywords, emoji in EMOJI_CATEGORIES.items():
        for keyword in keywords.split("|"):
            if keyword in text_lower:
                return emoji
    
    # Default fallback
    return '✨'
