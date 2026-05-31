# utils.py - COMPLETELY FIXED (Emojis + Images + Wikipedia)
import streamlit as st
import re
import os
import requests
import json
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

# ==================== EMOJI PICKERS ====================

# Topic emojis: matched against a single keyword (the LLM-provided topic_keyword
# or the card title). Order doesn't matter much here since titles are short.
_TOPIC_EMOJI_MAP = {
    # --- PRIORITY: collision-prone long keys (checked first) ---
    'cinematography': '🎬', 'screenwriting': '🎬', 'method acting': '🎬',
    'theatre production': '🎬', 'film production': '🎬',
    'ethnomusicology': '🎤', 'audio engineering': '🎤',
    'venture capital': '💡', 'intellectual property': '💡',
    'carpentry': '🪚', 'joinery': '🪚',
    'pottery': '🏺', 'resin pouring': '🏺',
    'skateboarding': '🛹', 'rollerblading': '🛹',
    'rockhounding': '🪨', 'fossil hunting': '🪨', 'seashell collecting': '🪨',
    'smart home': '🏠', 'home automation': '🏠',
    'esports': '🏆', 'speedrunning': '🏆', 'competitive gaming': '🏆',
    'breakdancing': '🕺', 'street dance': '🕺', 'hip hop dance': '🕺',
    'speech pathology': '🗣️', 'speech therapy': '🗣️',

    # --- PRIORITY: multi-word phrases that must beat short-word substring matches ---
    'harry potter': '🧙', 'star wars': '🚀', 'lord of the rings': '🧙',
    'princess bride': '🌹',
    # Food dishes that contain animal/short-word substrings
    'tiramisu': '🍰', 'ramen': '🍜', 'baguette': '🥖', 'baguettes': '🥖',
    'guacamole': '🥑', 'shawarma': '🥙', 'sunday roast': '🍖',
    'tom yum': '🍲', 'croissant': '🥐', 'croissants': '🥐',
    'massaman': '🍛', 'lasagne': '🍝', 'lasagna': '🍝',
    'parmesan': '🧀', 'mozzarella': '🧀', 'prosciutto': '🥩',
    'bolognese': '🍝', 'carbonara': '🍝',
    'dim sum': '🥟', 'char siu': '🥩',
    'pad thai': '🍜', 'satay': '🍢',
    'bibimbap': '🍚', 'bulgogi': '🥩',
    'samosa': '🥟', 'pakora': '🍤', 'chapati': '🫓',
    'enchilada': '🌯', 'quesadilla': '🫓',
    'bouillabaisse': '🦞', 'ratatouille': '🍆',
    'clam chowder': '🦪', 'lobster roll': '🦞',
    'bangers and mash': '🌭', 'shepherd\'s pie': '🥧',
    'toad in the hole': '🌭', 'yorkshire pudding': '🫓',
    'fish and chips': '🐟',
    'empire strikes back': '🚀', 'return of the jedi': '🚀',
    'indiana jones': '🏺', 'raiders of the lost ark': '🏺',
    'lion king': '🦁', 'finding nemo': '🐠', 'toy story': '🧸',
    'game of thrones': '⚔️', 'breaking bad': '🧪',
    # Book titles (priority - long phrases must beat short substring matches)
    'pride and prejudice': '💍', 'sense and sensibility': '💍',
    'crime and punishment': '⚖️', 'war and peace': '⚔️',
    'anna karenina': '🚂', 'brothers karamazov': '⛪',
    'les miserables': '⚔️', 'les misérables': '⚔️',
    'count of monte cristo': '⚔️',
    'great gatsby': '🥂', 'moby dick': '🐋',
    'huckleberry finn': '🚣', 'tom sawyer': '🚣',
    'alice in wonderland': '🐰', 'alice adventures in wonderland': '🐰',
    'wuthering heights': '🌪️', 'jane eyre': '🌹',
    'great expectations': '🎩', 'tale of two cities': '⚔️',
    'picture of dorian gray': '🖼️',
    'importance of being earnest': '🎭',
    'hound of the baskervilles': '🐕',
    'sherlock holmes': '🔍',
    'treasure island': '🏴‍☠️',
    'around the world in eighty days': '🌍',
    'journey to the centre of the earth': '🌋',
    'war of the worlds': '👽',
    'time machine': '⏰',
    'phantom of the opera': '🎭',
    'arabian nights': '🌙', 'thousand and one nights': '🌙',
    'canterbury tales': '📜',
    'divine comedy': '🔥',
    'thus spake zarathustra': '💭',
    'beyond good and evil': '💭',
    'farewell to arms': '⚔️',
    'romeo and juliet': '🌹',
    'midsummer nights dream': '🧚',
    'little women': '🌸',
    'wonderful wizard of oz': '🌈',
    'scarlet letter': '📜',
    'heart of darkness': '🌿',
    'a dolls house': '🏠', "doll's house": '🏠',
    'federalist papers': '🏛️',
    'golden retriever': '🐕', 'border collie': '🐕', 'german shepherd': '🐕',
    'french bulldog': '🐕', 'jack russell': '🐕', 'cocker spaniel': '🐕',
    'springer spaniel': '🐕', 'yorkshire terrier': '🐕', 'bull terrier': '🐕',
    'shih tzu': '🐕', 'great dane': '🐕', 'saint bernard': '🐕',
    'miniature schnauzer': '🐕', 'belgian shepherd': '🐕',
    'british shorthair': '🐈', 'maine coon': '🐈', 'scottish fold': '🐈',
    'russian blue': '🐈', 'norwegian forest cat': '🐈', 'cornish rex': '🐈',
    'devon rex': '🐈',
    'polar bear': '🐻‍❄️', 'giant panda': '🐼', 'red panda': '🐼',
    'killer whale': '🐋', 'blue whale': '🐋', 'sperm whale': '🐋',
    'great white': '🦈', 'whale shark': '🦈',
    'sea lion': '🦭', 'snow leopard': '🐆', 'clouded leopard': '🐆',
    'komodo dragon': '🦎',
    'black hole': '🌑', 'solar system': '🪐', 'space station': '🛰️',
    'natural selection': '🧬', 'fossil fuel': '⛽', 'climate change': '🌡️',
    'global warming': '🌡️', 'mental health': '🧠',
    'nervous system': '🧠', 'immune system': '🛡️',
    'civil rights': '✊', 'world war': '⚔️',
    'artificial intelligence': '🤖', 'machine learning': '🤖',
    'social media': '📱', 'video game': '🎮',
    'fossil record': '🦴',

    # --- Dogs (breeds) ---
    'dog': '🐕', 'dogs': '🐕', 'puppy': '🐕', 'puppies': '🐕',
    'canine': '🐕', 'canines': '🐕', 'hound': '🐕', 'hounds': '🐕',
    # Terriers
    'terrier': '🐕', 'jack russell': '🐕', 'yorkshire terrier': '🐕',
    'bull terrier': '🐕', 'fox terrier': '🐕', 'border terrier': '🐕',
    # Herding & working
    'border collie': '🐕', 'collie': '🐕', 'sheepdog': '🐕',
    'german shepherd': '🐕', 'alsatian': '🐕',
    'rottweiler': '🐕', 'doberman': '🐕', 'dobermann': '🐕',
    'malinois': '🐕', 'belgian shepherd': '🐕',
    # Toy & small breeds
    'chihuahua': '🐕', 'pomeranian': '🐕', 'shih tzu': '🐕',
    'pug': '🐕', 'pugs': '🐕', 'maltese': '🐕', 'bichon': '🐕',
    'miniature schnauzer': '🐕', 'cavalier': '🐕',
    # Sighthounds
    'greyhound': '🐕', 'whippet': '🐕', 'saluki': '🐕', 'lurcher': '🐕',
    # Scent hounds
    'beagle': '🐕', 'beagles': '🐕', 'basset': '🐕', 'bloodhound': '🐕',
    'dachshund': '🐕', 'dachshunds': '🐕',
    # Large breeds
    'husky': '🐕', 'malamute': '🐕', 'samoyed': '🐕',
    'great dane': '🐕', 'saint bernard': '🐕', 'newfoundland': '🐕',
    'mastiff': '🐕', 'bernese': '🐕',
    # Fluffy / popular
    'poodle': '🐕', 'doodle': '🐕', 'cockapoo': '🐕', 'labradoodle': '🐕',
    'schnauzer': '🐕', 'dalmatian': '🐕', 'dalmatians': '🐕',
    'boxer': '🐕', 'bulldog': '🐕', 'french bulldog': '🐕',
    'chow chow': '🐕', 'akita': '🐕', 'shiba inu': '🐕',
    'corgi': '🐕', 'corgis': '🐕', 'pembroke': '🐕', 'cardigan': '🐕',
    'weimaraner': '🐕', 'vizsla': '🐕', 'pointer': '🐕',
    'setter': '🐕', 'irish setter': '🐕',

    # --- Cats (breeds expanded) ---
    'cat': '🐈', 'cats': '🐈', 'kitten': '🐈', 'kittens': '🐈',
    'feline': '🐈', 'felines': '🐈', 'tabby': '🐈', 'moggy': '🐈',
    'tomcat': '🐈', 'kitty': '🐈', 'kitties': '🐈',
    # Popular breeds
    'siamese': '🐈', 'persian': '🐈', 'bengal': '🐈', 'bengals': '🐈',
    'ragdoll': '🐈', 'ragdolls': '🐈', 'maine coon': '🐈',
    'british shorthair': '🐈', 'sphynx': '🐈', 'burmese': '🐈',
    'scottish fold': '🐈', 'abyssinian': '🐈', 'russian blue': '🐈',
    'norwegian forest cat': '🐈', 'birman': '🐈', 'tonkinese': '🐈',
    'devon rex': '🐈', 'cornish rex': '🐈', 'ocicat': '🐈',
    'savannah': '🐈', 'munchkin': '🐈', 'balinese': '🐈',

    # --- Big cats ---
    'lion': '🦁', 'lions': '🦁', 'lioness': '🦁', 'pride': '🦁',
    'tiger': '🐅', 'tigers': '🐅', 'tigress': '🐅',
    'leopard': '🐆', 'leopards': '🐆', 'cheetah': '🐆', 'cheetahs': '🐆',
    'jaguar': '🐆', 'puma': '🐆', 'cougar': '🐆', 'panther': '🐆',
    'snow leopard': '🐆', 'clouded leopard': '🐆',

    # --- Elephants ---
    'elephant': '🐘', 'elephants': '🐘', 'mammoth': '🐘', 'mammoths': '🐘',
    'tusk': '🐘', 'tusks': '🐘', 'trunk': '🐘',
    'mastodon': '🐘',

    # --- Giraffes ---
    'giraffe': '🦒', 'giraffes': '🦒', 'okapi': '🦒',

    # --- Marine mammals ---
    'whale': '🐋', 'whales': '🐋', 'cetacean': '🐋', 'cetaceans': '🐋',
    'humpback': '🐋', 'blue whale': '🐋', 'sperm whale': '🐋',
    'dolphin': '🐬', 'dolphins': '🐬', 'porpoise': '🐬', 'orca': '🐋',
    'killer whale': '🐋',
    'seal': '🦭', 'seals': '🦭', 'walrus': '🦭', 'sea lion': '🦭',
    'manatee': '🦭', 'dugong': '🦭',

    # --- Birds ---
    'bird': '🐦', 'birds': '🐦', 'avian': '🐦', 'avians': '🐦',
    'ornithology': '🐦', 'birdwatching': '🐦',
    'eagle': '🦅', 'eagles': '🦅', 'hawk': '🦅', 'hawks': '🦅',
    'falcon': '🦅', 'falcons': '🦅', 'osprey': '🦅', 'kite': '🦅',
    'buzzard': '🦅', 'condor': '🦅', 'vulture': '🦅',
    'owl': '🦉', 'owls': '🦉', 'barn owl': '🦉', 'tawny owl': '🦉',
    'parrot': '🦜', 'parrots': '🦜', 'macaw': '🦜', 'cockatoo': '🦜',
    'budgerigar': '🦜', 'budgie': '🦜', 'parakeet': '🦜', 'lovebird': '🦜',
    'penguin': '🐧', 'penguins': '🐧',
    'flamingo': '🦩', 'flamingos': '🦩',
    'duck': '🦆', 'ducks': '🦆', 'mallard': '🦆', 'goose': '🦆', 'geese': '🦆',
    'swan': '🦢', 'swans': '🦢',
    'robin': '🐦', 'sparrow': '🐦', 'finch': '🐦', 'pigeon': '🐦',
    'crow': '🐦', 'raven': '🐦', 'magpie': '🐦', 'jay': '🐦',
    'starling': '🐦', 'swallow': '🐦', 'swift': '🐦', 'wren': '🐦',
    'heron': '🐦', 'stork': '🐦', 'crane': '🐦', 'ibis': '🐦',
    'woodpecker': '🐦', 'kingfisher': '🐦',
    'peacock': '🦚', 'peacocks': '🦚', 'peahen': '🦚',
    'turkey': '🦃', 'turkeys': '🦃',
    'chicken': '🐔', 'chickens': '🐔', 'hens': '🐔',
    'rooster': '🐓', 'cockerel': '🐓', 'chick': '🐣', 'chicks': '🐣',
    'ostrich': '🦤', 'emu': '🦤', 'cassowary': '🦤',
    'kiwi': '🐦', 'puffin': '🐦', 'gannet': '🐦', 'albatross': '🐦',
    'parrot': '🦜', 'cockatiel': '🦜',

    # --- Insects ---
    'butterfly': '🦋', 'butterflies': '🦋', 'caterpillar': '🦋', 'caterpillars': '🦋',
    'moth': '🦋', 'moths': '🦋', 'chrysalis': '🦋', 'pupa': '🦋',
    'bee': '🐝', 'bees': '🐝', 'honeybee': '🐝', 'bumblebee': '🐝',
    'wasp': '🐝', 'wasps': '🐝', 'hornet': '🐝',
    'ant': '🐜', 'ants': '🐜', 'termite': '🐜', 'termites': '🐜',
    'beetle': '🐞', 'beetles': '🐞', 'ladybird': '🐞', 'ladybug': '🐞',
    'stag beetle': '🐞', 'dung beetle': '🐞',
    'dragonfly': '🦗', 'grasshopper': '🦗', 'cricket': '🦗', 'locust': '🦗',
    'mosquito': '🦟', 'mosquitoes': '🦟', 'fly': '🦟', 'flies': '🦟',
    'flea': '🦟', 'louse': '🦟', 'lice': '🦟', 'mite': '🦟', 'tick': '🦟',
    'spider': '🕷️', 'spiders': '🕷️', 'tarantula': '🕷️', 'arachnid': '🕷️',
    'scorpion': '🦂', 'scorpions': '🦂',
    'worm': '🪱', 'worms': '🪱', 'earthworm': '🪱', 'earthworms': '🪱',
    'slug': '🐌', 'snail': '🐌', 'snails': '🐌',
    'centipede': '🦠', 'millipede': '🦠',

    # --- Reptiles ---
    'snake': '🐍', 'snakes': '🐍', 'serpent': '🐍', 'viper': '🐍',
    'cobra': '🐍', 'python': '🐍', 'boa': '🐍', 'mamba': '🐍',
    'rattlesnake': '🐍', 'anaconda': '🐍', 'adder': '🐍',
    'lizard': '🦎', 'lizards': '🦎', 'gecko': '🦎', 'iguana': '🦎',
    'chameleon': '🦎', 'monitor': '🦎', 'komodo': '🦎',
    'crocodile': '🐊', 'crocodiles': '🐊', 'alligator': '🐊', 'alligators': '🐊',
    'turtle': '🐢', 'turtles': '🐢', 'tortoise': '🐢', 'tortoises': '🐢',
    'dinosaur': '🦕', 'dinosaurs': '🦕', 'trex': '🦖', 't-rex': '🦖',
    'pterodactyl': '🦕', 'prehistoric': '🦕',
    'fossil': '🦴', 'fossils': '🦴', 'palaeontology': '🦴', 'paleontology': '🦴',

    # --- Amphibians ---
    'frog': '🐸', 'frogs': '🐸', 'toad': '🐸', 'toads': '🐸',
    'salamander': '🐸', 'newt': '🐸', 'amphibian': '🐸', 'amphibians': '🐸',
    'axolotl': '🐸',

    # --- Fish & aquatic ---
    'fish': '🐟', 'fishes': '🐟', 'salmon': '🐟', 'trout': '🐟', 'cod': '🐟',
    'tuna': '🐟', 'herring': '🐟', 'bass': '🐟', 'carp': '🐟',
    'pike': '🐟', 'perch': '🐟', 'mackerel': '🐟', 'anchovy': '🐟',
    'goldfish': '🐠', 'clownfish': '🐠', 'tropical fish': '🐠',
    'angelfish': '🐠', 'guppy': '🐠',
    'shark': '🦈', 'sharks': '🦈', 'hammerhead': '🦈', 'great white': '🦈',
    'whale shark': '🦈',
    'octopus': '🐙', 'octopuses': '🐙', 'squid': '🐙', 'cuttlefish': '🐙',
    'crab': '🦀', 'crabs': '🦀', 'lobster': '🦞', 'lobsters': '🦞',
    'shrimp': '🦐', 'prawn': '🦐', 'prawns': '🦐', 'crayfish': '🦐',
    'jellyfish': '🪼', 'starfish': '⭐', 'seahorse': '🐠',
    'coral': '🪸', 'reef': '🪸', 'sea anemone': '🪸',
    'clam': '🐚', 'oyster': '🐚', 'mussel': '🐚', 'scallop': '🐚',

    # --- Small mammals & exotic pets ---
    'rabbit': '🐰', 'rabbits': '🐰', 'bunny': '🐰', 'bunnies': '🐰', 'hare': '🐰',
    'mouse': '🐭', 'mice': '🐭', 'rat': '🐭', 'rats': '🐭', 'rodent': '🐭',
    'hamster': '🐹', 'hamsters': '🐹', 'gerbil': '🐹', 'guinea pig': '🐹',
    'chinchilla': '🐹', 'chinchillas': '🐹', 'degu': '🐹',
    'squirrel': '🐿️', 'squirrels': '🐿️', 'chipmunk': '🐿️',
    'hedgehog': '🦔', 'hedgehogs': '🦔',
    'bat': '🦇', 'bats': '🦇',
    'otters': '🦦', 'beaver': '🦫', 'beavers': '🦫',
    'mole': '🐭', 'vole': '🐭', 'shrew': '🐭',
    'sugar glider': '🐿️', 'pygmy glider': '🐿️',

    # --- Farm animals (expanded) ---
    'horse': '🐴', 'horses': '🐴', 'pony': '🐴', 'ponies': '🐴',
    'foal': '🐴', 'mare': '🐴', 'stallion': '🐴', 'equine': '🐴',
    'thoroughbred': '🐴', 'clydesdale': '🐴', 'shire horse': '🐴',
    'shetland pony': '🐴', 'appaloosa': '🐴', 'quarter horse': '🐴',
    'cow': '🐄', 'cows': '🐄', 'cattle': '🐄', 'bull': '🐂', 'bulls': '🐂',
    'calf': '🐄', 'bovine': '🐄', 'heifer': '🐄', 'steer': '🐄',
    'pig': '🐷', 'pigs': '🐷', 'piglet': '🐷', 'piglets': '🐷',
    'boar': '🐗', 'swine': '🐷', 'pork': '🐷', 'sow': '🐷',
    'sheep': '🐑', 'lamb': '🐑', 'lambs': '🐑', 'ewe': '🐑', 'ram': '🐑',
    'merino': '🐑', 'leicester': '🐑',
    'goat': '🐐', 'goats': '🐐', 'kid': '🐐', 'nanny goat': '🐐',
    'donkey': '🫏', 'donkeys': '🫏', 'mule': '🫏',
    'llama': '🦙', 'llamas': '🦙', 'alpaca': '🦙', 'alpacas': '🦙',
    'camel': '🐪', 'camels': '🐪', 'dromedary': '🐪', 'bactrian': '🐪',
    'chicken': '🐔', 'chickens': '🐔', 'hens': '🐔',
    'rooster': '🐓', 'cockerel': '🐓', 'chick': '🐣',
    'duck': '🦆', 'ducks': '🦆', 'goose': '🦆', 'geese': '🦆',
    'turkey': '🦃', 'turkeys': '🦃',
    'rabbit': '🐰',
    'pig farming': '🐷', 'poultry': '🐔', 'livestock': '🐄',

    # --- Primates ---
    'monkey': '🐒', 'monkeys': '🐒', 'ape': '🦍', 'apes': '🦍',
    'gorilla': '🦍', 'gorillas': '🦍', 'chimpanzee': '🐒', 'chimp': '🐒',
    'orangutan': '🦧', 'baboon': '🐒', 'lemur': '🐒', 'primate': '🐒',
    'gibbon': '🐒', 'bonobo': '🐒', 'macaque': '🐒',

    # --- Bears ---
    'bear': '🐻', 'bears': '🐻', 'grizzly': '🐻', 'polar bear': '🐻‍❄️',
    'black bear': '🐻', 'brown bear': '🐻', 'sun bear': '🐻',
    'panda': '🐼', 'pandas': '🐼', 'giant panda': '🐼', 'red panda': '🐼',

    # --- Marsupials ---
    'kangaroo': '🦘', 'kangaroos': '🦘', 'wallaby': '🦘', 'wallabies': '🦘',
    'koala': '🐨', 'koalas': '🐨', 'wombat': '🐨', 'marsupial': '🦘',
    'possum': '🦘', 'opossum': '🦘', 'quokka': '🦘', 'tasmanian devil': '🦘',

    # --- Other mammals ---
    'fox': '🦊', 'foxes': '🦊', 'red fox': '🦊', 'arctic fox': '🦊',
    'wolf': '🐺', 'wolves': '🐺', 'grey wolf': '🐺', 'timber wolf': '🐺',
    'deer': '🦌', 'stag': '🦌', 'doe': '🦌', 'reindeer': '🦌',
    'moose': '🦌', 'elk': '🦌', 'fallow deer': '🦌', 'roe deer': '🦌',
    'zebra': '🦓', 'zebras': '🦓',
    'hippo': '🦛', 'hippopotamus': '🦛', 'hippos': '🦛',
    'rhino': '🦏', 'rhinoceros': '🦏', 'rhinos': '🦏',
    'giraffe': '🦒',
    'hyena': '🐺', 'jackal': '🐺', 'coyote': '🐺', 'dingo': '🐺',
    'raccoon': '🦝', 'raccoons': '🦝', 'skunk': '🦨', 'skunks': '🦨',
    'weasel': '🦦', 'ferret': '🦦', 'stoat': '🦦', 'mink': '🦦',
    'mongoose': '🦦', 'meerkat': '🦦', 'meerkats': '🦦',
    'aardvark': '🐾', 'anteater': '🐾', 'armadillo': '🐾',
    'sloth': '🦥', 'sloths': '🦥',
    'tapir': '🐾', 'okapi': '🦒', 'bison': '🐂', 'buffalo': '🐂',
    'wild boar': '🐗', 'warthog': '🐗',
    'narwhal': '🦄', 'unicorn': '🦄',

    # --- Space & astronomy ---
    'moon': '🌙', 'lunar': '🌙', 'moonlight': '🌙',
    'sun': '☀️', 'solar': '☀️', 'sunshine': '☀️', 'sunlight': '☀️',
    'star wars': '🚀', 'jedi': '⚔️', 'lightsaber': '⚔️',
    'star': '⭐', 'stars': '⭐', 'galaxy': '🌌', 'galaxies': '🌌',
    'universe': '🌌', 'cosmos': '🌌', 'cosmic': '🌌',
    'planet': '🪐', 'planets': '🪐', 'orbit': '🪐',
    'mars': '🪐', 'jupiter': '🪐', 'saturn': '🪐', 'venus': '🪐',
    'mercury': '🪐', 'neptune': '🪐', 'uranus': '🪐', 'pluto': '🪐',
    'asteroid': '☄️', 'comet': '☄️', 'meteor': '☄️', 'meteorite': '☄️',
    'rocket': '🚀', 'spacecraft': '🚀', 'astronaut': '🚀', 'nasa': '🚀',
    'spacex': '🚀', 'space shuttle': '🚀', 'apollo': '🚀',
    'telescope': '🔭', 'observatory': '🔭', 'astronomy': '🔭',
    'black hole': '🌑', 'nebula': '🌌', 'supernova': '💥',
    'satellite': '🛰️', 'space station': '🛰️', 'iss': '🛰️',

    # --- Science & biology ---
    'atom': '⚛️', 'atoms': '⚛️', 'atomic': '⚛️', 'nuclear': '⚛️',
    'molecule': '🧪', 'molecules': '🧪', 'chemistry': '🧪', 'chemical': '🧪',
    'dna': '🧬', 'gene': '🧬', 'genes': '🧬', 'genetic': '🧬', 'genetics': '🧬',
    'chromosome': '🧬', 'chromosomes': '🧬', 'genome': '🧬',
    'cell': '🔬', 'cells': '🔬', 'biology': '🔬', 'biological': '🔬',
    'microscope': '🔬', 'microbe': '🦠', 'microbes': '🦠',
    'virus': '🦠', 'viruses': '🦠', 'bacteria': '🦠', 'bacterium': '🦠',
    'natural selection': '🧬', 'adaptation': '🧬',
    'photosynthesis': '🌿', 'ecosystem': '🌍', 'ecology': '🌍',
    'climate': '🌡️', 'weather': '🌤️', 'atmosphere': '🌤️',

    # --- Human body ---
    'brain': '🧠', 'brains': '🧠', 'neuron': '🧠', 'neurons': '🧠',
    'nervous system': '🧠', 'nerve': '🧠', 'nerves': '🧠',
    'heart': '❤️', 'cardiac': '❤️', 'cardiovascular': '❤️',
    'blood': '🩸', 'vein': '🩸', 'veins': '🩸', 'artery': '🩸', 'arteries': '🩸',
    'bone': '🦴', 'bones': '🦴', 'skeleton': '🦴', 'skeletal': '🦴',
    'fossil': '🦴', 'fossils': '🦴',
    'muscle': '💪', 'muscles': '💪', 'muscular': '💪',
    'lung': '🫁', 'lungs': '🫁', 'respiratory': '🫁', 'breathing': '🫁',
    'stomach': '🫃', 'digestion': '🫃', 'digestive': '🫃', 'gut': '🫃',
    'kidney': '🫘', 'liver': '🫘', 'organ': '🫘', 'organs': '🫘',
    'skin': '🧴', 'immune': '🛡️', 'immunity': '🛡️',
    'hormone': '🧪', 'hormones': '🧪', 'endocrine': '🧪',

    # --- Health & medicine ---
    'medicine': '💊', 'medical': '💊', 'drug': '💊', 'drugs': '💊',
    'vaccine': '💉', 'vaccination': '💉', 'antibiotic': '💊',
    'hospital': '🏥', 'doctor': '🩺', 'nurse': '🩺', 'surgery': '🩺',
    'disease': '🦠', 'illness': '🤒', 'infection': '🦠', 'pandemic': '🦠',
    'cancer': '🩺', 'diabetes': '🩺', 'allergy': '🤧', 'allergies': '🤧',
    'mental health': '🧠', 'anxiety': '😟', 'depression': '😟',
    'autism': '🧩', 'adhd': '🧠', 'dyslexia': '📖',

    # --- Plants ---
    'tree': '🌳', 'trees': '🌳', 'forest': '🌳', 'woodland': '🌳',
    'oak': '🌳', 'pine': '🌲', 'evergreen': '🌲', 'conifer': '🌲',
    'birch': '🌳', 'willow': '🌳', 'maple': '🌳', 'ash': '🌳', 'elm': '🌳',
    'flower': '🌸', 'flowers': '🌸', 'blossom': '🌸', 'bloom': '🌸',
    'rose': '🌹', 'roses': '🌹', 'tulip': '🌷', 'tulips': '🌷',
    'sunflower': '🌻', 'sunflowers': '🌻', 'daisy': '🌸', 'daisies': '🌸',
    'orchid': '🌺', 'orchids': '🌺', 'lily': '🌸', 'lilies': '🌸',
    'lavender': '💜', 'poppy': '🌸', 'poppies': '🌸',
    'leaf': '🌿', 'leaves': '🌿', 'plant': '🌱', 'plants': '🌱',
    'seed': '🌱', 'seeds': '🌱', 'root': '🌱', 'roots': '🌱',
    'grass': '🌿', 'weed': '🌿', 'fern': '🌿', 'moss': '🌿',
    'mushroom': '🍄', 'mushrooms': '🍄', 'fungus': '🍄', 'fungi': '🍄',
    'cactus': '🌵', 'cacti': '🌵', 'succulent': '🌵',
    'seaweed': '🌿', 'algae': '🌿',
    'fruit': '🍎', 'vegetable': '🥦', 'crop': '🌾', 'crops': '🌾',
    'wheat': '🌾', 'rice': '🌾', 'corn': '🌽', 'maize': '🌽',
    'bamboo': '🎋', 'ivy': '🌿', 'vine': '🍇', 'grape': '🍇',

    # --- Geography & landscape ---
    'mountain': '⛰️', 'mountains': '⛰️', 'peak': '⛰️', 'summit': '⛰️', 'alps': '⛰️',
    'volcano': '🌋', 'volcanoes': '🌋', 'eruption': '🌋', 'lava': '🌋',
    'ocean': '🌊', 'oceans': '🌊', 'sea': '🌊', 'seas': '🌊',
    'river': '🏞️', 'rivers': '🏞️', 'lake': '🏞️', 'lakes': '🏞️',
    'waterfall': '🏞️', 'stream': '🏞️', 'pond': '🏞️',
    'desert': '🏜️', 'deserts': '🏜️', 'sahara': '🏜️', 'dune': '🏜️',
    'jungle': '🌴', 'rainforest': '🌴', 'tropical': '🌴',
    'arctic': '🧊', 'antarctica': '🧊', 'tundra': '🧊', 'glacier': '🧊',
    'cave': '🦇', 'cavern': '🦇', 'underground': '🦇',
    'island': '🏝️', 'islands': '🏝️', 'coast': '🏖️', 'beach': '🏖️',
    'valley': '🏞️', 'canyon': '🏜️', 'cliff': '⛰️',
    'earthquake': '🌍', 'tsunami': '🌊', 'flood': '🌊',
    'continent': '🌍', 'continents': '🌍', 'africa': '🌍', 'europe': '🌍',
    'asia': '🌏', 'america': '🌎', 'australia': '🌏',
    'ireland': '🍀', 'britain': '🌍', 'england': '🌍', 'scotland': '🌍',
    'wales': '🌍', 'france': '🗼', 'germany': '🌍', 'italy': '🍕',
    'spain': '🌍', 'japan': '⛩️', 'china': '🌏', 'india': '🌏',

    # --- Weather & climate ---
    'rain': '🌧️', 'rainfall': '🌧️', 'drizzle': '🌧️',
    'snow': '❄️', 'snowfall': '❄️', 'blizzard': '❄️', 'frost': '❄️',
    'lightning': '⚡', 'thunder': '⛈️', 'storm': '⛈️', 'tornado': '🌪️',
    'hurricane': '🌀', 'cyclone': '🌀', 'typhoon': '🌀',
    'wind': '💨', 'breeze': '💨', 'gale': '💨',
    'fog': '🌫️', 'mist': '🌫️', 'hail': '🌨️',
    'drought': '☀️', 'heatwave': '🌡️', 'temperature': '🌡️',
    'rainbow': '🌈', 'cloud': '☁️', 'clouds': '☁️',
    'season': '🍂', 'seasons': '🍂', 'autumn': '🍂', 'fall': '🍂',
    'spring': '🌸', 'summer': '☀️', 'winter': '❄️',

    # --- History & society ---
    'history': '📜', 'historical': '📜', 'ancient': '🏛️', 'medieval': '⚔️',
    'war': '⚔️', 'wars': '⚔️', 'battle': '⚔️', 'battles': '⚔️', 'conflict': '⚔️',
    'revolution': '⚔️', 'revolutions': '⚔️', 'empire': '👑',
    'kingdom': '👑', 'kingdoms': '👑', 'monarchy': '👑', 'royal': '👑',
    'king of': '👑', 'queen of': '👑', 'prince': '👑', 'princess': '👑',
    'castle': '🏰', 'palace': '🏰', 'pyramid': '🔺', 'ruins': '🏛️',
    'democracy': '🗳️', 'government': '🏛️', 'politics': '🗳️', 'election': '🗳️',
    'law': '⚖️', 'laws': '⚖️', 'justice': '⚖️', 'rights': '⚖️',
    'religion': '⛪', 'faith': '⛪', 'church': '⛪', 'temple': '🛕',
    'trade': '💰', 'economy': '💰', 'market': '💰', 'money': '💰',
    'slavery': '⛓️', 'colonialism': '🗺️', 'migration': '🧭',
    'civilisation': '🏛️', 'civilization': '🏛️', 'culture': '🎭',
    'roman': '🏛️', 'greek': '🏛️', 'egyptian': '🔺', 'viking': '⚔️',
    'aztec': '🔺', 'inca': '🔺', 'mayan': '🔺', 'mongol': '⚔️',
    'ottoman': '🌙', 'byzantine': '🏛️', 'persian': '🏛️',
    'tudor': '👑', 'victorian': '👑', 'georgian': '👑', 'edwardian': '👑',
    'world war one': '⚔️', 'world war two': '⚔️', 'cold war': '⚔️',
    'holocaust': '📜', 'civil rights': '✊', 'suffragette': '✊',

    # --- Technology ---
    'computer': '💻', 'computers': '💻', 'software': '💻', 'programming': '💻',
    'code': '💻', 'coding': '💻', 'algorithm': '💻', 'data': '📊',
    'internet': '🌐', 'web': '🌐', 'network': '🌐', 'online': '🌐',
    'social media': '📱', 'instagram': '📱', 'tiktok': '📱', 'youtube': '📺',
    'robot': '🤖', 'robots': '🤖', 'artificial intelligence': '🤖', 'chatgpt': '🤖',
    'machine learning': '🤖', 'automation': '🤖', 'chatgpt': '🤖',
    'phone': '📱', 'smartphone': '📱', 'mobile': '📱', 'iphone': '📱',
    'electricity': '⚡', 'electric': '⚡', 'circuit': '⚡', 'battery': '🔋',
    'engine': '⚙️', 'machine': '⚙️', 'invention': '💡', 'technology': '⚙️',
    'printing': '🖨️', 'print': '🖨️', 'newspaper': '📰',
    'camera': '📷', 'photography': '📷', 'film': '🎬',
    'television': '📺', 'radio': '📻', 'streaming': '📺',
    'nuclear': '☢️', 'radiation': '☢️',
    'video game': '🎮', 'gaming': '🎮', 'console': '🎮', 'playstation': '🎮',
    'xbox': '🎮', 'nintendo': '🎮', 'minecraft': '🎮',

    # --- Arts & culture ---
    'music': '🎵', 'musical': '🎵', 'song': '🎵', 'songs': '🎵', 'melody': '🎵',
    'guitar': '🎸', 'piano': '🎹', 'violin': '🎻', 'drum': '🥁', 'drums': '🥁',
    'trumpet': '🎺', 'flute': '🎵', 'saxophone': '🎷', 'harp': '🎵',
    'singing': '🎤', 'singer': '🎤', 'concert': '🎤', 'orchestra': '🎻',
    'pop music': '🎵', 'rock music': '🎸', 'jazz': '🎷', 'classical music': '🎻',
    'hip hop': '🎤', 'rap': '🎤', 'folk music': '🎵', 'opera': '🎤',
    'art': '🎨', 'arts': '🎨', 'painting': '🎨', 'drawing': '🎨', 'artist': '🎨',
    'sculpture': '🗿', 'dance': '💃', 'dancing': '💃', 'ballet': '🩰',
    'theatre': '🎭', 'theater': '🎭', 'drama': '🎭',
    'poetry': '📝', 'poem': '📝', 'poet': '📝', 'literature': '📖',
    'book': '📖', 'books': '📖', 'novel': '📖', 'story': '📖', 'author': '📖',
    'language': '🔤', 'languages': '🔤', 'grammar': '🔤', 'writing': '✍️',
    'architecture': '🏛️', 'design': '✏️',
    'fashion': '👗', 'clothing': '👗', 'textile': '🧵',
    'cinema': '🎬', 'movie': '🎬',

    # --- Film & TV (general) ---
    'film': '🎬', 'films': '🎬', 'movie': '🎬', 'movies': '🎬',
    'television': '📺', 'tv show': '📺', 'series': '📺', 'episode': '📺',
    'animation': '🎬', 'cartoon': '🎬', 'anime': '🎬',
    'documentary': '🎬', 'screenplay': '🎬', 'director': '🎬',
    'actor': '🎭', 'actress': '🎭', 'cast': '🎭', 'character': '🎭',
    'superhero': '🦸', 'superheroes': '🦸', 'villain': '🦹',
    'marvel': '🦸', 'avengers': '🦸', 'spider-man': '🕷️', 'batman': '🦇',
    'disney': '✨', 'pixar': '🎬', 'dreamworks': '🎬',
    'netflix': '📺', 'streaming': '📺',
    'jedi': '⚔️', 'lightsaber': '⚔️',
    'tolkien': '🧙',

    # --- IMDB Top 100 films ---
    # Top 10
    'shawshank redemption': '🔒',
    'godfather': '🤌',
    'dark knight': '🦇',
    'godfather part ii': '🤌', 'godfather part 2': '🤌',
    '12 angry men': '⚖️', 'twelve angry men': '⚖️',
    "schindler's list": '📜',
    'schindlers list': '📜',
    'lord of the rings': '🧙', 'fellowship of the ring': '🧙',
    'return of the king': '🧙', 'two towers': '🧙',
    'pulp fiction': '🎲',
    'hobbit': '🧙',

    # Classics & drama
    'casablanca': '🎩',
    'citizen kane': '🎬',
    'gone with the wind': '💨',
    'vertigo': '🌀',
    'psycho': '🔪',
    'rear window': '🪟',
    'sunset boulevard': '🎥',
    'some like it hot': '🎷',
    'singin in the rain': '🌧️',
    'all about eve': '🎭',
    'chinatown': '🕵️',
    'the apartment': '🏢',
    'double indemnity': '🕵️',

    # War & history films
    'schindlers list': '📜',
    'saving private ryan': '⚔️',
    'full metal jacket': '🪖',
    'apocalypse now': '🌿',
    'platoon': '🪖',
    'bridge on the river kwai': '🌉',
    'das boot': '⚓',
    'lawrence of arabia': '🏜️',
    'dr strangelove': '☢️',
    'paths of glory': '🪖',

    # Sci-fi
    '2001 a space odyssey': '🚀', '2001: a space odyssey': '🚀',
    'blade runner': '🤖',
    'metropolis': '🤖',
    'aliens': '👽', 'alien': '👽',
    'terminator': '🤖',
    'matrix': '💊',
    'interstellar': '🚀',
    'inception': '💭',
    'arrival': '👽',
    'gravity': '🚀',
    'ex machina': '🤖',

    # Crime & thriller
    'goodfellas': '🔫',
    'the departed': '🔫',
    'heat': '🔫',
    'silence of the lambs': '🐑',
    'se7en': '🔪', 'seven': '🔪',
    'fargo': '❄️',
    'no country for old men': '🤠',
    'reservoir dogs': '🔫',
    'memento': '🧠',
    'taxi driver': '🚕',
    'city of god': '🌃',
    'oldboy': '🔒',
    'the usual suspects': '🕵️',

    # Adventure & action
    'raiders of the lost ark': '🏺', 'indiana jones': '🏺',
    'star wars': '🚀',
    'empire strikes back': '🚀',
    'return of the jedi': '🚀',
    'jurassic park': '🦕',
    'back to the future': '⏰',
    'die hard': '🔥',
    'mad max': '🏎️',
    'gladiator': '⚔️',
    'braveheart': '⚔️',

    # Fantasy & magic
    'harry potter': '🧙', 'hogwarts': '🧙', 'wizarding': '🧙', 'potter': '🧙',
    'wizard of oz': '🌈',
    'princess bride': '🌹',
    'pan labyrinth': '🌀',
    'spirited away': '👻',
    'my neighbour totoro': '🌳', 'my neighbor totoro': '🌳',
    'princess mononoke': '🌳',
    'grave of the fireflies': '🌟',
    'studio ghibli': '🌳',

    # Animation
    'toy story': '🧸',
    'finding nemo': '🐠',
    'frozen': '❄️',
    'up': '🎈',
    'wall-e': '🤖', 'wall e': '🤖',
    'inside out': '🧠',
    'coco': '💀',
    'the incredibles': '🦸',
    'shrek': '🌿',
    'lion king': '🦁',
    'aladdin': '🧞',
    'beauty and the beast': '🌹',

    # Drama
    'forrest gump': '🏃',
    'titanic': '🚢',
    'american beauty': '🌹',
    'fight club': '🥊',
    'good will hunting': '📚',
    'a beautiful mind': '🧠',
    'rain man': '🧩',
    'one flew over the cuckoos nest': '🏥', "one flew over the cuckoo's nest": '🏥',
    'the green mile': '🔒',
    'requiem for a dream': '💊',
    'american history x': '⚔️',
    'eternal sunshine': '🌞',
    'lost in translation': '✈️',
    'the truman show': '📺',
    'dead poets society': '📖',
    'whiplash': '🥁',
    'la la land': '🎵',
    'birdman': '🐦',
    'parasite': '🪲',
    'everything everywhere': '🌀',
    'oppenheimer': '☢️',
    'barbie': '💗',
    'dune': '🏜️',

    # Horror
    'the shining': '👻',
    'get out': '😱',
    'hereditary': '👻',
    'midsommar': '🌸',
    'it the movie': '🤡', 'pennywise': '🤡', 'stephen king it': '🤡',
    'halloween': '🎃',
    'exorcist': '👹',
    'jaws': '🦈',
    'nightmare on elm street': '😴',

    # Comedy
    'some like it hot': '🎷',
    'monty python': '🐍',
    'life of brian': '✝️',
    'groundhog day': '🌤️',
    'big lebowski': '🎳',
    'home alone': '🏠',
    'ferris bueller': '😎',
    'breakfast club': '🎒',
    'office space': '💼',

    # TV shows
    'game of thrones': '⚔️',
    'breaking bad': '🧪',
    'the wire': '🔫',
    'sopranos': '🤌',
    'stranger things': '👾',
    'the office': '💼',
    'friends': '☕',
    'peaky blinders': '🎩',
    'black mirror': '📱',
    'chernobyl': '☢️',
    'band of brothers': '🪖',

    # --- Classic literature & books (Project Gutenberg top 100 + curriculum) ---
    # Jane Austen
    'pride and prejudice': '💍', 'sense and sensibility': '💍',
    'emma': '💌', 'persuasion': '💌', 'northanger abbey': '🏰',
    'mansfield park': '🌹', 'jane austen': '📖',

    # Shakespeare
    'romeo and juliet': '🌹', 'hamlet': '💀', 'macbeth': '🗡️',
    'othello': '🖤', 'king lear': '👑', 'a midsummer nights dream': '🧚',
    'the merchant of venice': '⚖️', 'twelfth night': '🎭',
    'much ado about nothing': '💬', 'as you like it': '🌳',
    'the tempest': '⛈️', 'julius caesar': '🏛️',
    'william shakespeare': '🎭', 'shakespeare': '🎭',

    # Dickens
    'great expectations': '🎩', 'oliver twist': '🎩',
    'a tale of two cities': '⚔️', 'david copperfield': '🎩',
    'a christmas carol': '🎄', 'bleak house': '⚖️',
    'the mystery of edwin drood': '🕵️', 'charles dickens': '🎩',

    # Gothic & horror literature
    'frankenstein': '⚡', 'dracula': '🧛',
    'the strange case of dr jekyll and mr hyde': '🧪',
    'dr jekyll and mr hyde': '🧪', 'jekyll and hyde': '🧪',
    'the picture of dorian gray': '🖼️',
    'wuthering heights': '🌪️',
    'the turn of the screw': '👻',
    'the monk': '⛪',
    'the mysteries of udolpho': '🏰',

    # Mystery & detective
    'the adventures of sherlock holmes': '🔍',
    'sherlock holmes': '🔍', 'sherlock': '🔍',
    'the hound of the baskervilles': '🐕',
    'a study in scarlet': '🔍',
    'the secret of chimneys': '🕵️',
    'the woman in white': '🕵️',
    'arsene lupin': '🎩', 'gentleman burglar': '🎩',
    'agatha christie': '🔍', 'arthur conan doyle': '🔍',
    'poirot': '🔍', 'miss marple': '🔍',

    # Adventure & travel
    'treasure island': '🏴‍☠️', 'robinson crusoe': '🏝️',
    'gulliver travels': '⛵', "gulliver's travels": '⛵',
    'around the world in eighty days': '🌍',
    'a journey to the centre of the earth': '🌋',
    'twenty thousand leagues under the sea': '🌊',
    'the adventures of tom sawyer': '🚣',
    'adventures of huckleberry finn': '🚣',
    'life on the mississippi': '🚣',
    'jules verne': '🚀', 'mark twain': '🚣',

    # Russian literature
    'crime and punishment': '⚖️',
    'the brothers karamazov': '⛪',
    'war and peace': '⚔️',
    'anna karenina': '🚂',
    'the idiot': '🕊️',
    'fyodor dostoyevsky': '⚖️', 'dostoyevsky': '⚖️',
    'leo tolstoy': '📜', 'tolstoy': '📜',

    # French literature
    'les miserables': '⚔️', 'les misérables': '⚔️',
    'the count of monte cristo': '⚔️',
    'twenty years after': '⚔️',
    'le fantome de lopera': '🎭', 'phantom of the opera': '🎭',
    'victor hugo': '📜', 'alexandre dumas': '⚔️',

    # American classics
    'the great gatsby': '🥂',
    'moby dick': '🐋',
    'the scarlet letter': '📜',
    'little women': '🌸',
    'the wonderful wizard of oz': '🌈',
    'the adventures of huckleberry finn': '🚣',
    'a farewell to arms': '⚔️',
    'the old man and the sea': '🐟',
    'of mice and men': '🐭',
    'to kill a mockingbird': '⚖️',
    'f scott fitzgerald': '🥂', 'fitzgerald': '🥂',
    'ernest hemingway': '✍️', 'hemingway': '✍️',
    'edgar allan poe': '🐦', 'poe': '🐦',

    # Children's classics
    "alice's adventures in wonderland": '🐰',
    'alice in wonderland': '🐰',
    'peter pan': '🧚',
    "grimms' fairy tales": '🧚', 'grimm': '🧚',
    'the jungle book': '🐯',
    'robinson crusoe': '🏝️',
    'lewis carroll': '🐰',
    'j m barrie': '🧚',
    'l frank baum': '🌈',

    # Philosophy & non-fiction
    'meditations': '💭',
    'leviathan': '🦕',
    'thus spake zarathustra': '💭',
    'beyond good and evil': '💭',
    'the prince': '👑',
    'the republic': '🏛️',
    'the odyssey': '⚓', 'odyssey': '⚓',
    'the iliad': '⚔️', 'iliad': '⚔️',
    'beowulf': '⚔️',
    'marcus aurelius': '🏛️',
    'machiavelli': '👑',
    'nietzsche': '💭',
    'plato': '🏛️',
    'aristotle': '🏛️',
    'thomas hobbes': '⚖️',
    'jean jacques rousseau': '💭',
    'homer': '⚓',
    'dante': '🔥', 'dante alighieri': '🔥',
    'divine comedy': '🔥', 'inferno': '🔥',

    # Gothic romance & Victorian
    'jane eyre': '🌹',
    'middlemarch': '📜',
    'north and south': '🏭',
    'tess of the durbervilles': '🌹',
    'charlotte bronte': '🌹', 'brontë': '🌹',
    'emily bronte': '🌪️',
    'george eliot': '📖',
    'thomas hardy': '🌹',
    'oscar wilde': '🌹',
    'the importance of being earnest': '🎭',
    'de profundis': '📜',

    # Sci-fi & speculative fiction (classic)
    'the war of the worlds': '👽',
    'the time machine': '⏰',
    'the invisible man': '👁️',
    'h g wells': '🚀', 'hg wells': '🚀',
    'edgar rice burroughs': '🌴',
    'thuvia maid of mars': '🪐',

    # Horror & weird fiction
    'the king in yellow': '👑',
    'h p lovecraft': '🐙', 'lovecraft': '🐙',
    'robert w chambers': '👑',
    'mary shelley': '⚡',

    # Biography & memoir
    'autobiography of benjamin franklin': '⚡',
    'narrative of the life of frederick douglass': '✊',
    'frederick douglass': '✊',
    'benjamin franklin': '⚡',

    # World literature
    'don quixote': '⚔️', 'cervantes': '⚔️',
    'the arabian nights': '🌙', 'thousand and one nights': '🌙',
    'the canterbury tales': '📜', 'chaucer': '📜',
    'the sorrows of young werther': '💔',
    'goethe': '💭',
    'metamorphosis': '🦋', 'kafka': '🦋',
    'sigmund freud': '🧠', 'freud': '🧠',
    'a dolls house': '🏠', "a doll's house": '🏠', 'ibsen': '🎭',
    'the federalist papers': '🏛️',
    'aesop': '🦁', "aesop's fables": '🦁',
    'rudyard kipling': '🐯', 'kipling': '🐯',
    'jack london': '🐺',
    'joseph conrad': '⚓',
    'heart of darkness': '🌿',
    'robert louis stevenson': '🏴‍☠️',

    # General book/literature terms
    'classic literature': '📖', 'classics': '📖',
    'novel': '📖', 'fiction': '📖', 'non-fiction': '📰',
    'poetry': '📝', 'poem': '📝', 'sonnet': '📝',
    'biography': '📜', 'autobiography': '📜', 'memoir': '📜',
    'short story': '📖', 'anthology': '📖',
    'gothic': '🏰', 'gothic fiction': '🏰',
    'romance novel': '🌹', 'satire': '😏',
    'dystopia': '⚠️', 'utopia': '🌍',
    'philosophy': '💭', 'philosophical': '💭',

    # --- Music artists & genres ---
    'beatles': '🎸', 'taylor swift': '🎤', 'beyonce': '🎤',
    'ed sheeran': '🎸', 'adele': '🎤', 'coldplay': '🎵',
    'pop': '🎵', 'rock': '🎸', 'metal': '🎸', 'punk': '🎸',
    'country': '🎸', 'blues': '🎷', 'soul': '🎤', 'rnb': '🎤',
    'reggae': '🎵', 'classical': '🎻', 'electronic': '🎵', 'dance': '💃',

    # --- Sports (expanded) ---
    'football': '⚽', 'soccer': '⚽', 'premier league': '⚽',
    'rugby': '🏉', 'rugby union': '🏉', 'rugby league': '🏉',
    'cricket': '🏏', 'baseball': '⚾', 'softball': '⚾',
    'basketball': '🏀', 'netball': '🏀', 'nba': '🏀',
    'tennis': '🎾', 'wimbledon': '🎾', 'badminton': '🏸',
    'swimming': '🏊', 'diving': '🤿', 'water polo': '🏊',
    'athletics': '🏃', 'running': '🏃', 'marathon': '🏃',
    'cycling': '🚴', 'tour de france': '🚴',
    'golf': '⛳', 'gymnastics': '🤸', 'boxing': '🥊',
    'martial arts': '🥋', 'karate': '🥋', 'judo': '🥋', 'taekwondo': '🥋',
    'wrestling': '🤼', 'mma': '🥊',
    'skiing': '⛷️', 'snowboarding': '🏂', 'ice skating': '⛸️',
    'ice hockey': '🏒', 'field hockey': '🏑',
    'rowing': '🚣', 'sailing': '⛵', 'surfing': '🏄',
    'olympics': '🥇', 'sport': '🏅', 'sports': '🏅', 'exercise': '🏋️',
    'yoga': '🧘', 'fitness': '🏋️', 'weightlifting': '🏋️',
    'formula one': '🏎️', 'f1': '🏎️', 'motorsport': '🏎️',
    'horse racing': '🐴', 'dressage': '🐴',
    'archery': '🏹', 'fencing': '🤺',
    'volleyball': '🏐', 'handball': '🤾',
    'table tennis': '🏓', 'snooker': '🎱', 'billiards': '🎱',
    'darts': '🎯',

    # --- Food & nutrition ---
    'food': '🍽️', 'nutrition': '🥗', 'diet': '🥗', 'eating': '🍽️',
    'fruit': '🍎', 'vegetable': '🥦', 'vegetables': '🥦',
    'meat': '🥩', 'fish': '🐟', 'dairy': '🧀', 'egg': '🥚', 'eggs': '🥚',
    'bread': '🍞', 'grain': '🌾', 'cereal': '🌾',
    'sugar': '🍬', 'fat': '🧈', 'protein': '🥩', 'vitamin': '💊',
    'cooking': '🍳', 'baking': '🥖', 'recipe': '📋',
    'restaurant': '🍴', 'chef': '👨‍🍳', 'kitchen': '🍳',
    'vegan': '🥗', 'vegetarian': '🥗', 'halal': '🌙', 'kosher': '✡️',
    'street food': '🥙', 'fast food': '🍔', 'takeaway': '🥡',
    'spicy': '🌶️', 'sweet': '🍬', 'savoury': '🧂', 'salty': '🧂',

    # Italian
    'pizza': '🍕', 'pasta': '🍝', 'spaghetti': '🍝', 'lasagne': '🍝',
    'risotto': '🍚', 'gelato': '🍦', 'tiramisu': '🍰',
    'carbonara': '🍝', 'bolognese': '🍝', 'pesto': '🌿',
    'bruschetta': '🍞', 'focaccia': '🍞',

    # Japanese
    'sushi': '🍣', 'sashimi': '🍣', 'ramen': '🍜', 'udon': '🍜',
    'tempura': '🍤', 'teriyaki': '🍱', 'miso': '🍲', 'tofu': '🫘',
    'onigiri': '🍙', 'gyoza': '🥟', 'edamame': '🫘',
    'katsu': '🍱', 'yakitori': '🍢',

    # Chinese
    'dim sum': '🥟', 'dumplings': '🥟', 'spring rolls': '🥢',
    'fried rice': '🍚', 'noodles': '🍜', 'peking duck': '🦆',
    'char siu': '🥩', 'hot pot': '🍲', 'wonton': '🥟',
    'sweet and sour': '🍊', 'chow mein': '🍜',

    # Indian
    'curry': '🍛', 'naan': '🫓', 'roti': '🫓', 'chapati': '🫓',
    'biryani': '🍚', 'samosa': '🥟', 'dal': '🍲', 'lentil': '🫘',
    'tikka masala': '🍛', 'vindaloo': '🌶️', 'korma': '🍛',
    'paneer': '🧀', 'mango lassi': '🥛', 'chutney': '🫙',
    'tandoori': '🔥', 'pakora': '🍤',

    # Mexican
    'taco': '🌮', 'tacos': '🌮', 'burrito': '🌯', 'burritos': '🌯',
    'enchilada': '🌯', 'quesadilla': '🫓', 'guacamole': '🥑',
    'salsa': '🍅', 'nachos': '🧀', 'fajita': '🌮',
    'tortilla': '🫓', 'tamale': '🌽', 'churros': '🍩',

    # American
    'burger': '🍔', 'hamburger': '🍔', 'cheeseburger': '🍔',
    'hot dog': '🌭', 'bbq': '🍖', 'barbecue': '🍖',
    'mac and cheese': '🧀', 'pancakes': '🥞', 'waffles': '🧇',
    'fried chicken': '🍗', 'wings': '🍗', 'ribs': '🍖',
    'clam chowder': '🦪', 'lobster roll': '🦞',
    'cornbread': '🍞', 'biscuits and gravy': '🍳',
    'apple pie': '🥧', 'cheesecake': '🍰',

    # British & Irish
    'fish and chips': '🐟', 'full english': '🍳', 'fry up': '🍳',
    'sunday roast': '🍖', 'roast dinner': '🍖',
    'shepherd\'s pie': '🥧', 'cottage pie': '🥧',
    'bangers and mash': '🌭', 'beans on toast': '🫘',
    'scones': '🫓', 'crumpets': '🫓', 'pasty': '🥧',
    'haggis': '🥩', 'black pudding': '🍳',
    'yorkshire pudding': '🫓', 'toad in the hole': '🌭',

    # French
    'croissant': '🥐', 'baguette': '🥖', 'crepe': '🫓',
    'quiche': '🥧', 'souffle': '🍮', 'ratatouille': '🍆',
    'bouillabaisse': '🦞', 'coq au vin': '🍗',
    'french onion soup': '🧅', 'crème brûlée': '🍮',
    'macarons': '🍪', 'éclair': '🍩',

    # Spanish
    'paella': '🍚', 'tapas': '🍽️', 'gazpacho': '🍅',
    'churros': '🍩', 'tortilla española': '🥚',
    'jamón': '🥩', 'chorizo': '🌶️', 'patatas bravas': '🥔',

    # Middle Eastern
    'hummus': '🫘', 'falafel': '🫓', 'shawarma': '🥙',
    'kebab': '🥙', 'pita': '🫓', 'flatbread': '🫓',
    'tabbouleh': '🌿', 'baklava': '🍯', 'mezze': '🍽️',
    'tahini': '🫙',

    # Thai
    'pad thai': '🍜', 'green curry': '🍛', 'tom yum': '🍲',
    'massaman': '🍛', 'sticky rice': '🍚', 'som tam': '🥗',
    'satay': '🍢',

    # Korean
    'kimchi': '🥬', 'bibimbap': '🍚', 'bulgogi': '🥩',
    'japchae': '🍜', 'tteok': '🍡', 'kimbap': '🍣',
    'doenjang': '🫙', 'korean bbq': '🍖',

    # Desserts & drinks
    'chocolate': '🍫', 'cake': '🎂', 'ice cream': '🍦',
    'doughnut': '🍩', 'cookie': '🍪', 'brownie': '🍫',
    'pudding': '🍮', 'custard': '🍮', 'trifle': '🍮',
    'coffee': '☕', 'espresso': '☕', 'latte': '☕', 'cappuccino': '☕',
    'tea': '🫖', 'green tea': '🍵', 'chai': '🍵',
    'smoothie': '🥤', 'juice': '🥤', 'milkshake': '🥛',
    'wine': '🍷', 'beer': '🍺', 'cocktail': '🍹',
    'lemonade': '🍋', 'hot chocolate': '🍫',

    # --- Environment & sustainability ---
    'environment': '🌍', 'environmental': '🌍', 'sustainability': '♻️',
    'recycling': '♻️', 'recycle': '♻️', 'pollution': '🏭', 'waste': '🗑️',
    'deforestation': '🌳', 'conservation': '🌿', 'biodiversity': '🦋',
    'renewable': '♻️', 'solar energy': '☀️', 'wind energy': '💨',
    'fossil fuel': '⛽', 'oil': '⛽', 'gas': '⛽', 'coal': '⛽',
    'global warming': '🌡️', 'climate change': '🌡️', 'greenhouse': '🌡️',

    # --- Transport ---
    'car': '🚗', 'cars': '🚗', 'vehicle': '🚗', 'vehicles': '🚗',
    'electric car': '🚗', 'tesla': '🚗',
    'train': '🚂', 'trains': '🚂', 'railway': '🚂', 'railroad': '🚂',
    'plane': '✈️', 'aircraft': '✈️', 'aviation': '✈️', 'airport': '✈️',
    'ship': '🚢', 'ships': '🚢', 'boat': '⛵', 'boats': '⛵',
    'bus': '🚌', 'buses': '🚌', 'transport': '🚌', 'road': '🛣️',
    'bicycle': '🚲', 'bike': '🚲', 'motorcycle': '🏍️',
    'helicopter': '🚁', 'drone': '🚁',
    'submarine': '🤿', 'hovercraft': '🚢',
    'space travel': '🚀', 'exploration': '🔭',

    # --- Mathematics ---
    'number': '🔢', 'numbers': '🔢', 'counting': '🔢', 'arithmetic': '🔢',
    'addition': '➕', 'subtraction': '➖', 'multiplication': '✖️', 'division': '➗',
    'fraction': '🔢', 'percentage': '💯', 'geometry': '📐', 'algebra': '🔡',
    'statistics': '📊', 'probability': '🎲', 'calculus': '📈',
    'shape': '🔷', 'shapes': '🔷', 'circle': '⭕', 'triangle': '🔺', 'square': '🔲',

    # --- Physics ---
    'gravity': '⬇️', 'force': '💥', 'motion': '🏃', 'momentum': '💥',
    'energy': '⚡', 'heat': '🔥', 'light': '💡', 'sound': '🔊',
    'wave': '〰️', 'frequency': '〰️', 'magnetism': '🧲', 'magnet': '🧲',
    'optics': '🔭', 'lens': '🔭', 'reflection': '🪞', 'refraction': '🌈',
    'thermodynamics': '🌡️', 'pressure': '💨', 'density': '⚖️',

    # --- Education & learning ---
    'school': '🎓', 'education': '🎓', 'learning': '🎓', 'study': '📚',
    'university': '🎓', 'college': '🎓', 'teacher': '👩‍🏫', 'student': '🎓',
    'maths': '🔢', 'mathematics': '🔢',
    'physics': '⚛️', 'chemistry': '🧪', 'biology': '🔬',
    'geography': '🗺️', 'philosophy': '💭',
    'psychology': '🧠', 'sociology': '👥', 'economics': '💰',
    'literacy': '📖', 'numeracy': '🔢',

    # --- Fantasy & mythology ---
    'dragon': '🐉', 'dragons': '🐉',
    'magic': '🔮', 'wizard': '🧙', 'witch': '🧙', 'spell': '✨',
    'unicorn': '🦄', 'fairy': '🧚', 'fairies': '🧚', 'elf': '🧝', 'elves': '🧝',
    'vampire': '🧛', 'werewolf': '🐺', 'ghost': '👻', 'zombie': '🧟',
    'mythology': '⚡', 'myth': '⚡', 'legend': '📜', 'folklore': '📜',
    'greek mythology': '⚡', 'norse mythology': '⚔️', 'roman mythology': '🏛️',
    'zeus': '⚡', 'thor': '⚡', 'odin': '⚔️', 'athena': '🏛️',
    'hercules': '💪', 'achilles': '⚔️', 'odysseus': '⚓',
    'medusa': '🐍', 'minotaur': '🐂', 'phoenix': '🔥',

    # --- People & society ---
    'family': '👨‍👩‍👧', 'families': '👨‍👩‍👧', 'parenting': '👨‍👩‍👧',
    'friendship': '🤝', 'community': '👥', 'society': '👥',
    'childhood': '👶', 'teenager': '🧑', 'adult': '🧑', 'elderly': '👴',
    'gender': '🧑', 'identity': '🧑', 'diversity': '🌍',
    'leadership': '👑', 'teamwork': '🤝', 'communication': '💬',
    'emotions': '😊', 'feelings': '😊', 'empathy': '❤️',

    # --- Hobbies & leisure ---
    'hobby': '🎨', 'hobbies': '🎨', 'craft': '🧵', 'crafts': '🧵',
    'knitting': '🧶', 'sewing': '🧵', 'gardening': '🌱', 'garden': '🌱',
    'cooking': '🍳', 'baking': '🥖',
    'photography': '📷', 'drawing': '✏️', 'painting': '🎨',
    'reading': '📖', 'writing': '✍️',
    'travelling': '✈️', 'travel': '✈️', 'hiking': '🥾', 'camping': '⛺',
    'fishing': '🎣', 'hunting': '🏹', 'swimming': '🏊',
    'gaming': '🎮', 'chess': '♟️', 'puzzles': '🧩',
    'collecting': '🏆', 'stamp collecting': '📮',
    # --- Philosophy & humanities ---
    'ethics': '🤔', 'ethical': '🤔', 'aesthetics': '🤔', 'epistemology': '🤔',
    'metaphysics': '🤔', 'political philosophy': '🤔', 'moral philosophy': '🤔',
    'logic': '🤔', 'logical': '🤔',
    'hermeneutics': '📜', 'archival science': '📜', 'historiography': '📜',
    'biblical studies': '✝️', 'hermeneutic': '✝️',
    'phonetics': '🗣️', 'phonology': '🗣️', 'morphology': '🗣️',
    'syntax': '🗣️', 'semantics': '🗣️', 'pragmatics': '🗣️',
    'historical linguistics': '🗣️',
    'literary criticism': '📖', 'comparative literature': '📖',
    'field archaeology': '🏺', 'bioarchaeology': '🏺', 'zooarchaeology': '🏺',
    'geoarchaeology': '🏺', 'cultural heritage': '🏺',

    # --- Natural sciences (gaps) ---
    'geology': '🪨', 'geotechnical': '🪨', 'mineralogy': '🪨',
    'hydrology': '💧', 'hydrological': '💧',
    'climatology': '🌡️', 'climate science': '🌡️',
    'cosmology': '🌌', 'astrophysics': '🌌', 'astrobiology': '🌌',
    'molecular biology': '🧬', 'evolutionary biology': '🧬',
    'polymer science': '🧪', 'analytical chemistry': '🧪',

    # --- Maths & computing (gaps) ---
    'topology': '🔢', 'number theory': '🔢', 'discrete mathematics': '🔢',
    'linear algebra': '🔢', 'pure mathematics': '🔢',
    'cybersecurity': '🔒', 'encryption': '🔒', 'network security': '🔒',
    'information security': '🔒',
    'database systems': '🗄️', 'data structures': '🗄️',
    'signal processing': '📡', 'telecommunications': '📡', 'microelectronics': '📡',
    'power systems': '⚡', 'electrical engineering': '⚡', 'circuit design': '⚡',

    # --- Engineering (gaps) ---
    'fluid mechanics': '💨', 'aerodynamics': '💨', 'hydrodynamics': '💨',
    'kinematics': '⚙️', 'mechanical engineering': '⚙️',
    'structural analysis': '🏗️', 'civil engineering': '🏗️', 'urban planning': '🏗️',
    'geotechnical engineering': '🏗️',
    'avionics': '✈️', 'propulsion': '✈️', 'orbital mechanics': '✈️',
    'aerospace engineering': '✈️', 'aerospace': '✈️',
    'materials science': '🧱',

    # --- Social sciences (gaps) ---
    'neuroscience': '🧠', 'cognitive psychology': '🧠', 'neurology': '🧠',
    'econometrics': '📊', 'biostatistics': '📊', 'demography': '📊',
    'international relations': '🌍', 'global health policy': '🌍',
    'development economics': '🌍',
    'public policy': '⚖️', 'penology': '⚖️', 'victimology': '⚖️',
    'torts': '⚖️', 'contract law': '⚖️', 'corporate law': '⚖️',
    'constitutional law': '⚖️',
    'forensic science': '🔬', 'forensic accounting': '🔬',
    'social theory': '👥', 'urban sociology': '👥', 'ethnography': '👥',

    # --- Arts & media (gaps) ---
    'printmaking': '🖨️', 'typography': '🖨️',
    'ui/ux design': '🖥️', 'ux design': '🖥️', '3d modeling': '🖥️',
    'animation': '🖥️', 'game design': '🖥️', 'digital art': '🖥️',
    'cinematography': '🎬', 'screenwriting': '🎬', 'method acting': '🎬',
    'theatre production': '🎬', 'film production': '🎬',
    'ethnomusicology': '🎤', 'audio engineering': '🎤', 'vocal performance': '🎤',
    'investigative reporting': '📰', 'broadcast journalism': '📰',
    'public relations': '📰', 'mass communication': '📰',

    # --- Business & law (gaps) ---
    'investment banking': '🏦', 'corporate finance': '🏦', 'auditing': '🏦',
    'human resources': '👔', 'operations management': '👔',
    'supply chain logistics': '👔', 'strategic management': '👔',
    'consumer behaviour': '📣', 'digital marketing': '📣',
    'brand management': '📣', 'market research': '📣',
    'venture capital': '💡', 'intellectual property': '💡',
    'entrepreneurship': '💡', 'startup': '💡',

    # --- Health & medicine (gaps) ---
    'pathology': '🦠', 'epidemiology': '🦠', 'immunology': '🦠',
    'pharmacology': '💊', 'dietotherapy': '💊', 'metabolism': '💊',
    'sports nutrition': '💊',
    'speech pathology': '🗣️', 'speech therapy': '🗣️',
    'global health': '🏥', 'preventative medicine': '🏥', 'public health': '🏥',

    # --- Trades & applied skills (gaps) ---
    'plumbing': '🔧', 'hvac': '🔧', 'auto mechanics': '🔧',
    'aviation maintenance': '🔧', 'marine engineering': '🔧',
    'carpentry': '🪚', 'joinery': '🪚',
    'horticulture': '🌱', 'hydroponics': '🌱', 'permaculture': '🌱',
    'composting': '🌱',
    'animal husbandry': '🐄',
    'butchery': '🍖', 'molecular gastronomy': '🍖', 'pastry arts': '🍰',

    # --- Textile & craft hobbies (gaps) ---
    'crocheting': '🧶', 'embroidery': '🧶', 'quilting': '🧶',
    'weaving': '🧶', 'lacemaking': '🧶', 'spinning wool': '🧶',
    'woodturning': '🪵', 'whittling': '🪵', 'blacksmithing': '🪵',
    'glassblowing': '🪵', 'metal sculpting': '🪵',
    'origami': '📦', 'papier-mâché': '📦', 'scale model building': '📦',
    'scrapbooking': '📦', 'cardmaking': '📦',
    'pottery': '🏺', 'resin pouring': '🏺',
    'clock repair': '🕰️', 'antique restoration': '🕰️', 'bookbinding': '🕰️',
    'shoe cobbling': '🕰️',

    # --- Outdoor & adventure hobbies (gaps) ---
    'bouldering': '🧗', 'mountaineering': '🧗', 'caving': '🧗',
    'spelunking': '🧗',
    'kayaking': '🛶', 'canoeing': '🛶', 'paddleboarding': '🛶',
    'snorkeling': '🤿', 'scuba diving': '🤿',
    'skateboarding': '🛹', 'rollerblading': '🛹',
    'foraging': '🍄', 'mushroom hunting': '🍄', 'geocaching': '🍄',
    'bonsai training': '🌿', 'aquascaping': '🌿',
    'parkour': '🤸',

    # --- Food & home hobbies (gaps) ---
    'homebrewing': '🍺', 'beer brewing': '🍺', 'winemaking': '🍷',
    'cheese making': '🧀', 'fermenting': '🧀', 'pickling': '🧀',
    'coffee roasting': '☕',
    'smart home': '🏠', 'home automation': '🏠',

    # --- Games & puzzles (gaps) ---
    'backgammon': '🎲', 'dungeons and dragons': '🎲', 'warhammer': '🎲',
    'tabletop gaming': '🎲', 'board gaming': '🎲',
    'mahjong': '🀄', 'tarot': '🀄', 'tarot reading': '🀄',
    'sudoku': '🧩', 'jigsaw puzzles': '🧩', 'rubiks cube': '🧩',
    'logic grids': '🧩', 'crosswords': '🧩',
    'esports': '🏆', 'speedrunning': '🏆', 'competitive gaming': '🏆',

    # --- Martial arts (gaps) ---
    'brazilian jiu-jitsu': '🥋', 'muay thai': '🥋', 'krav maga': '🥋',
    'bjj': '🥋',

    # --- Fitness (gaps) ---
    'calisthenics': '💪', 'powerlifting': '💪',

    # --- Dance (gaps) ---
    'salsa': '💃', 'tango': '💃', 'ballroom dance': '💃',
    'swing dancing': '💃', 'latin dance': '💃',
    'ballet': '🩰', 'tap dance': '🩰',
    'breakdancing': '🕺', 'street dance': '🕺', 'hip hop dance': '🕺',

    # --- Collecting hobbies (gaps) ---
    'philately': '📮', 'stamp collecting': '📮', 'postcard collecting': '📮',
    'numismatics': '🪙', 'coin collecting': '🪙',
    'vinyl records': '💿', 'record collecting': '💿', 'comic books': '💿',
    'trading cards': '💿',
    'rockhounding': '🪨', 'fossil hunting': '🪨', 'seashell collecting': '🪨',
    'mineral collecting': '🪨',
    'mechanical watches': '⌚', 'vintage cameras': '⌚', 'watch collecting': '⌚',
    'sneakers': '👟', 'sneaker collecting': '👟',
    'action figures': '🎭', 'movie memorabilia': '🎭',

    # --- Performance & audio hobbies (gaps) ---
    'stand-up comedy': '🎤', 'improv': '🎤', 'karaoke': '🎤',
    'magic tricks': '🪄', 'puppetry': '🪄', 'juggling': '🪄',
    'fire spinning': '🪄', 'fire performance': '🪄',
    'djing': '🎧', 'podcasting': '🎧', 'field recording': '🎧',
    'blogging': '✍️', 'journaling': '✍️', 'fan fiction': '✍️',
    'poetry slams': '✍️',
}




