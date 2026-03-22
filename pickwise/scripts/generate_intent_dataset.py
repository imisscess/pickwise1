#!/usr/bin/env python3
"""
Generate a comprehensive intent dataset for the PickWise chatbot.
Fetches all Dota 2 heroes and items from OpenDota and generates
natural question variations for counter_heroes, hero_build, item_info,
counter_items, general_strategy, and self_intro intents.
"""

import csv
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests

OPEN_DOTA = "https://api.opendota.com/api"
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "intents_dataset.csv"

# Hero counter question templates (hero name substituted as {hero})
HERO_COUNTER_TEMPLATES = [
    "What counters {hero}?",
    "Who counters {hero}?",
    "What heroes counter {hero}?",
    "Who is strong against {hero}?",
    "Who counters {hero} in Dota 2?",
    "How do I beat {hero}?",
    "How to beat {hero}?",
    "How do I counter {hero}?",
    "How to counter {hero}?",
    "How do I play against {hero}?",
    "Tips for fighting {hero}?",
    "What heroes are good against {hero}?",
    "Best counters for {hero}?",
    "Who should I pick against {hero}?",
    "Which heroes beat {hero}?",
    "How to deal with {hero}?",
    "What's the counter to {hero}?",
    "Strong against {hero}",
]

# Hero build question templates
HERO_BUILD_TEMPLATES = [
    "What should I build on {hero}?",
    "Best items for {hero}?",
    "Item build for {hero}",
    "What should I buy on {hero}?",
    "Best build for {hero}?",
    "What items for {hero}?",
    "Itemization for {hero}",
    "Recommended items for {hero}?",
    "Build guide for {hero}?",
    "What to build on {hero}?",
    "Items for {hero} build",
    "Optimal build for {hero}?",
    "Core items for {hero}?",
    "Starting items for {hero}?",
    "Late game items for {hero}?",
]

# Item info question templates
ITEM_INFO_TEMPLATES = [
    "What is {item}?",
    "What does {item} do?",
    "Explain {item}",
    "How does {item} work?",
    "Describe {item}",
    "Tell me about {item}",
    "Info about {item}",
    "What is {item} in Dota 2?",
    "What does {item} do in Dota?",
    "How does {item} work in Dota 2?",
    "Explain what {item} does",
    "What does {item} give?",
    "Stats for {item}?",
    "Info on {item}",
]

# Item counter question templates (for commonly countered items)
ITEM_COUNTER_TEMPLATES = [
    "How do I counter {item}?",
    "How to counter {item}?",
    "What counters {item}?",
    "Items against {item}?",
    "How to deal with {item}?",
    "Best items against {item}?",
    "What items counter {item}?",
    "How do you counter {item}?",
    "Counter to {item}?",
]

# General strategy question templates
GENERAL_STRATEGY_TEMPLATES = [
    "How should I play late game strategy?",
    "Tips for early game farming?",
    "How to win teamfights?",
    "Late game tips",
    "Early game farming tips?",
    "How to win team fights in Dota?",
    "What should I do in late game?",
    "Early game strategy?",
    "Teamfight tips for Dota 2?",
    "How to farm efficiently early?",
    "Late game strategy Dota 2",
    "Tips for winning teamfights?",
    "How to play late game?",
    "Best early game strategy?",
    "General Dota 2 strategy tips",
    "How to close out games?",
    "Farming tips early game",
    "When to take teamfights?",
    "Draft strategy tips",
    "Map control tips",
]

# Self-intro question templates
SELF_INTRO_TEMPLATES = [
    "Who are you?",
    "What are you?",
    "Introduce yourself",
    "What is PickWise?",
    "What do you do?",
    "What can you do?",
    "What kind of assistant are you?",
    "Tell me about yourself",
    "Who is PickWise?",
    "What is this chatbot?",
    "What is this bot?",
    "What is PickWise AI?",
    "What are you for?",
    "What kind of bot are you?",
    "Your name?",
    "Your purpose?",
    "Are you a bot?",
    "Are you an AI?",
    "Introduction",
    "Help",
]


