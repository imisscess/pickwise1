import requests
from dataclasses import dataclass
from enum import Enum, auto
from functools import lru_cache
from typing import Dict, List, Optional, Tuple
import difflib


BASE_URL = "https://api.opendota.com/api"


class OpenDotaError(Exception):
    pass


def _get_json(path: str) -> dict:
    url = f"{BASE_URL}{path}"
    try:
        resp = requests.get(url, timeout=8)
        if resp.status_code != 200:
            raise OpenDotaError(f"OpenDota status {resp.status_code}")
        return resp.json()
    except requests.RequestException as e:
        raise OpenDotaError(f"OpenDota request failed: {e}") from e


@lru_cache(maxsize=1)
def get_heroes() -> List[dict]:
    return _get_json("/heroes")


@lru_cache(maxsize=1)
def get_items() -> Dict[str, dict]:
    return _get_json("/constants/items")


def get_hero_matchups(hero_id: int) -> List[dict]:
    return _get_json(f"/heroes/{hero_id}/matchups")


def get_hero_item_popularity(hero_id: int) -> dict:
    return _get_json(f"/heroes/{hero_id}/itemPopularity")


@dataclass
class HeroInfo:
    id: int
    name: str
    localized_name: str


@dataclass
class ItemInfo:
    key: str
    display_name: str
    raw: dict


class QuestionType(Enum):
    HERO_COUNTER = auto()
    HERO_BUILD = auto()
    ITEM_EXPLANATION = auto()
    ITEM_COUNTER = auto()
    GAMEPLAY_STRATEGY = auto()


@lru_cache(maxsize=1)
def _hero_name_maps() -> Tuple[Dict[str, HeroInfo], List[str]]:
    heroes = get_heroes()
    name_to_hero: Dict[str, HeroInfo] = {}

    for h in heroes:
        hi = HeroInfo(id=h["id"], name=h["name"], localized_name=h["localized_name"])
        variants = {
            h["localized_name"],
            h["localized_name"].replace(" ", ""),
            h["localized_name"].replace(" ", "").lower(),
            h["localized_name"].lower(),
        }
        for v in variants:
            name_to_hero[v] = hi

    all_keys = list(name_to_hero.keys())
    return name_to_hero, all_keys


@lru_cache(maxsize=1)
def _item_name_maps() -> Tuple[Dict[str, ItemInfo], List[str]]:
    items = get_items()
    name_to_item: Dict[str, ItemInfo] = {}

    for key, raw in items.items():
        display = raw.get("dname") or key
        ii = ItemInfo(key=key, display_name=display, raw=raw)

        variants = {
            display,
            display.replace(" ", ""),
            display.replace(" ", "").lower(),
            display.lower(),
            key,
            key.replace("_", " "),
            key.replace("_", " ").lower(),
        }
        for v in variants:
            name_to_item[v] = ii

    all_keys = list(name_to_item.keys())
    return name_to_item, all_keys


def _normalize(s: str) -> str:
    return s.strip().lower().replace("'", "")


def detect_hero(question: str) -> Optional[HeroInfo]:
    question_norm = _normalize(question)
    hero_map, hero_keys = _hero_name_maps()

    for key in hero_keys:
        if key and key in question_norm:
            return hero_map[key]

    close = difflib.get_close_matches(question_norm, hero_keys, n=1, cutoff=0.8)
    if close:
        return hero_map[close[0]]
    return None


def detect_item(question: str) -> Optional[ItemInfo]:
    question_norm = _normalize(question)
    item_map, item_keys = _item_name_maps()

    for key in item_keys:
        if key and key in question_norm:
            return item_map[key]

    close = difflib.get_close_matches(question_norm, item_keys, n=1, cutoff=0.8)
    if close:
        return item_map[close[0]]
    return None


def classify_question(
    question: str,
    hero: Optional[HeroInfo],
    item: Optional[ItemInfo],
) -> QuestionType:
    q = question.lower()

    counter_words = ["counter", "good against", "beat", "strong against", "deal with"]
    build_words = ["build", "items for", "what should i buy", "itemization", "best items"]
    explain_words = ["what does", "explain", "how does", "description", "what is "]
    strategy_words = ["how to play against", "tips for", "how do i play against"]

    if hero and any(w in q for w in counter_words):
        return QuestionType.HERO_COUNTER

    if hero and any(w in q for w in build_words):
        return QuestionType.HERO_BUILD

    if item and any(w in q for w in counter_words):
        return QuestionType.ITEM_COUNTER

    if item and any(w in q for w in explain_words):
        return QuestionType.ITEM_EXPLANATION

    if hero and any(w in q for w in strategy_words):
        return QuestionType.GAMEPLAY_STRATEGY

    if hero:
        return QuestionType.GAMEPLAY_STRATEGY
    if item:
        return QuestionType.ITEM_EXPLANATION

    return QuestionType.GAMEPLAY_STRATEGY