# Fact emojis: ORDERED list of (keyword-list, emoji) tuples. The picker scans
# the FULL fact text and the first match wins, so put multi-word phrases and
# more specific concepts at the top.
_FACT_EMOJI_PATTERNS = [
    # --- Multi-word phrases (must come first to beat single-word matches) ---
    (["best friend", "best friends", "man's best friend"], "🤝"),
    (["body language", "body languages"], "🗣️"),
    (["sign language", "sign languages"], "🤟"),
    (["sense of smell"], "👃"),
    (["world war", "world wars"], "⚔️"),
    (["solar system"], "🪐"),
    (["climate change", "global warming", "greenhouse effect"], "🌡️"),
    (["food chain", "food web"], "🔗"),
    (["life cycle", "life cycles"], "🔄"),
    (["blood pressure"], "❤️"),
    (["natural selection", "survival of the fittest"], "🧬"),
    (["carbon dioxide", "carbon monoxide", "greenhouse gas"], "🌡️"),
    (["photosynthesis"], "🌿"),
    (["immune system"], "🛡️"),
    (["nervous system"], "🧠"),
    (["digestive system"], "🫃"),
    (["solar energy", "solar power"], "☀️"),
    (["wind energy", "wind power", "wind turbine"], "💨"),
    (["fossil fuel", "fossil fuels"], "⛽"),
    (["big bang"], "💥"),
    (["black hole", "black holes"], "🌑"),
    (["milky way"], "🌌"),
    (["ice age"], "🧊"),
    (["civil war", "civil wars"], "⚔️"),
    (["world record", "world records"], "🏆"),
    (["heart rate", "heart beat", "heartbeat"], "❤️"),
    (["heart", "hearts", "cardiac", "cardiovascular", "pulse",
       "blood vessel", "blood vessels", "artery", "arteries",
       "vein", "veins", "circulation", "circulatory"], "❤️"),
    (["blood type", "blood group"], "🩸"),
    (["endangered species", "endangered animal"], "⚠️"),
    (["food web"], "🔗"),
    (["water cycle"], "💧"),
    (["rock cycle"], "🪨"),
    (["carbon cycle"], "🔄"),
    (["nitrogen cycle"], "🔄"),
    (["tectonic plate", "tectonic plates", "plate tectonics"], "🌍"),
    (["periodic table"], "🧪"),
    (["double helix"], "🧬"),
    (["stem cell", "stem cells"], "🔬"),
    (["mental health"], "🧠"),
    (["blood vessel", "blood vessels"], "🩸"),
    (["spinal cord"], "🦴"),
    (["bone marrow"], "🦴"),
    (["lymph node", "lymph nodes", "lymphatic"], "🩺"),
    (["solar flare", "solar flares"], "☀️"),
    (["nuclear fusion", "nuclear fission"], "☢️"),
    (["electric current"], "⚡"),
    (["magnetic field"], "🧲"),
    (["gravitational pull", "gravitational force"], "⬇️"),
    (["sound wave", "sound waves"], "🔊"),
    (["light wave", "light waves"], "💡"),

    # --- Cause & effect (must beat single words like "loss", "produce") ---
    (["cause", "causes", "caused", "causing",
       "lead to", "leads to", "led to",
       "result in", "results in", "resulted in",
       "reason for", "reasons for", "because of",
       "therefore", "consequently", "hence", "thus",
       "due to", "owing to",
       "impact on", "outcome of",
       "trigger", "triggers", "triggered"], "⚖️"),

    # --- Contrast & comparison (must beat "gills", "fish" etc.) ---
    (["unlike", "whereas", "in contrast", "on the other hand",
       "compared to", "compared with",
       "differ from", "differs from", "difference between",
       "although", "though", "nevertheless",
       "rather than", "instead of", "alternatively",
       "versus", "as opposed to"], "🆚"),

    # --- Location & habitat (must beat animal names like "tiger") ---
    (["native to", "found in", "live in", "lives in",
       "located in", "endemic to",
       "habitat", "habitats", "natural habitat",
       "distributed across", "distribution",
       "inhabit", "inhabits", "inhabited",
       "geographic range", "where it lives"], "📍"),

    # --- Dates & historical anchors (must beat "great", "large" etc.) ---
    (["in 1066", "in 1215", "in 1492", "in 1600", "in 1700", "in 1800",
       "in 1900", "in 1939", "in 1945", "in 1969",
       "in 1776", "in 1865", "in 1918", "in 1963",
       "founded in", "established in", "invented in",
       "discovered in", "born in", "died in",
       "during the war", "during the revolution",
       "by the year", "as of the year",
       "in the year", "in the century",
       "in the 19th century", "in the 20th century",
       "in the 18th century", "in the 17th century",
       "bce", "bc", "ce", "ad"], "📅"),

    # --- Government & politics (must beat "laws" → ⚖️) ---
    (["parliament", "parliamentary",
       "democracy", "democratic",
       "prime minister", "head of state",
       "constitution", "constitutional",
       "legislation", "legislative",
       "election", "elections", "voting rights",
       "political party", "republic",
       "monarchy", "senate", "congress",
       "sovereignty", "citizenship", "civic",
       "government policy", "public policy"], "🏛️"),

    # --- Economics & trade (must beat "economic" → 💰) ---
    (["gdp", "gross domestic product",
       "inflation", "unemployment rate",
       "supply and demand", "free market",
       "imports and exports", "balance of trade",
       "recession", "economic growth",
       "stock market", "interest rate",
       "taxation", "fiscal policy",
       "monetary policy", "capitalism",
       "manufacturing output", "trade deficit"], "💹"),

    # --- Religion & spirituality (must beat "central" → ⭐, "soul" etc.) ---
    (["religion", "religious",
       "worship", "worshipped",
       "prayer", "praying",
       "sacred text", "holy book",
       "bible", "quran", "torah",
       "mosque", "synagogue", "cathedral",
       "pilgrimage", "ritual", "ceremony",
       "faith tradition", "spiritual belief",
       "divine", "afterlife", "salvation",
       "buddhism", "christianity", "islam",
       "hinduism", "judaism", "sikhism"], "🕌"),

    # --- Literature analysis (must beat "runs" → 🏃, "create" → 💼) ---
    (["theme of", "themes of",
       "symbolism", "symbolic of",
       "metaphor for", "extended metaphor",
       "imagery", "pathetic fallacy",
       "foreshadowing", "allegory",
       "narrative structure", "plot structure",
       "protagonist", "antagonist",
       "soliloquy", "monologue",
       "rhyme scheme", "iambic pentameter",
       "literary device", "literary technique",
       "written by", "authored by",
       "shakespeare", "dickens", "austen"], "🎭"),

    # --- Art & design (must beat "create" → 💼) ---
    (["impressionism", "impressionist",
       "renaissance art", "baroque",
       "colour palette", "art style",
       "brushstroke", "brushstrokes",
       "portrait painting", "landscape painting",
       "abstract art", "sculpture",
       "art movement", "art technique",
       "exhibition", "art gallery",
       "canvas", "oil paint",
       "watercolour", "watercolor",
       "mixed media", "graphic design"], "🎨"),

    # --- Music theory (must beat single word "note", "scale" etc.) ---
    (["tempo", "rhythm", "melody",
       "harmony", "harmonies",
       "time signature", "key signature",
       "major key", "minor key",
       "musical note", "music theory",
       "chord progression",
       "dynamics", "timbre",
       "concerto", "symphony", "sonata",
       "overture", "opera",
       "composer", "conductor",
       "orchestra", "ensemble",
       "beats per minute", "musical instrument"], "🎼"),

    # --- Computer science (must beat "data", "function", "variable") ---
    (["algorithm", "algorithms",
       "programming language",
       "source code", "binary code",
       "cpu", "processor",
       "operating system",
       "cybersecurity", "encryption",
       "machine learning",
       "artificial intelligence",
       "database", "data structure",
       "software development",
       "computer science",
       "coding language", "hardware"], "💻"),

    # --- Maths formulae (must beat "calculate" → 📏) ---
    (["formula", "formulae", "formulas",
       "theorem", "theorems",
       "equation", "equations",
       "square root", "cube root",
       "area of", "volume of",
       "perimeter of", "circumference of",
       "power of", "to the power",
       "mean of", "median of", "mode of",
       "prime number",
       "ratio", "proportion",
       "coordinate geometry",
       "simultaneous equations",
       "quadratic", "trigonometry",
       "pythagoras"], "🧮"),


    # --- Communication & senses ---
    (["communicate", "communication", "language", "speak", "speech", "talk", "talking",
       "conversation", "verbal", "dialogue", "discuss", "express", "expression",
       "message", "signal", "signals", "call", "calls", "vocalise", "vocalise",
       "vocalize", "vocalization", "shout", "whisper", "announce", "tell"], "💬"),
    (["bark", "barking", "howl", "howling", "growl", "growling", "meow", "meowing",
       "roar", "roaring", "chirp", "chirping", "squeak", "squeaking", "hiss", "hissing",
       "moo", "mooing", "bray", "neigh", "trumpets", "trumpet", "purr", "purring",
       "croak", "croaking", "screech", "screeching"], "🔊"),
    (["listen", "listening", "hearing", "hear", "heard", "ear", "ears", "auditory",
       "acoustic", "sound", "sounds", "noise", "noisy", "quiet", "silent", "silence"], "👂"),
    (["smell", "smelling", "smells", "scent", "scents", "odor", "odour", "odours",
       "nose", "nostrils", "sniff", "sniffing", "olfactory", "aroma", "fragrance",
       "stench", "pheromone", "pheromones"], "👃"),
    (["see", "seeing", "sight", "sights", "vision", "visual", "eye", "eyes",
       "watch", "watching", "look", "looking", "observe", "observing", "spot",
       "spotting", "detect", "detecting", "view", "gaze", "stare", "colour", "color",
       "blind", "blindness", "retina", "pupil", "iris", "lens"], "👀"),
    (["taste", "tasting", "tongue", "tongues", "flavour", "flavor", "flavours", "flavors",
       "sweet", "sour", "bitter", "salty", "savory", "savoury", "gustatory"], "👅"),
    (["touch", "touching", "feel", "feeling", "tactile", "texture", "rough", "smooth",
       "soft", "hard", "pressure", "vibration", "vibrations"], "✋"),
    (["read", "reading", "write", "writing", "written", "text", "letter", "letters",
       "word", "words", "sentence", "sentences", "literacy", "literate"], "📖"),

    # --- Relationships & social ---
    (["best friend", "best friends", "man's best friend"], "🤝"),
    (["friend", "friendship", "friendships", "companion", "companions", "companionship",
       "buddy", "buddies", "mate", "mates", "ally", "allies", "associate", "bond",
       "bonding", "loyal", "loyalty", "trust", "trusted"], "🤝"),
    (["family", "families", "parent", "parents", "mother", "mothers", "father", "fathers",
       "child", "children", "sibling", "siblings", "brother", "brothers", "sister",
       "sisters", "offspring", "kin", "relative", "relatives", "ancestor", "ancestors",
       "generation", "generations", "grandparent", "grandparents"], "👨‍👩‍👧"),
    (["love", "loving", "affection", "affectionate", "romance", "romantic", "bond",
       "attachment", "care", "caring", "devotion", "devoted"], "❤️"),
    (["enemy", "enemies", "fight", "fighting", "attack", "attacking", "war", "wars",
       "battle", "battles", "conflict", "conflicts", "aggression", "aggressive",
       "hostile", "hostility", "rival", "rivals", "rivalry", "compete", "competition",
       "predator", "predators", "prey", "threat", "threats"], "⚔️"),
    (["pack", "packs", "group", "groups", "herd", "herds", "flock", "flocks",
       "swarm", "swarms", "colony", "colonies", "team", "teams", "community",
       "communities", "society", "societies", "population", "populations",
       "tribe", "tribes", "band", "bands", "cluster", "clusters"], "👥"),
    (["leader", "leaders", "leadership", "dominant", "dominance", "alpha", "hierarchy",
       "rank", "status", "power", "authority", "control"], "👑"),
    (["partner", "partners", "mate", "mating", "breed", "breeding", "reproduce",
       "reproduction", "courtship", "court", "attract", "attraction"], "💑"),

    # --- Behaviour & actions ---
    (["mark", "marking", "marks", "territory", "territories", "territorial", "claim",
       "claiming", "scent mark", "boundary", "boundaries"], "🚩"),
    (["hunt", "hunting", "hunts", "hunter", "hunters", "predator", "predators",
       "prey", "stalk", "stalking", "ambush", "chase", "chasing", "capture",
       "capturing", "catch", "catching", "kill", "killing", "carnivore", "carnivores"], "🏹"),
    (["sleep", "sleeping", "sleeps", "slept", "rest", "resting", "rests", "nap",
       "napping", "dream", "dreaming", "hibernate", "hibernating", "hibernation",
       "dormant", "dormancy", "nocturnal", "diurnal"], "😴"),
    (["eat", "eating", "eats", "ate", "food", "foods", "meal", "meals", "diet",
       "diets", "feed", "feeding", "feeds", "digest", "digestion", "chew", "chewing",
       "swallow", "swallowing", "herbivore", "herbivores", "omnivore", "omnivores",
       "forage", "foraging", "graze", "grazing", "nutrient", "nutrients",
       "calorie", "calories", "nourish", "nourishment"], "🍽️"),
    (["drink", "drinking", "drinks", "drank", "thirst", "thirsty", "water",
       "hydrate", "hydration", "dehydrate", "dehydration"], "🥤"),
    (["migrate", "migration", "migrating", "migrates", "seasonal", "journey",
       "travel", "travels", "travelling", "move", "movement", "navigate",
       "navigation", "route", "routes", "path", "paths", "direction"], "🧭"),
    (["run", "running", "runs", "ran", "race", "racing", "sprint", "sprinting",
       "dash", "dashing", "jog", "jogging", "chase", "chasing", "flee", "fleeing",
       "escape", "escaping", "speed", "speedy", "fast", "quick", "rapid"], "🏃"),
    (["jump", "jumping", "jumps", "jumped", "leap", "leaping", "leaps", "leapt",
       "hop", "hopping", "hops", "hopped", "bounce", "bouncing", "spring"], "🦘"),
    (["swim", "swimming", "swims", "swam", "dive", "diving", "dives", "dived",
       "submerge", "submerging", "float", "floating", "aquatic", "underwater"], "🏊"),
    (["fly", "flying", "flies", "flew", "flight", "soar", "soaring", "glide",
       "gliding", "hover", "hovering", "migrate", "wing", "wings", "airborne"], "🕊️"),
    (["climb", "climbing", "climbs", "climbed", "scale", "scaling", "ascend",
       "ascending", "crawl", "crawling"], "🧗"),
    (["play", "playing", "plays", "played", "fun", "funny", "game", "games",
       "entertain", "entertainment", "recreation", "leisure", "enjoyment", "enjoy"], "🎮"),
    (["learn", "learning", "learns", "learned", "study", "studying", "school",
       "education", "educate", "educating", "teach", "teaching", "train", "training",
       "instruct", "instruction", "knowledge", "understand", "understanding",
       "memory", "remember", "memorise", "memorize", "skill", "skills"], "🎓"),
    (["work", "working", "works", "worked", "job", "jobs", "labour", "labor",
       "task", "tasks", "effort", "produce", "production", "create", "creating",
       "make", "making", "build", "building", "construct", "construction"], "💼"),
    (["protect", "protecting", "protection", "guard", "guarding", "defend",
       "defending", "defense", "defence", "shield", "shielding", "camouflage",
       "hide", "hiding", "escape", "warn", "warning", "alarm", "signal"], "🛡️"),
    (["grow", "growing", "grows", "grew", "growth", "develop", "development",
       "develops", "mature", "maturing", "maturity", "age", "ageing", "aging",
       "change", "changing", "transform", "transformation", "evolve", "evolving",
       "evolution", "adapt", "adapting", "adaptation"], "🌱"),
    (["born", "birth", "births", "hatch", "hatching", "hatches", "spawn",
       "spawning", "reproduce", "reproduction", "breed", "breeding", "offspring",
       "baby", "babies", "newborn", "infant", "young"], "🐣"),
    (["die", "dying", "death", "deaths", "dead", "extinct", "extinction",
       "kill", "killed", "perish", "perishing", "end", "ending", "loss", "lost"], "⚰️"),
    (["cure", "cures", "heal", "healing", "heals", "recover", "recovery",
       "treat", "treatment", "treatments", "therapy", "therapies", "rehabilitate"], "🩹"),
    (["discover", "discovers", "discovered", "discovery", "explore", "exploring",
       "exploration", "invent", "inventing", "invention", "create", "creating",
       "find", "finding", "found", "research", "researching", "investigate",
       "investigating", "investigation", "experiment", "experimenting"], "💡"),
    (["measure", "measuring", "measurement", "calculate", "calculating",
       "calculation", "count", "counting", "estimate", "estimating",
       "record", "recording", "observe", "observing", "observation"], "📏"),
    (["warn", "warning", "warnings", "alert", "alerts", "signal", "signals",
       "alarm", "alarms", "danger", "dangerous", "threat", "threats"], "⚠️"),
    (["store", "storing", "storage", "save", "saving", "reserve", "reserves",
       "collect", "collecting", "gather", "gathering", "hoard", "hoarding"], "📦"),
    (["clean", "cleaning", "cleans", "cleaned", "groom", "grooming",
       "hygiene", "wash", "washing", "sanitise", "sanitize"], "🧹"),

    # --- Body parts ---
    (["tail", "tails", "wag", "wagging", "wags", "wagged"], "〰️"),
    (["paw", "paws", "claw", "claws", "talon", "talons", "hoof", "hooves",
       "foot", "feet", "toes", "toe", "limb", "limbs", "leg", "legs"], "🐾"),
    (["fur", "furs", "coat", "fleece", "wool", "pelage", "pelt", "hide",
       "feather", "feathers", "scale", "scales", "shell", "shells", "skin"], "🐾"),
    (["hair", "hairs", "mane", "manes", "bristle", "bristles", "quill", "quills",
       "beard", "whisker", "whiskers"], "💇"),
    (["teeth", "tooth", "fang", "fangs", "bite", "biting", "bites", "jaw",
       "jaws", "tusk", "tusks", "molar", "canine tooth"], "🦷"),
    (["wing", "wings", "feather", "feathers", "beak", "beaks", "bill", "bills",
       "talon", "talons", "plume", "plumage"], "🪶"),
    (["horn", "horns", "antler", "antlers", "spine", "spines", "spike", "spikes"], "🦌"),
    (["eye", "eyes", "pupil", "iris", "retina", "cornea", "eyelid"], "👁️"),
    (["ear", "ears", "hearing", "eardrum"], "👂"),
    (["nose", "nostrils", "snout", "muzzle"], "👃"),
    (["fin", "fins", "gill", "gills", "flipper", "flippers"], "🐟"),
    (["pouch", "pouches", "marsupial"], "🦘"),
    (["venom", "venomous", "poison", "poisonous", "toxin", "toxic", "sting", "stinging"], "☠️"),

    # --- Numbers, size, scale ---
    (["million", "millions", "billion", "billions", "trillion", "trillions",
       "thousand", "thousands", "hundred", "hundreds", "many", "numerous",
       "countless", "vast", "majority", "minority", "percent", "percentage"], "🔢"),
    (["big", "bigger", "biggest", "large", "larger", "largest", "huge", "giant",
       "enormous", "massive", "immense", "colossal", "gigantic",
       "wide", "broad", "tall", "high", "deep", "long"], "📏"),
    (["small", "smaller", "smallest", "tiny", "little", "miniature", "microscopic",
       "minute", "compact", "short", "narrow", "thin", "lightweight"], "🔍"),
    (["fast", "faster", "fastest", "quick", "quicker", "quickest", "speed",
       "speedy", "rapid", "swift", "agile", "nimble", "brisk"], "⚡"),
    (["slow", "slower", "slowest", "slowly", "gradual", "gradually"], "🐢"),
    (["heavy", "heavier", "heaviest", "weight", "weigh", "weighs", "mass",
       "dense", "density", "solid", "hard"], "⚖️"),
    (["light", "lighter", "lightest", "lightweight", "hollow", "buoyant"], "🪶"),

    # --- Time & history ---
    (["old", "older", "oldest", "ancient", "history", "historical", "past",
       "ago", "millennium", "millennia", "prehistoric",
       "fossil", "fossils", "antique", "archaic", "traditional", "heritage"], "📜"),
    (["new", "newer", "newest", "modern", "recent", "recently", "today",
       "current", "contemporary", "latest", "now", "present", "future"], "✨"),
    (["year", "years", "decade", "decades",
       "day", "days", "month", "months", "week", "weeks",
       "hour", "hours", "minute", "minutes", "second", "seconds",
       "era", "eras", "period", "periods", "epoch", "epochs",
       "season", "seasons", "annual", "annually", "daily", "weekly", "monthly"], "📅"),
    (["first", "earliest", "original", "begin", "beginning", "start",
       "starting", "origin", "origins", "founding", "found", "pioneer",
       "evolution", "evolve", "evolving", "evolves", "evolved",
       "revolution", "revolutions"], "🥇"),
    (["final", "end", "ending", "finish", "finishing", "conclude",
       "conclusion", "complete", "completion", "ultimate"], "✅"),
    (["change", "changed", "changing", "shift", "shifted", "transform",
       "transformed", "revolutionary"], "🔄"),
    (["progress", "progressed", "progressing", "develop", "development",
       "develops", "developed", "advance", "advances", "advanced",
       "advancement", "improve", "improved", "improvement"], "📈"),

    # --- Space & motion ---
    (["orbit", "orbits", "orbiting", "orbited", "revolve", "revolves", "revolution",
       "rotate", "rotates", "rotation", "spin", "spinning", "spins", "spun",
       "circular", "elliptical", "axis", "axial"], "🔄"),
    (["walk", "walked", "walking", "walks", "step", "steps", "stepping",
       "stride", "strides", "pace", "pacing", "march", "marching", "wander",
       "wandering", "roam", "roaming", "stroll", "strolling"], "🚶"),
    (["reflect", "reflects", "reflected", "reflection", "reflections", "mirror",
       "mirrors", "bounce", "bounces", "bounced", "echo", "echoes", "echoed"], "🪞"),
    (["absorb", "absorbs", "absorbed", "absorption", "soak", "soaks", "soaked"], "💧"),
    (["explode", "explodes", "explosion", "explosions", "burst", "bursts",
       "erupt", "erupts", "eruption", "eruptions", "blast", "blasts"], "💥"),
    (["collapse", "collapses", "collapsed", "compress", "compresses", "compressed",
       "crush", "crushes", "crushed", "contract", "contracts", "contracted"], "⬇️"),
    (["expand", "expands", "expanded", "expansion", "stretch", "stretches",
       "stretched", "extend", "extends", "extended", "spread", "spreads"], "↔️"),

    # --- Habitat & environment ---
    (["forest", "forests", "wood", "woods", "woodland", "jungle", "jungles",
       "rainforest", "rainforests", "canopy", "understory", "undergrowth"], "🌳"),
    (["desert", "deserts", "sand", "sands", "sandy", "dune", "dunes",
       "arid", "dry", "barren", "sahara", "wasteland"], "🏜️"),
    (["arctic", "antarctic", "polar", "ice", "icy", "frozen", "freeze",
       "frost", "frosty", "glacier", "glaciers", "tundra", "freezing",
       "permafrost", "iceberg", "icebergs", "snowfield"], "🧊"),
    (["sea", "ocean", "oceans", "marine", "maritime", "coastal", "coast",
       "shore", "shores", "reef", "reefs", "tidal", "tide", "tides",
       "saltwater", "seawater", "deepsea", "deep sea", "abyss", "benthic"], "🌊"),
    (["mountain", "mountains", "mountainous", "hill", "hills", "highland",
       "highlands", "alpine", "altitude", "elevation", "peak", "peaks",
       "summit", "summits", "cliff", "cliffs", "rocky", "rock", "rocks"], "⛰️"),
    (["sky", "skies", "cloud", "clouds", "cloudy", "air", "aerial",
       "atmosphere", "atmospheric", "airborne", "aloft", "canopy", "above"], "☁️"),
    (["home", "homes", "house", "houses", "shelter", "shelters", "den",
       "dens", "nest", "nests", "burrow", "burrows", "hole", "holes",
       "lair", "cave", "caves", "lodge", "lodges", "dam", "dams"], "🏠"),
    (["city", "cities", "urban", "town", "towns", "suburb", "suburbs",
       "street", "streets", "building", "buildings", "infrastructure"], "🏙️"),
    (["farm", "farms", "farming", "rural", "countryside", "field", "fields",
       "meadow", "meadows", "pasture", "pastures", "crop", "crops", "agricultural"], "🚜"),
    (["soil", "soils", "earth", "ground", "dirt", "mud", "clay",
       "sediment", "silt", "mineral", "minerals", "nutrient", "nutrients"], "🌍"),
    (["wetland", "wetlands", "swamp", "swamps", "marsh", "marshes", "bog",
       "bogs", "estuary", "estuaries", "mangrove", "mangroves"], "🌿"),

    # --- Science & abstract ---
    (["energy", "energies", "power", "powerful", "electric", "electrical",
       "electricity", "fuel", "fuels", "charge", "charged", "voltage",
       "current", "kinetic", "potential"], "⚡"),
    (["water", "liquid", "liquids", "wet", "moisture", "humid", "humidity",
       "damp", "fluid", "fluids", "aqueous", "dissolve", "dissolves", "soluble"], "💧"),
    (["fire", "fires", "flame", "flames", "burn", "burning", "burns", "hot",
       "heat", "heated", "ignite", "ignition", "combustion", "blaze", "blazing",
       "inferno", "warm", "warming"], "🔥"),
    (["cold", "colder", "coldest", "freeze", "freezes", "freezing", "frost",
       "frosty", "frozen", "chill", "chilly", "icy", "cool", "cooling"], "❄️"),
    (["light", "bright", "brightness", "shine", "shining", "shines", "shone",
       "glow", "glowing", "glows", "illuminate", "illuminating", "luminous",
       "phosphorescent", "bioluminescent", "radiant", "radiation", "ray", "rays",
       "beam", "beams", "photon", "photons", "visible", "ultraviolet", "infrared"], "💡"),
    (["dark", "darker", "darkest", "darkness", "shadow", "shadows", "night",
       "nights", "nighttime", "dusk", "dim", "dimly", "obscure", "opaque"], "🌑"),
    (["health", "healthy", "medicine", "medicines", "medical", "doctor",
       "doctors", "nurse", "nurses", "hospital", "hospitals", "clinic",
       "clinics", "treat", "treatment", "treatments", "cure", "cures",
       "heal", "healing", "drug", "drugs", "vaccine", "vaccines", "surgery"], "🩺"),
    (["disease", "diseases", "illness", "illnesses", "sick", "sickness",
       "infection", "infections", "virus", "viruses", "bacteria", "bacterium",
       "pathogen", "pathogens", "epidemic", "pandemic", "symptom", "symptoms",
       "diagnose", "diagnosis", "contagious", "contagion", "spread", "spreading"], "🦠"),
    (["danger", "dangerous", "risk", "risks", "risky", "warning", "warnings",
       "hazard", "hazards", "hazardous", "threat", "threats", "threatening",
       "toxic", "toxicity", "poisonous", "poison", "deadly", "lethal",
       "harmful", "harmful", "vulnerable", "vulnerability", "endangered"], "⚠️"),
    (["safe", "safer", "safest", "safety", "secure", "security", "protect",
       "protected", "protection", "stable", "stability", "reliable", "reliability"], "🛡️"),
    (["money", "moneys", "cost", "costs", "price", "prices", "economy",
       "economies", "economic", "trade", "trades", "trading", "buy", "buying",
       "sell", "selling", "market", "markets", "wealth", "wealthy", "rich",
       "poor", "poverty", "finance", "financial", "income", "wage", "wages",
       "salary", "profit", "loss", "invest", "investment"], "💰"),
    (["important", "importance", "essential", "key", "main", "major", "critical",
       "crucial", "significant", "significance", "fundamental", "vital", "primary",
       "core", "central", "leading", "chief", "principal", "notable"], "⭐"),
    (["idea", "ideas", "thought", "thoughts", "concept", "concepts", "theory",
       "theories", "hypothesis", "hypotheses", "principle", "principles",
       "belief", "beliefs", "philosophy", "philosophical", "notion", "notions",
       "assumption", "assumptions", "model", "models", "framework"], "💡"),
    (["question", "questions", "ask", "asking", "asks", "asked", "wonder",
       "wondering", "wonders", "doubt", "doubts", "mystery", "mysteries",
       "puzzle", "puzzles", "unknown", "uncertain", "uncertainty", "curious",
       "curiosity", "investigate", "investigate", "probe", "query", "queries"], "❓"),
    (["answer", "answers", "solve", "solving", "solves", "solved", "solution",
       "solutions", "explain", "explanation", "explanations", "prove",
       "proof", "proofs", "evidence", "correct", "right", "accurate", "true",
       "truth", "fact", "facts", "confirm", "confirmed", "verify"], "✅"),
    (["connect", "connection", "connections", "link", "links", "linked",
       "relate", "relation", "relationship", "relationships", "associate",
       "association", "interact", "interaction", "interactions", "depend",
       "dependence", "interdependence", "symbiosis", "symbiotic"], "🔗"),
    (["recycle", "recycling", "reuse", "reusing", "sustainable",
       "sustainability", "conserve", "conservation", "preserve",
       "preservation", "environment", "environmental", "green",
       "renewable", "biodegradable", "compost", "composting"], "♻️"),
    (["pollute", "pollution", "pollutions", "contaminate", "contamination",
       "waste", "wastes", "emission", "emissions", "toxic", "dump", "dumping",
       "litter", "littering", "deforestation", "habitat loss"], "🏭"),
    (["attract", "attraction", "magnetic", "magnetism", "magnet", "magnets",
       "repel", "repulsion", "force", "forces", "field", "fields"], "🧲"),
    (["law", "laws", "rule", "rules", "principle", "principles", "regulation",
       "regulations", "gravity", "thermodynamics", "momentum", "conservation"], "⚖️"),
    (["chemical", "chemicals", "reaction", "reactions", "compound", "compounds",
       "element", "elements", "molecule", "molecules", "bond", "bonds",
       "acid", "acidic", "base", "alkaline", "neutral", "ph"], "🧪"),
    (["pressure", "pressures", "compress", "compression", "squeeze",
       "atmospheric", "barometric", "hydraulic"], "💨"),
    (["wave", "waves", "frequency", "frequencies", "amplitude", "wavelength",
       "vibrate", "vibration", "vibrations", "oscillate", "oscillation",
       "resonance", "resonate"], "〰️"),
    (["gravity", "gravitational", "weight", "fall", "falling", "falls",
       "fell", "drop", "dropping", "attract", "attraction"], "⬇️"),

    # --- Generic animals (catch-all, after all concept categories) ---
    (["dog", "puppy", "puppies", "canine", "canines", "hound", "hounds",
       "labrador", "retriever", "terrier", "spaniel", "poodle", "bulldog",
       "husky", "dachshund"], "🐕"),
    (["cat", "kitten", "kittens", "feline", "felines", "tabby", "moggy",
       "kitty", "tomcat"], "🐈"),
    (["lion", "lions", "lioness", "pride", "big cat", "big cats"], "🦁"),
    (["tiger", "tigers", "tigress"], "🐅"),
    (["elephant", "elephants", "mammoth", "mammoths"], "🐘"),
    (["whale", "whales", "cetacean", "cetaceans", "orca"], "🐋"),
    (["dolphin", "dolphins", "porpoise", "porpoises"], "🐬"),
    (["shark", "sharks"], "🦈"),
    (["bird", "birds", "avian", "avians", "sparrow", "robin", "finch",
       "crow", "raven", "pigeon", "dove"], "🐦"),
    (["eagle", "eagles", "hawk", "hawks", "falcon", "falcons", "osprey"], "🦅"),
    (["owl", "owls"], "🦉"),
    (["butterfly", "butterflies", "caterpillar", "caterpillars", "moth", "moths"], "🦋"),
    (["bee", "bees", "honeybee", "bumblebee", "wasp", "wasps", "hornet"], "🐝"),
    (["ant", "ants", "termite", "termites"], "🐜"),
    (["spider", "spiders", "arachnid", "arachnids"], "🕷️"),
    (["snake", "snakes", "serpent", "viper", "cobra", "python", "boa"], "🐍"),
    (["frog", "frogs", "toad", "toads", "amphibian", "amphibians"], "🐸"),
    (["fish", "fishes", "salmon", "trout", "tuna", "cod", "herring"], "🐟"),
    (["horse", "horses", "pony", "ponies", "foal", "mare", "stallion", "equine"], "🐴"),
    (["monkey", "monkeys", "ape", "apes", "chimpanzee", "chimp", "primate", "primates"], "🐒"),
    (["gorilla", "gorillas", "orangutan"], "🦍"),
    (["bear", "bears", "grizzly"], "🐻"),
    (["panda", "pandas"], "🐼"),
    (["penguin", "penguins"], "🐧"),
    (["rabbit", "rabbits", "bunny", "bunnies", "hare", "hares"], "🐰"),
    (["mouse", "mice", "rat", "rats", "rodent", "rodents", "hamster", "gerbil"], "🐭"),
    (["fox", "foxes"], "🦊"),
    (["wolf", "wolves", "wolfpack"], "🐺"),
    (["deer", "stag", "doe", "reindeer", "moose", "elk"], "🦌"),
    (["kangaroo", "kangaroos", "wallaby", "wallabies", "marsupial"], "🦘"),
    (["koala", "koalas"], "🐨"),
    (["crocodile", "crocodiles", "alligator", "alligators"], "🐊"),
    (["turtle", "turtles", "tortoise", "tortoises"], "🐢"),
    (["dinosaur", "dinosaurs", "prehistoric", "fossil", "fossils"], "🦕"),
    (["human", "humans", "people", "person", "man", "woman", "mankind",
       "humankind", "homo sapiens", "homo", "sapiens"], "🧑"),
    (["plant", "plants", "tree", "trees", "flower", "flowers", "flora"], "🌿"),
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


def _looks_like_emoji(s):
    """Best-effort check that a short string is an emoji (not text/ascii).
    Accepts single emoji plus modifiers/ZWJ sequences. No external library.
    """
    if not s or not isinstance(s, str):
        return False
    s = s.strip()
    if not s or len(s) > 8:
        return False
    # Reject anything containing ascii letters/digits (i.e. plain text)
    if any(c.isascii() and c.isalnum() for c in s):
        return False
    # Require at least one char in a pictographic/emoji range
    for c in s:
        o = ord(c)
        if (0x1F000 <= o <= 0x1FAFF) or (0x2600 <= o <= 0x27BF) \
           or (0x2190 <= o <= 0x21FF) or (0x2B00 <= o <= 0x2BFF) \
           or o in (0x2122, 0x2139) or (0x1F1E6 <= o <= 0x1F1FF) \
           or (0xFE00 <= o <= 0xFE0F) or (0x2700 <= o <= 0x27BF):
            return True
    return False

# ==================== TWEMOJI: CRISP, IDENTICAL EMOJIS EVERYWHERE ====================
# Converts emoji characters in a string into <img> tags pointing at the Twemoji
# SVG set (served via jsDelivr). This makes every emoji render identically and
# sharply on all devices, instead of using each device's own system font.
# The original emoji is kept in the img alt, so it still degrades gracefully.

_TWEMOJI_CDN = "https://cdn.jsdelivr.net/gh/jdecked/twemoji@latest/assets/svg"

# Matches single emoji, skin-tone modifiers, variation selectors, flags, keycaps
# and ZWJ sequences (e.g. family emoji) as one unit.
_EMOJI_RE = re.compile(
    "(?:"
    "[#*0-9]\uFE0F?\u20E3"
    "|[\U0001F1E6-\U0001F1FF]{2}"
    "|[\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U00002B00-\U00002BFF"
    "\U00002190-\U000021FF"
    "\U00002300-\U000023FF"
    "\u2122\u2139\u3030\u303D\u3297\u3299\u00A9\u00AE]"
    "[\U0001F3FB-\U0001F3FF]?"
    "\uFE0F?"
    "(?:\u200D"
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFF]"
    "[\U0001F3FB-\U0001F3FF]?\uFE0F?)*"
    ")"
)


