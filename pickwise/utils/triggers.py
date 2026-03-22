"""
Trigger words, phrases, and patterns for intent recognition.
Used to match user queries to the correct response pathway even with
varied phrasing, synonyms, and abbreviations. All matching is case-insensitive.
"""

from typing import List, Optional, Set

# ---------------------------------------------------------------------------
# INTENT TRIGGERS: phrases (substring match) and keywords (token match)
# ---------------------------------------------------------------------------

# Items to counter a hero: "Best items to counter PA?", "What items counter X?"
COUNTER_HERO_ITEMS_PHRASES: List[str] = [
    "best items to counter",
    "items to counter",
    "what items to counter",
    "what items counter",
    "items that counter",
    "items against",
    "best items against",
    "what items are good against",
    "item counters for",
    "counter items for",
    "items to beat",
    "what to buy against",
    "what to build against",
    "recommended items against",
    "good items against",
]

COUNTER_HERO_ITEMS_KEYWORDS: Set[str] = {
    "items", "item", "build", "buy", "purchase",
}

# Hero counters: "How do I counter X?", "What heroes are good against Y?", etc.
COUNTER_HEROES_PHRASES: List[str] = [
    "how do i counter",
    "how to counter",
    "how can i counter",
    "what counters",
    "what hero counters",
    "what heroes counter",
    "who counters",
    "who is good against",
    "who's good against",
    "good against",
    "strong against",
    "best against",
    "counter pick",
    "counterpick",
    "counter pick for",
    "beat ",
    "how to beat",
    "how do i beat",
    "deal with",
    "how to deal with",
    "answer to",
    "answer for",
    "handle ",
    "how to handle",
    "versus",
    " vs ",
    "vs ",
    " vs.",
    "weak against",
    "lose to",
    "losing to",
    "struggle against",
    "counter to",
    "anti ",
    "destroy ",
    "shut down",
    "shutdown",
]

COUNTER_HEROES_KEYWORDS: Set[str] = {
    "counter", "counters", "counterpick", "counter-pick",
    "beat", "against", "versus", "vs", "good against", "strong against",
    "deal", "handle", "answer", "anti", "shut", "destroy",
}

# Item builds: "Best build for X", "What items should I buy on Y?", etc.
HERO_BUILD_PHRASES: List[str] = [
    "best build",
    "best build for",
    "build for",
    "item build",
    "item build for",
    "items for",
    "what items for",
    "what items should",
    "what should i build",
    "what should i buy",
    "what to build",
    "what to buy",
    "items to build",
    "items to buy",
    "buy on",
    "build on",
    "purchase on",
    "core items",
    "core build",
    "itemization",
    "itemization for",
    "recommended items",
    "suggested items",
    "guide for",
    "build guide",
    "what do i build",
    "what do i buy",
    "starting items",
    "early items",
    "late game items",
    "best items for",
    "good items for",
]

HERO_BUILD_KEYWORDS: Set[str] = {
    "build", "builds", "items", "itemization", "itemisation",
    "buy", "purchase", "core", "recommended", "guide", "setup",
}

# Strategy advice: "How do I lane against X?", "Tips against Z", etc.
STRATEGY_PHRASES: List[str] = [
    "how do i lane",
    "how to lane",
    "lane against",
    "laning against",
    "tips for",
    "tips against",
    "tips vs",
    "advice for",
    "advice against",
    "how to play against",
    "how do i play against",
    "playing against",
    "play against",
    "best early game",
    "early game for",
    "early game against",
    "how to fight",
    "how do i fight",
    "fight against",
    "strategy against",
    "strategy for",
    "matchup",
    "matchup against",
    "win against",
    "win vs",
    "beating ",
    "beating the",
    "how to win",
    "role for",
    "best role for",
    "position for",
    "playstyle",
    "play style",
]

STRATEGY_KEYWORDS: Set[str] = {
    "tips", "advice", "strategy", "lane", "laning", "matchup",
    "play", "fighting", "early", "role", "position", "playstyle",
}

# Item explanations: "What is X item?", "Explain Y", "What does Z do?"
ITEM_INFO_PHRASES: List[str] = [
    "what is ",
    "whats ",
    "what's ",
    "what does ",
    "what do ",
    "how does ",
    "how do ",
    "explain ",
    "tell me about",
    "describe ",
    "info about",
    "info on",
    "information about",
    "meaning of",
    "what is the ",
    "explain the",
    "how does the",
    "what does the",
]

ITEM_INFO_KEYWORDS: Set[str] = {
    "what", "explain", "describe", "meaning", "info", "information",
    "does", "work", "do", "description",
}