def fetch_heroes():
    """Fetch all Dota 2 heroes from OpenDota."""
    resp = requests.get(f"{OPEN_DOTA}/heroes", timeout=10)
    resp.raise_for_status()
    return resp.json()


def fetch_items():
    """Fetch all Dota 2 items from OpenDota."""
    resp = requests.get(f"{OPEN_DOTA}/constants/items", timeout=10)
    resp.raise_for_status()
    return resp.json()


def is_relevant_item(key: str, data: dict) -> bool:
    """Filter out recipes and obscure items."""
    if "recipe" in key.lower():
        return False
    dname = (data.get("dname") or "").strip()
    if not dname:
        return False
    # Skip very basic components if desired; for comprehensive dataset include most
    return True


def main():
    print("Fetching heroes from OpenDota...")
    heroes = fetch_heroes()
    hero_names = [h["localized_name"] for h in heroes]
    print(f"  Found {len(hero_names)} heroes")

    print("Fetching items from OpenDota...")
    raw_items = fetch_items()
    items = []
    for key, data in raw_items.items():
        if isinstance(data, dict) and is_relevant_item(key, data):
            dname = data.get("dname") or key
            items.append(dname)
    items = sorted(set(items))
    print(f"  Found {len(items)} items")

    rows = []

    # Hero counter questions
    for name in hero_names:
        for tpl in HERO_COUNTER_TEMPLATES:
            rows.append((tpl.format(hero=name), "counter_heroes"))

    # Hero build questions
    for name in hero_names:
        for tpl in HERO_BUILD_TEMPLATES:
            rows.append((tpl.format(hero=name), "hero_build"))

    # Item info questions
    for name in items:
        for tpl in ITEM_INFO_TEMPLATES:
            rows.append((tpl.format(item=name), "item_info"))

    # Item counter questions (for commonly discussed items)
    counter_relevant = [
        "Black King Bar", "Ghost Scepter", "Blink Dagger", "Shiva's Guard",
        "Force Staff", "Glimmer Cape", "Scythe of Vyse", "Abyssal Blade",
        "Monkey King Bar", "Assault Cuirass", "Heart of Tarrasque", "Butterfly",
        "Radiance", "Divine Rapier", "Aghanim's Scepter", "Linken's Sphere",
        "Bloodthorn", "Nullifier", "Silver Edge", "Shadow Blade", "Ethereal Blade",
        "Mask of Madness",
    ]
    items_lower = {i.lower(): i for i in items}
    for cr in counter_relevant:
        match = items_lower.get(cr.lower())
        if not match:
            for k, v in items_lower.items():
                if cr.lower() in k or (len(cr) > 3 and k in cr.lower()):
                    match = v
                    break
        if match:
            for tpl in ITEM_COUNTER_TEMPLATES:
                rows.append((tpl.format(item=match), "counter_items"))
    # Abbreviation-based counter questions (entity detector maps these)
    for abbrev, full in [("BKB", "Black King Bar"), ("MKB", "Monkey King Bar"),
                         ("Shiva", "Shiva's Guard"), ("Hex", "Scythe of Vyse"),
                         ("AC", "Assault Cuirass")]:
        for tpl in ITEM_COUNTER_TEMPLATES[:5]:
            rows.append((tpl.format(item=abbrev), "counter_items"))

    # General strategy
    for tpl in GENERAL_STRATEGY_TEMPLATES:
        rows.append((tpl, "general_strategy"))

    # Self-intro
    for tpl in SELF_INTRO_TEMPLATES:
        rows.append((tpl, "self_intro"))

    # Deduplicate while preserving order
    seen = set()
    unique_rows = []
    for q, intent in rows:
        key = (q.lower().strip(), intent)
        if key not in seen:
            seen.add(key)
            unique_rows.append((q.strip(), intent))

    # Write CSV
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["question", "intent"])
        writer.writerows(unique_rows)

    print(f"\nWrote {len(unique_rows)} rows to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