def _twemoji_codepoint(emoji):
    """Build the Twemoji filename codepoint for an emoji cluster.
    Mirrors Twemoji's own rule: strip the variation selector (FE0F) unless the
    cluster contains a zero-width joiner (ZWJ), then join codepoints with '-'.
    """
    if "\u200d" not in emoji:
        emoji = emoji.replace("\ufe0f", "")
    return "-".join(f"{ord(c):x}" for c in emoji)


def twemojify(text, size="1em"):
    """Replace emoji in text with Twemoji <img> tags. size sets the rendered
    height/width (defaults to 1em so it scales with the surrounding font size).
    """
    if not text:
        return text

    def _replace(match):
        emoji = match.group(0)
        code = _twemoji_codepoint(emoji)
        src = f"{_TWEMOJI_CDN}/{code}.svg"
        return (
            f"<img class='twemoji' src='{src}' alt='{emoji}' draggable='false' "
            f"style='height:{size}; width:{size}; margin:0 .08em; "
            f"vertical-align:-0.15em; display:inline-block;' loading='lazy' />"
        )

    return _EMOJI_RE.sub(_replace, text)


def _get_pollinations_key():
    try:
        return st.secrets.get("POLLINATIONS_API_KEY") or os.getenv("POLLINATIONS_API_KEY")
    except Exception:
        return os.getenv("POLLINATIONS_API_KEY")