# Item counter: "How to counter BKB?", "Counter Ghost Scepter"
COUNTER_ITEMS_PHRASES: List[str] = [
    "counter ",
    "how to counter",
    "how do i counter",
    "counter to",
    "deal with ",
    "how to deal with",
    "against ",
    "beat ",
    "answer to",
    "handle ",
]

COUNTER_ITEMS_KEYWORDS: Set[str] = {
    "counter", "deal", "beat", "against", "versus", "vs", "handle",
}

# Self-introduction
SELF_INTRO_PHRASES: List[str] = [
    "who are you",
    "what are you",
    "introduce yourself",
    "what is pickwise",
    "whats pickwise",
    "what's pickwise",
    "what do you do",
    "what is this chatbot",
    "what is this bot",
    "what can you do",
    "tell me about yourself",
    "who is pickwise",
    "what kind of bot",
    "are you a bot",
    "are you an ai",
    "your name",
    "your purpose",
]

SELF_INTRO_KEYWORDS: Set[str] = {
    "who", "yourself", "pickwise", "assistant", "bot", "chatbot", "intro",
}

# General gameplay
GENERAL_PHRASES: List[str] = [
    "how to win",
    "how to win lane",
    "best role",
    "general tips",
    "dota tips",
    "gameplay tips",
    "how to play",
    "beginner",
    "meta ",
    "current meta",
]

GENERAL_KEYWORDS: Set[str] = {
    "win", "lane", "role", "meta", "general", "gameplay", "tips",
}


def _normalize_for_trigger(q: str) -> str:
    """Lowercase, strip; used for phrase matching."""
    return q.lower().strip()


def match_intent_by_triggers(
    question: str,
    hero_detected: bool,
    item_detected: bool,
) -> Optional[str]:
    """
    Determine intent from trigger phrases and keywords.
    Returns intent string or None if no strong match.
    Priority: self_intro > counter_heroes (if hero) > hero_build (if hero) >
    counter_items (if item) > item_info (if item) > strategy (if hero) > general_strategy.
    """
    q = _normalize_for_trigger(question)
    if not q:
        return None

    # Phrase check: any of these substrings in question
    def has_phrase(phrases: List[str]) -> bool:
        return any(p in q for p in phrases)

    # Token set from preprocessed question (avoid circular import by lazy import)
    from .text_preprocessing import preprocess_text
    tokens: Set[str] = set(preprocess_text(question))

    def has_keywords(kw: Set[str]) -> bool:
        return bool(kw & tokens)

    # 1) Self-intro
    if has_phrase(SELF_INTRO_PHRASES) or (has_keywords(SELF_INTRO_KEYWORDS) and len(tokens) <= 6):
        return "self_intro"

    # 2) Items to counter this hero (must come before generic hero counters)
    if hero_detected and (
        has_phrase(COUNTER_HERO_ITEMS_PHRASES)
        or (has_keywords(COUNTER_HERO_ITEMS_KEYWORDS) and has_keywords(COUNTER_HEROES_KEYWORDS))
    ):
        return "counter_hero_items"

    # 3) Hero counter (need hero in message for routing; triggers only suggest intent)
    if hero_detected and (has_phrase(COUNTER_HEROES_PHRASES) or has_keywords(COUNTER_HEROES_KEYWORDS)):
        return "counter_heroes"

    # 4) Hero build
    if hero_detected and (has_phrase(HERO_BUILD_PHRASES) or has_keywords(HERO_BUILD_KEYWORDS)):
        return "hero_build"

    # 5) Item counter
    if item_detected and (has_phrase(COUNTER_ITEMS_PHRASES) or has_keywords(COUNTER_ITEMS_KEYWORDS)):
        return "counter_items"

    # 6) Item info/explanation
    if item_detected and (has_phrase(ITEM_INFO_PHRASES) or has_keywords(ITEM_INFO_KEYWORDS)):
        return "item_info"
    if item_detected:
        return "item_info"  # Just item name -> explain it

    # 7) Strategy (hero in message)
    if hero_detected and (has_phrase(STRATEGY_PHRASES) or has_keywords(STRATEGY_KEYWORDS)):
        return "general_strategy"

    # 8) General gameplay
    if has_phrase(GENERAL_PHRASES) or has_keywords(GENERAL_KEYWORDS):
        return "general_strategy"

    return None


def get_all_counter_phrases() -> List[str]:
    """Return combined counter-like phrases for use elsewhere (e.g. is_item_info_question)."""
    return list(COUNTER_HEROES_PHRASES) + list(COUNTER_ITEMS_PHRASES)