def _hero_id_to_name_map() -> Dict[int, str]:
    return {h["id"]: h["localized_name"] for h in get_heroes()}


def _top_matchup_counters(target_hero: HeroInfo, top_n: int = 5) -> List[Tuple[HeroInfo, float]]:
    matchups = get_hero_matchups(target_hero.id)
    id_to_name = _hero_id_to_name_map()

    results: List[Tuple[int, float, int]] = []
    for m in matchups:
        games = m.get("games_played", 0) or 0
        wins = m.get("wins", 0) or 0
        if games <= 0:
            continue
        if games < 50:
            continue
        wr = wins / games
        results.append((m["hero_id"], wr, games))

    results.sort(key=lambda x: x[1], reverse=True)
    top = results[:top_n]

    hero_map, _ = _hero_name_maps()
    loc_to_hero = {h.localized_name: h for h in hero_map.values()}

    counters: List[Tuple[HeroInfo, float]] = []
    for hid, wr, _ in top:
        loc_name = id_to_name.get(hid)
        if not loc_name:
            continue
        hi = loc_to_hero.get(loc_name)
        if hi:
            counters.append((hi, wr))
    return counters


def _describe_hero_as_counter(counter: HeroInfo, target: HeroInfo) -> str:
    t = target.localized_name
    c = counter.localized_name

    if c in {"Axe", "Centaur Warrunner", "Mars", "Underlord", "Tidehunter"}:
        return f"{c} – Durable initiator who forces {t} to fight on his terms and punishes overextension."
    if c in {"Lion", "Shadow Shaman", "Disruptor", "Rubick"}:
        return f"{c} – Strong disables that lock down {t} before they can use mobility or defensive tools."
    if c in {"Viper", "Venomancer", "Necrophos"}:
        return f"{c} – Damage over time and sustain that make drawn-out fights bad for {t}."
    if c in {"Timbersaw", "Huskar", "Outworld Destroyer", "Lina", "Zeus"}:
        return f"{c} – Heavy magical or pure burst that punishes {t} even through armor or evasion."
    return f"{c} – Naturally matches up well into {t} due to stat profile, spell kit, or lane pressure."


def generate_counter_response(hero: HeroInfo) -> str:
    counters = _top_matchup_counters(hero)
    if not counters:
        explanation = (
            f"{hero.localized_name} has no clear statistical counters from the available matchup data."
        )
        bullets = [
            "Consider drafting heroes with **reliable disables** or **burst damage**.",
            "Look for lane matchups where you can **pressure early** before core items.",
            "Prioritize items that **limit their mobility or survivability**.",
        ]
        tip = (
            "Think about what makes this hero strong (mobility, damage, or sustain) and draft tools that directly undermine that strength."
        )
    else:
        explanation = (
            f"{hero.localized_name} is vulnerable to heroes that can disrupt their game plan or withstand their key damage window."
        )

        bullets = []
        for c, wr in counters:
            desc = _describe_hero_as_counter(c, hero)
            bullets.append(f"{desc} (win rate vs {hero.localized_name}: ~{wr*100:.1f}%).")

        tip = (
            "When drafting against this hero, prioritize lineups that either **survive their first big timing** or **catch them before they scale**."
        )

    lines = []
    lines.append(explanation)
    lines.append("")
    lines.append("Key counters:")
    for b in bullets:
        lines.append(f"- {b}")
    lines.append("")
    lines.append(f"**Strategy Tip**: {tip}")
    return "\n".join(lines)


def _aggregate_popular_items(item_popularity: dict, top_n: int = 6) -> List[Tuple[str, int]]:
    phases = [
        "start_game_items",
        "early_game_items",
        "mid_game_items",
        "late_game_items",
    ]
    counts: Dict[str, int] = {}

    for phase in phases:
        items = item_popularity.get(phase, {})
        for k, v in items.items():
            counts[k] = counts.get(k, 0) + (v or 0)

    sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return sorted_items[:top_n]