# ==================== SUPABASE IMAGE CACHE (durable, shared across users) ====================
# A generated image is saved to Supabase storage and indexed by its keyword.
# The next user who needs the SAME keyword gets the stored image instantly,
# with no new generation. The cache fills up and gets more useful over time.
# This layer is OPTIONAL: if the Supabase secrets are not set, image generation
# works exactly as before (generate fresh each time).

_IMAGE_BUCKET = "flashcard-images"


@st.cache_resource(show_spinner=False)
def _get_supabase():
    """Return a cached Supabase client, or None if not configured."""
    try:
        try:
            url = st.secrets.get("SUPABASE_URL")
            key = st.secrets.get("SUPABASE_KEY")
        except Exception:
            url = key = None
        url = url or os.getenv("SUPABASE_URL")
        key = key or os.getenv("SUPABASE_KEY")
        if not url or not key:
            return None
        from supabase import create_client
        return create_client(url, key)
    except Exception as e:
        print(f"Supabase init skipped: {e}")
        return None


def _normalise_keyword(text):
    """Lowercase, strip punctuation, collapse spaces."""
    cleaned = re.sub(r"[^\w\s-]", "", text or "").lower()
    return re.sub(r"\s+", " ", cleaned).strip()


# Common filler words to strip when extracting a short cache key from a long
# image_search phrase like "a dog using body language to communicate with owner"
_STOP_WORDS = {
    "a", "an", "the", "of", "in", "on", "at", "to", "for", "with", "by",
    "from", "into", "about", "as", "its", "their", "his", "her", "that",
    "this", "these", "those", "and", "or", "but", "is", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "do", "does",
    "did", "show", "showing", "shows", "depict", "depicting", "depicts",
    "illustrate", "illustrating", "illustrates", "image", "picture",
    "photo", "photograph", "diagram", "using", "used", "use", "uses",
    "during", "between", "through", "across", "under", "over", "around",
}


