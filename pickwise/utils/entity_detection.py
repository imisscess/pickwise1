from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from .opendota_client import get_heroes, get_items
from .text_preprocessing import preprocess_text

# Common Dota 2 hero abbreviations and shorthand -> canonical lowercase name
# Used so "counter PA" / "build for BB" etc. resolve correctly
HERO_ABBREVIATIONS: List[Tuple[str, str]] = [
    ("pa", "phantom assassin"),
    ("bb", "bristleback"),
    ("am", "anti-mage"),
    ("bm", "beastmaster"),
    ("bs", "bloodseeker"),
    ("cm", "crystal maiden"),
    ("dk", "dragon knight"),
    ("dp", "death prophet"),
    ("es", "earthshaker"),
    ("io", "wisp"),
    ("kotl", "keeper of the light"),
    ("lc", "legion commander"),
    ("ls", "lifestealer"),
    ("na", "nyx assassin"),
    ("np", "nature's prophet"),
    ("ns", "night stalker"),
    ("od", "outworld destroyer"),
    ("omni", "omniknight"),
    ("pl", "phantom lancer"),
    ("pudge", "pudge"),
    ("sb", "spirit breaker"),
    ("sf", "shadow fiend"),
    ("shaker", "earthshaker"),
    ("sniper", "sniper"),
    ("ss", "shadow shaman"),
    ("storm", "storm spirit"),
    ("ta", "templar assassin"),
    ("tb", "terrorblade"),
    ("ts", "timbersaw"),
    ("vengeful", "vengeful spirit"),
    ("wd", "witch doctor"),
    ("wk", "wraith king"),
    ("wr", "windranger"),
    ("zeus", "zeus"),
]

# Item abbreviations
ITEM_ABBREVIATIONS: List[Tuple[str, str]] = [
    ("bkb", "black king bar"),
    ("mkb", "monkey king bar"),
    ("sny", "sange and yasha"),
    ("yasha", "yasha"),
    ("sange", "sange"),
    ("mom", "mask of madness"),
    ("bf", "butterfly"),
    ("daed", "daedalus"),
    ("rapier", "divine rapier"),
    ("shiva", "shiva's guard"),
    ("shivas", "shiva's guard"),
    ("hex", "scythe of vyse"),
    ("abyssal", "abyssal blade"),
    ("ac", "assault cuirass"),
    ("ags", "aghanim's scepter"),
    ("aghs", "aghanim's scepter"),
    ("bloodthorn", "bloodthorn"),
]


@dataclass
class HeroEntity:
    id: int
    name: str
    localized_name: str


@dataclass
class ItemEntity:
    key: str
    display_name: str


@lru_cache(maxsize=1)
def _hero_name_map() -> Dict[str, HeroEntity]:
    """
    Build a lookup from lowercase hero name phrases and abbreviations to HeroEntity.
    """
    mapping: Dict[str, HeroEntity] = {}
    for hero in get_heroes():
        entity = HeroEntity(
            id=hero["id"],
            name=hero["name"],
            localized_name=hero["localized_name"],
        )
        loc = hero["localized_name"].lower()
        mapping[loc] = entity
        mapping[loc.replace(" ", "")] = entity
    for abbrev, canonical in HERO_ABBREVIATIONS:
        ent = mapping.get(canonical) or mapping.get(canonical.replace(" ", ""))
        if ent:
            mapping[abbrev] = ent
    return mapping


@lru_cache(maxsize=1)
def _item_name_map() -> Dict[str, ItemEntity]:
    """
    Build a lookup from lowercase item name phrases to ItemEntity.
    """
    mapping: Dict[str, ItemEntity] = {}
    items = get_items()
    for key, data in items.items():
        display_raw = data.get("dname") or key
        display = display_raw.lower()
        entity = ItemEntity(key=key, display_name=display_raw)

        # Base forms (case-insensitive; various formats)
        variants = {
            display,
            display.replace(" ", ""),
            display.replace("'", ""),
            display.replace(" ", "").replace("'", ""),
        }
        # Possessive / "What's Shiva's Guard" -> preprocess yields "shiva guard" or "shivaguard"
        no_possessive = display.replace("'s ", " ").replace("'s", " ").replace("'", "").strip()
        if no_possessive:
            variants.add(no_possessive)
            variants.add(no_possessive.replace(" ", ""))

        # Also index by key forms
        key_lower = key.lower()
        variants.update(
            {
                key_lower,
                key_lower.replace("_", " "),
                key_lower.replace("_", ""),
            }
        )

        for v in variants:
            if v:
                mapping[v] = entity

    for abbrev, name_part in ITEM_ABBREVIATIONS:
        name_lower = name_part.lower()
        for k, ent in list(mapping.items()):
            if name_lower in ent.display_name.lower():
                mapping[abbrev] = ent
                break

    return mapping


def detect_hero(text: str) -> Optional[HeroEntity]:
    """
    Detect a hero mentioned in the user text by matching against
    the live hero name list from OpenDota and common abbreviations (PA, BB, AM, etc.).
    """
    words = preprocess_text(text)
    joined = " ".join(words)
    compact = joined.replace(" ", "")

    hero_map = _hero_name_map()

    # Prefer full names, then abbreviations (e.g. "phantom assassin" before "pa")
    for key, hero in hero_map.items():
        if " " in key and key in joined:
            return hero
        if key.replace(" ", "") in compact:
            return hero
        if key in words or key in joined:
            return hero

    return None


def detect_item(text: str) -> Optional[ItemEntity]:
    """
    Detect an item mentioned in the user text by matching against
    the live item name list from OpenDota. Case-insensitive; matches
    various formats (with/without apostrophes, spaces).
    """
    text_lower = text.lower().strip()
    text_normalized = text_lower.replace("'", "")

    item_map = _item_name_map()

    # First pass: match item display names directly in raw message
    # (handles "What's Shiva's Guard?" even if tokenizer drops apostrophe)
    for key, item in item_map.items():
        name_lower = item.display_name.lower()
        if name_lower in text_lower:
            return item
        if name_lower.replace("'", "") in text_normalized:
            return item
        # Without apostrophe: "shivas guard" or "shiva guard"
        name_no_apos = name_lower.replace("'s ", " ").replace("'s", " ").replace("'", "")
        if name_no_apos in text_lower or name_no_apos.replace(" ", "") in text_normalized:
            return item

    # Second pass: token-based match (preprocessed)
    words = preprocess_text(text)
    joined = " ".join(words)
    compact = joined.replace(" ", "")

    for key, item in item_map.items():
        if " " in key and key in joined:
            return item
        if key.replace(" ", "") in compact:
            return item

    return None