def _format_item_name(item_key: str) -> str:
    items = get_items()
    rec = items.get(item_key, {})
    return rec.get("dname") or item_key.replace("_", " ").title()


def generate_build_response(hero: HeroInfo) -> str:
    data = get_hero_item_popularity(hero.id)
    core_items = _aggregate_popular_items(data, top_n=7)

    explanation = (
        f"{hero.localized_name} typically buys items that enhance their natural strengths and timing windows."
    )

    bullets = []
    for key, _count in core_items:
        name = _format_item_name(key)
        bullets.append(f"{name} – Commonly picked to reinforce {hero.localized_name}'s preferred playstyle.")

    tip = (
        f"Identify whether you should be the **initiator**, **damage dealer**, or **utility core** on {hero.localized_name}, "
        "and prioritize items that help you reliably perform that job in fights."
    )

    lines = []
    lines.append(explanation)
    lines.append("")
    lines.append("Popular core items include:")
    for b in bullets:
        lines.append(f"- {b}")
    lines.append("")
    lines.append(f"**Strategy Tip**: {tip}")
    return "\n".join(lines)


def _describe_item(item: ItemInfo) -> Tuple[str, List[str]]:
    raw = item.raw
    dname = item.display_name
    desc = raw.get("desc") or ""
    notes = raw.get("notes") or ""
    cost = raw.get("cost")

    explanation = f"{dname} is an item that {desc.strip()}".strip()
    if cost:
        explanation += f" It costs {cost} gold."

    bullets = []

    if "ethereal" in desc.lower() or "ethereal" in notes.lower():
        bullets.append("Turns the target ethereal, **blocking physical damage** but increasing **magical damage taken**.")
    if "spell immunity" in desc.lower() or "spell immunity" in notes.lower():
        bullets.append("Grants **spell immunity**, blocking most magical damage and many disables.")
    if "invisible" in desc.lower() or "invisibility" in desc.lower() or "invisible" in notes.lower():
        bullets.append("Provides **invisibility**, making the user hard to target without true sight.")
    if "blink" in item.key or "blink" in desc.lower():
        bullets.append("Offers **mobility/blink**, enabling quick initiation or escape.")
    if not bullets:
        bullets.append("Provides a mix of stats and active/passive effects that support its intended role.")

    return explanation, bullets


def _infer_item_counters(item: ItemInfo) -> List[str]:
    desc = (item.raw.get("desc") or "").lower()
    notes = (item.raw.get("notes") or "").lower()
    text = desc + " " + notes

    counters: List[str] = []

    if "ethereal" in text:
        counters.append("Use **strong magical burst** while the target is ethereal to punish the increased magic damage taken.")
        counters.append("Pick heroes or items with **dispels** (e.g., purge effects) to remove the ethereal state when it is defensive.")
    if "spell immunity" in text or "bkb" in item.key:
        counters.append("Draft heroes whose **ults pierce spell immunity** or rely on **right-click damage** instead of disables.")
        counters.append("Kite the target during spell immunity and **re-engage after the duration ends**.")
    if "invisible" in text or "invisibility" in text:
        counters.append("Buy **true sight** items (Sentry Wards, Dust, Gem, or items that reveal invisibility).")
        counters.append("Place **deep vision** to catch the user before they can disengage.")
    if "lifesteal" in text or "life steal" in text:
        counters.append("Apply **heal reduction** or **burst damage** that kills through lifesteal.")
    if "evasion" in text:
        counters.append("Purchase **True Strike** or accuracy items to negate evasion.")
    if not counters:
        counters.append("Look for **dispels, silence, or hard disables** to prevent the user from leveraging this item at key moments.")
        counters.append("Adapt your item build to **bypass or outscale** the primary strength this item provides.")

    return counters