def _extract_cache_key(query):
    """Reduce a long image_search phrase to 2-4 meaningful words.

    "a dog using body language to communicate with its owner"
    -> "dog body language"

    This dramatically increases cache hits because two cards about the same
    topic produce slightly different long phrases but the same short key.
    """
    words = _normalise_keyword(query).split()
    core = [w for w in words if w not in _STOP_WORDS and len(w) > 2]
    # Keep at most 4 words so the key stays stable
    return " ".join(core[:4])


def _cache_lookup(keyword):
    """Return a stored image URL for this keyword, or None.
    Tries the short core key first, then falls back to the full normalised
    phrase so existing cache entries are not lost after this update.
    """
    sb = _get_supabase()
    if not sb or not keyword:
        return None
    try:
        # Primary: short core key
        res = (sb.table("image_cache")
                 .select("image_url")
                 .eq("keyword", keyword)
                 .limit(1)
                 .execute())
        if res.data:
            return res.data[0]["image_url"]
    except Exception as e:
        print(f"Cache lookup error for '{keyword}': {e}")
    return None


def _cache_store(core_key, full_description, image_bytes, mime):
    """Upload the image to Supabase storage and index it by core_key.
    Also stores the full_description so you can see what each image is.
    """
    sb = _get_supabase()
    if not sb or not core_key:
        return None
    try:
        ext = "png" if "png" in mime else "jpg"
        safe = re.sub(r"[^a-z0-9_-]+", "_", core_key).strip("_") or "image"
        path = f"{safe}.{ext}"
        sb.storage.from_(_IMAGE_BUCKET).upload(
            path, image_bytes,
            {"content-type": mime, "upsert": "true"},
        )
        public_url = sb.storage.from_(_IMAGE_BUCKET).get_public_url(path)
        sb.table("image_cache").upsert(
            {"keyword": core_key, "image_url": public_url, "description": full_description}
        ).execute()
        return public_url
    except Exception as e:
        print(f"Cache store error for '{core_key}': {e}")
        return None