def generate_item_response(item: ItemInfo, explain_only: bool = False) -> str:
    explanation, mechanics_bullets = _describe_item(item)

    if explain_only:
        tip = (
            f"Think about whether {item.display_name} helps you **survive**, **deal damage**, or **control fights**, "
            "and purchase it when it clearly advances your game plan."
        )
        lines = []
        lines.append(explanation)
        lines.append("")
        lines.append("Key mechanics:")
        for b in mechanics_bullets:
            lines.append(f"- {b}")
        lines.append("")
        lines.append(f"**Strategy Tip**: {tip}")
        return "\n".join(lines)

    counter_bullets = _infer_item_counters(item)
    tip = (
        f"When playing against {item.display_name}, track its **cooldown and timing** and "
        "force fights when the item is down or poorly positioned."
    )

    lines = []
    lines.append(f"{item.display_name} can be very impactful if left unchecked.")
    lines.append("")
    lines.append("Effective ways to counter this item:")
    for b in counter_bullets:
        lines.append(f"- {b}")
    lines.append("")
    lines.append("Understanding its mechanics:")
    for b in mechanics_bullets:
        lines.append(f"- {b}")
    lines.append("")
    lines.append(f"**Strategy Tip**: {tip}")
    return "\n".join(lines)


def _generic_hero_strategy(hero: Optional[HeroInfo], vs: bool) -> str:
    if not hero:
        explanation = "General gameplay decisions in Dota 2 revolve around timings, map control, and information."
        bullets = [
            "Play around **power spikes** (levels, big items, Roshan) instead of taking constant skirmishes.",
            "Use **vision and smoke** to create favorable fights rather than walking blindly into dark areas.",
            "Align your lineup around **clear win conditions** (tower pressure, teamfight, pickoff, or scaling).",
        ]
        tip = (
            "Before each game, define your **primary win condition** and make sure every rotation and item choice supports it."
        )
    else:
        name = hero.localized_name
        if vs:
            explanation = f"Playing against {name} is about denying their ideal conditions and forcing awkward fights."
            bullets = [
                f"Identify {name}'s **strongest timing** (key level or item) and avoid fair 5v5 fights during that power spike.",
                f"Use **smoke ganks** and vision to catch {name} before or after big cooldowns.",
                f"Draft tools that either **kite** {name} or **burst them before they can fully commit**.",
            ]
            tip = (
                f"Ask: 'What does {name} need to win fights?' Then build heroes and items that remove that requirement "
                "(e.g., vision, mobility, or sustain)."
            )
        else:
            explanation = f"Playing {name} well is about understanding your timing and how you enter fights."
            bullets = [
                "Clarify whether you are the **frontliner**, **damage dealer**, or **utility hero** for your lineup.",
                "Play for your first big **item/level timing**, and communicate with your team to fight around it.",
                "Avoid random deaths before objective fights; keep **lanes pushed** and **vision up** before you commit.",
            ]
            tip = (
                f"Review each fight and ask whether {name} started the fight on **their terms**—good positioning, vision, "
                "and spells/items ready."
            )

    lines = []
    lines.append(explanation)
    lines.append("")
    lines.append("Key points:")
    for b in bullets:
        lines.append(f"- {b}")
    lines.append("")
    lines.append(f"**Strategy Tip**: {tip}")
    return "\n".join(lines)


def generate_strategy_response(hero: Optional[HeroInfo], question: str) -> str:
    vs = "against" in question.lower()
    return _generic_hero_strategy(hero, vs=vs)


def answer_question(question: str) -> str:
    try:
        hero = detect_hero(question)
        item = detect_item(question)
    except OpenDotaError:
        return (
            "I attempted to retrieve data from the OpenDota API but the service is currently unavailable. "
            "Please try again shortly."
        )

    qtype = classify_question(question, hero, item)

    try:
        if qtype == QuestionType.HERO_COUNTER:
            if not hero:
                return "I couldn't confidently detect the hero you're asking about. Please rephrase with the hero's full name."
            return generate_counter_response(hero)

        if qtype == QuestionType.HERO_BUILD:
            if not hero:
                return "I couldn't confidently detect the hero you're asking about. Please rephrase with the hero's full name."
            return generate_build_response(hero)

        if qtype == QuestionType.ITEM_EXPLANATION:
            if not item:
                return "I couldn't confidently detect the item you're asking about. Please rephrase with the item's full name."
            return generate_item_response(item, explain_only=True)

        if qtype == QuestionType.ITEM_COUNTER:
            if not item:
                return "I couldn't confidently detect the item you're asking how to counter. Please rephrase with the item's full name."
            return generate_item_response(item, explain_only=False)

        return generate_strategy_response(hero, question)

    except OpenDotaError:
        return (
            "I attempted to retrieve data from the OpenDota API but the service is currently unavailable. "
            "Please try again shortly."
        )