@st.cache_data(show_spinner=False, ttl=3600)
def search_wikipedia_image(query):
    """Return an image URL for the topic query.
    Order: Supabase cache (short core key) -> generate via Pollinations
    then save to cache for everyone else.
    """
    if not query:
        return None

    core_key = _extract_cache_key(query)
    if not core_key:
        return None

    # 1) Check cache with the short core key
    cached = _cache_lookup(core_key)
    if cached:
        return cached

    # 2) Generate a fresh image
    api_key = _get_pollinations_key()
    if not api_key:
        return None

    prompt = (
        f"cheerful educational illustration of {query}, "
        "child-friendly, bright flat colours, friendly cartoon style, "
        "simple clean background, appropriate for ages 4 to 18, "
        "no people, no violence, no scary imagery, no text, no labels"
    )

    try:
        import urllib.parse
        import base64
        encoded = urllib.parse.quote(prompt)
        url = f"https://gen.pollinations.ai/image/{encoded}?model=flux&key={api_key}&width=500&height=500&nologo=true"
        response = requests.get(url, timeout=30)
        if response.ok and response.headers.get("content-type", "").startswith("image"):
            mime = response.headers.get("content-type", "image/jpeg").split(";")[0]
            # 3) Save to cache using short key + full description
            public_url = _cache_store(core_key, query, response.content, mime)
            if public_url:
                return public_url
            # Fallback: cache not configured or upload failed
            b64 = base64.b64encode(response.content).decode()
            return f"data:{mime};base64,{b64}"
    except Exception as e:
        print(f"Pollinations error for '{query}': {e}")

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

    # Scale card count to text length
    n_chars = len(raw_text)
    if n_chars <= 5000:
        min_cards, max_cards = 3, 5
    elif n_chars <= 12000:
        min_cards, max_cards = 5, 10
    elif n_chars <= 20000:
        min_cards, max_cards = 8, 15
    else:
        min_cards, max_cards = 12, 20

    # Reading level instructions
    if reading_level == "simple":
        level_text = (
            "EASY (Ages 4-11): Use very short, common words only. "
            "One idea per sentence. Maximum 10 words per sentence. "
            "Active voice always. Use digits for numbers (e.g. 3 not three). "
            "No jargon — if a technical word is essential, explain it in the same sentence."
        )
    elif reading_level == "complex":
        level_text = (
            "ADVANCED (Ages 18+): Use precise academic vocabulary. "
            "Sentences up to 25 words. Include technical terms where appropriate. "
            "Active voice preferred. Digits for numbers. No double negatives."
        )
    else:
        level_text = (
            "MEDIUM (Ages 11-18): Clear everyday language. "
            "One idea per sentence, 12-18 words max. Active voice. "
            "Digits for numbers. Avoid jargon unless explained."
        )

    prompt = f"""You are creating educational flashcards for students with dyslexia, ADHD, and other learning differences.

READING LEVEL: {level_text}

YOUR GOAL: Turn ALL key information from the text into {min_cards}-{max_cards} flashcards that work as a quick study summary.
- Group related ideas into clearly themed cards (e.g. "How Dogs Communicate", "What Dogs Eat").
- Every distinct topic or concept in the text must appear on at least one card — do not skip anything.
- Each card has 3-5 facts. Order the facts so the MOST important or memorable one comes first.
- Each fact must be a genuine key takeaway worth remembering — not filler, not an example, not trivia.
- Give each card a short, descriptive title that captures its theme at a glance.

WRITING RULES (follow strictly):
- Active voice: write "Dogs use smell to communicate." NOT "Smell is used by dogs."
- One idea per sentence — never join 2 facts with "and" or "but".
- Front-load the key word: start the sentence with what the fact is actually about.
- Use digits for numbers: "3 types" not "three types".
- No double negatives.
- No vague openers like "It is important to note..." — start with the subject.
- Each fact must make sense on its own without reading the others.
- Keep facts tight: a clear summary sentence, not a long explanation.

IMAGE (very important — this drives the card illustration):
- Each card needs an "image_search": a descriptive phrase (8-15 words) that would find the RIGHT image for this card's specific topic.
- Be specific, not generic. "a dog using body language to show happiness to its owner" beats "dog".
- Describe the scene or concept visually: what would you see in a good illustration of this card?
- Avoid abstract words that don't translate to images (e.g. "importance", "overview").

EMOJI (very important — this app relies on visual cues):
- Each fact needs an "emoji": the SINGLE best emoji that represents that fact's MAIN idea.
- Choose it for meaning, not for a stray word. "Whales migrate each year" -> the journey, not the animal.
- Pick concrete, instantly recognisable emojis. Vary them across the facts on a card.
- Also include an "emoji_hint": one keyword for that fact (used as a backup).

Return ONLY valid JSON in this exact format, no commentary:
{{
  "flashcards": [
    {{
      "title": "How Dogs Communicate",
      "topic_keyword": "dog",
      "image_search": "a dog using body language to communicate with its owner",
      "facts": [
        {{"text": "Dogs use body language to show how they feel.", "emoji": "🗣️", "emoji_hint": "body language"}},
        {{"text": "A wagging tail usually means a dog is happy.", "emoji": "〰️", "emoji_hint": "tail"}},
        {{"text": "Dogs growl to warn others to stay away.", "emoji": "🔊", "emoji_hint": "growl"}}
      ]
    }}
  ]
}}

TEXT TO CONVERT:
{raw_text[:70000]}"""

    try:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You create flashcards. For each fact you choose the single best emoji representing its main idea, and order the facts with the most important first. Return only valid JSON."},
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
        for fact in card.get("facts", [])[:5]:
            if isinstance(fact, dict):
                fact_text = fact.get("text", "")
                emoji_hint = fact.get("emoji_hint", "")
                llm_emoji = fact.get("emoji", "")
                # 1) Trust the LLM's chosen emoji if it is a real emoji - it
                #    understands the sentence's MEANING, not just its keywords.
                # 2) Else match keywords in the fact text (curated fallback).
                # 3) Else match the LLM's keyword hint.
                # 4) Else fall back to the topic emoji (always relevant).
                if _looks_like_emoji(llm_emoji):
                    fact_emoji = llm_emoji.strip()
                else:
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
    """High-resolution 1920×1080 PNG render respecting the chosen colour scheme."""
    W, H = 1920, 1080
    MARGIN = 72
    CX1, CY1 = MARGIN, MARGIN
    CX2, CY2 = W - MARGIN, H - MARGIN

    card_bg  = colors.get("card_bg", "#FFFFFF")
    text_col = colors.get("text",     "#1C1C1C")
    accent   = colors.get("accent",   "#3A7CA5")

    def hex_to_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    img  = Image.new("RGB", (W, H), hex_to_rgb(page_bg_hex))
    draw = ImageDraw.Draw(img)

    # Card background
    draw.rectangle([CX1, CY1, CX2, CY2], fill=hex_to_rgb(card_bg))

    # Accent stripe across top (6 px tall)
    draw.rectangle([CX1, CY1, CX2, CY1 + 12], fill=hex_to_rgb(accent))

    # Fonts — graceful fallback
    try:
        font_title  = ImageFont.truetype("DejaVuSans-Bold.ttf", 80)
        font_label  = ImageFont.truetype("DejaVuSans-Bold.ttf", 36)
        font_fact   = ImageFont.truetype("DejaVuSans.ttf",      46)
    except Exception:
        font_title  = ImageFont.load_default()
        font_label  = font_title
        font_fact   = font_title

    # --- Left panel: polaroid image (if available) ---
    text_x = CX1 + 80          # default: full-width text start
    if wiki_image_bytes:
        try:
            wiki_img = Image.open(BytesIO(wiki_image_bytes)).convert("RGB")
            panel_w  = (CX2 - CX1) // 2 - 80
            panel_h  = CY2 - CY1 - 140
            wiki_img.thumbnail((panel_w, panel_h), Image.LANCZOS)

            pol_pad  = 18
            pol_bott = 52           # extra bottom border for polaroid caption area
            pol_w    = wiki_img.width  + pol_pad * 2
            pol_h    = wiki_img.height + pol_pad + pol_bott
            pol_x    = CX1 + 60
            pol_y    = CY1 + (CY2 - CY1 - pol_h) // 2   # vertically centred

            draw.rectangle(
                [pol_x, pol_y, pol_x + pol_w, pol_y + pol_h],
                fill=(255, 255, 255)
            )
            img.paste(wiki_img, (pol_x + pol_pad, pol_y + pol_pad))

            # Polaroid caption line
            cap = card['title'][:30]
            cap_bbox = draw.textbbox((0, 0), cap, font=font_label)
            cap_x    = pol_x + (pol_w - (cap_bbox[2] - cap_bbox[0])) // 2
            cap_y    = pol_y + pol_pad + wiki_img.height + 10
            draw.text((cap_x, cap_y), cap, fill=hex_to_rgb(accent), font=font_label)

            text_x = pol_x + pol_w + 70
        except Exception:
            pass  # fall through to full-width text

    # --- Right panel (or full width): title + facts ---
    content_w = CX2 - text_x - 60

    # "KEY FACTS" label
    draw.text((text_x, CY1 + 50), "KEY FACTS",
              fill=hex_to_rgb(accent), font=font_label)

    # Title (wrap if needed)
    title = card['title']
    title_y = CY1 + 110
    chars_per_line = max(content_w // 44, 10)
    words = title.split()
    lines, line = [], []
    for w in words:
        if sum(len(x) + 1 for x in line) + len(w) > chars_per_line and line:
            lines.append(" ".join(line)); line = [w]
        else:
            line.append(w)
    if line:
        lines.append(" ".join(line))
    for ln in lines[:2]:
        draw.text((text_x, title_y), ln, fill=hex_to_rgb(text_col), font=font_title)
        title_y += 96

    # Divider
    div_y = title_y + 20
    draw.rectangle([text_x, div_y, text_x + content_w, div_y + 3],
                   fill=hex_to_rgb(accent))

    # Facts
    fact_y = div_y + 36
    for fact in card['facts'][:5]:
        fact_text = fact.get('text', '') if isinstance(fact, dict) else str(fact)
        # Wrap
        chars_f = max(content_w // 26, 10)
        fwords  = fact_text.split()
        flines, fl = [], []
        for w in fwords:
            if sum(len(x) + 1 for x in fl) + len(w) > chars_f and fl:
                flines.append(" ".join(fl)); fl = [w]
            else:
                fl.append(w)
        if fl: flines.append(" ".join(fl))
        for ln in flines[:2]:
            draw.text((text_x + 10, fact_y), ln,
                      fill=hex_to_rgb(text_col), font=font_fact)
            fact_y += 56
        fact_y += 8     # gap between facts

    # Card counter
    counter = f"{idx + 1} / {total}"
    cb = draw.textbbox((0, 0), counter, font=font_label)
    draw.text(
        (CX2 - (cb[2] - cb[0]) - 24, CY2 - 50),
        counter, fill=hex_to_rgb(accent), font=font_label
    )

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


def _cute_star_svg_markup():
    """Option A kawaii star: gold body, sparkly eyes, smile, rosy cheeks."""
    return (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='-72 -72 144 144'>"
        "<polygon points='0,-60 15.3,-21 57.1,-18.5 24.7,8 35.3,48.5 0,26 "
        "-35.3,48.5 -24.7,8 -57.1,-18.5 -15.3,-21' fill='#FFD93B' "
        "stroke='#F0B400' stroke-width='9' stroke-linejoin='round'/>"
        "<ellipse cx='-15' cy='-8' rx='6.5' ry='9' fill='#3A2E2E'/>"
        "<ellipse cx='15' cy='-8' rx='6.5' ry='9' fill='#3A2E2E'/>"
        "<circle cx='-12.5' cy='-11' r='2.4' fill='#ffffff'/>"
        "<circle cx='17.5' cy='-11' r='2.4' fill='#ffffff'/>"
        "<path d='M -12 6 Q 0 20 12 6' fill='none' stroke='#3A2E2E' "
        "stroke-width='3.5' stroke-linecap='round'/>"
        "<ellipse cx='-27' cy='6' rx='7' ry='4.5' fill='#FF9EB5'/>"
        "<ellipse cx='27' cy='6' rx='7' ry='4.5' fill='#FF9EB5'/>"
        "</svg>"
    )


def _cute_star_img(size="1em", cls=""):
    """Render the kawaii star as an <img> (data-URI SVG) so it always shows in
    Streamlit. The element itself is animated by CSS in apply_styles()."""
    import urllib.parse
    uri = "data:image/svg+xml;utf8," + urllib.parse.quote(_cute_star_svg_markup())
    return (
        f"<img class='fcm-star-svg {cls}' src=\"{uri}\" alt='' aria-hidden='true' "
        f"style='height:{size}; width:{size}; vertical-align:-0.15em; "
        f"display:inline-block;' />"
    )


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

    if colour_scheme == "Low Stimulation":
        left_stars = right_stars = ""
    else:
        left_stars = (
            _cute_star_img("0.7em", "fcm-star-b")
            + _cute_star_img("1.05em", "fcm-star-a") + " "
        )
        right_stars = (
            " " + _cute_star_img("1.05em", "fcm-star-a")
            + _cute_star_img("0.7em", "fcm-star-b")
        )

    st.markdown(f"""
    <div class="fcm-header" style='text-align:center; padding:24px 20px;
                background:linear-gradient(135deg, {accent}, {grad_end});
                border-radius:14px; margin-bottom:20px;'>
        <h1 style='color:{title_color}; margin:0; line-height:1.15;
                   font-size:{text_size * 2}px;'>{left_stars}<span class="fcm-title-text">{app_title}</span>{right_stars}</h1>
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
    # --- Load the non-system fonts so the Font Style selector actually works ---
    # Arial / Comic Sans MS / Calibri are (usually) installed locally and render
    # as-is. Everything else must be pulled in as a webfont, otherwise the
    # browser silently falls back to the default sans-serif and switching fonts
    # appears to "do nothing". Google Fonts covers most; OpenDyslexic ships via
    # an @font-face (it isn't on Google Fonts). Gotham is proprietary and can't
    # be loaded from a free CDN, so it will still fall back unless self-hosted.
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bangers&family=Fredoka:wght@400;500;600&family=Oswald:wght@400;700&family=Playfair+Display:wght@400;700&family=Roboto:wght@400;500;700&display=swap');
@font-face {
    font-family: 'OpenDyslexic';
    src: url('https://cdn.jsdelivr.net/gh/madjeek-web/open-dyslexic@main/OpenDyslexic-2025/opendyslexic-regular-webfont.woff2') format('woff2'),
         url('https://cdn.jsdelivr.net/gh/madjeek-web/open-dyslexic@main/OpenDyslexic-2025/opendyslexic-regular-webfont.woff') format('woff');
    font-weight: normal; font-style: normal; font-display: swap;
}
@font-face {
    font-family: 'OpenDyslexic';
    src: url('https://cdn.jsdelivr.net/gh/madjeek-web/open-dyslexic@main/OpenDyslexic-2025/opendyslexic-bold-webfont.woff2') format('woff2');
    font-weight: bold; font-style: normal; font-display: swap;
}
</style>
""", unsafe_allow_html=True)

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
    .stApp p:not([style]), .stApp li:not([style]), .stApp label:not([style]),
    .stApp span:not([style]), .stMarkdown:not([style]) {{
        font-size: {text_size}px !important;
        line-height: {line_spacing} !important;
        color: {text} !important;
    }}
    /* Elements with inline styles keep their own font/line-height but not a forced colour */
    .stApp p[style], .stApp li[style], .stApp span[style] {{
        font-size: {text_size}px !important;
        line-height: {line_spacing} !important;
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
        /* iOS fix: font-size below 16px triggers auto-zoom on focus, which
           is very jarring on mobile. We enforce 16px minimum here.
           The user's chosen text_size still applies via the CSS cascade for
           non-input elements. */
        font-size: max({text_size}px, 16px) !important;
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

    /* ---- MOBILE FIX: stop hidden number inputs on sliders triggering the keyboard ---- */
    /* Streamlit renders a hidden <input type="number"> inside every slider for
       accessibility. On mobile browsers this input is sometimes focusable,
       which pops up the numeric keyboard. We make it truly non-interactive. */
    .stSlider input[type="number"],
    .stSlider input {{
        pointer-events: none !important;
        user-select: none !important;
        -webkit-user-select: none !important;
        opacity: 0 !important;
        position: absolute !important;
        width: 1px !important;
        height: 1px !important;
        overflow: hidden !important;
        clip: rect(0,0,0,0) !important;
        /* Prevent mobile browsers from focusing and opening a keyboard */
        tabindex: -1 !important;
        readonly: true !important;
    }}

    /* ---- Links ---- */
    .stApp a {{ color: {accent} !important; }}

    /* ---- Header banner (HIGHER specificity than the blanket h1/p rules) ---- */
    /* These win because `.stApp .fcm-header h1` (0,2,1) beats `.stApp h1`     */
    /* (0,1,1). Set here in a <style> block - not inline - because Streamlit   */
    /* strips !important from inline style attributes.                         */
    .stApp .fcm-header h1,
    .stApp .fcm-header h1 .fcm-title-text {{
        color: {header_title_col} !important;
        font-size: {text_size * 2}px !important;
        line-height: 1.15 !important;
    }}
    .stApp .fcm-header p {{
        color: {header_subtitle_col} !important;
        font-size: {text_size}px !important;
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
    /* Cute star gentle bob + wiggle. Disabled automatically when the user   */
    /* has asked their device for reduced motion (sensory-friendly).         */
    @keyframes fcmStarBob {{
        0%, 100% {{ transform: translateY(0) rotate(0deg); }}
        30%      {{ transform: translateY(-3px) rotate(-7deg); }}
        60%      {{ transform: translateY(-1px) rotate(7deg); }}
    }}
    .stApp .fcm-header .fcm-star-svg {{
        animation: fcmStarBob 2.6s ease-in-out infinite;
        transform-origin: 50% 60%;
    }}
    .stApp .fcm-header .fcm-star-b {{
        animation-duration: 3.2s;
        animation-delay: 0.5s;
    }}
    @media (prefers-reduced-motion: reduce) {{
        .stApp .fcm-header .fcm-star-svg {{ animation: none; }}
    }}
    </style>
    """, unsafe_allow_html=True)
