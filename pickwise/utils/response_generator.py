from functools import lru_cache
from typing import List, Tuple, Optional

from .entity_detection import HeroEntity, ItemEntity
from .opendota_client import (
    OpenDotaError,
    get_heroes,
    get_items,
    get_hero_matchups,
    get_hero_item_popularity,
)


def generate_self_intro_response() -> str:
    """
    Friendly self-introduction for PickWise. Used when the user asks who the bot is
    or what it does. Conversational and helpful, explains purpose and example questions.
    """
    return (
        "Hi! I'm PickWise — an AI strategy assistant built to help you make better decisions in Dota 2.\n\n"
        "I use live data from the OpenDota API to give you accurate, up-to-date advice on:\n\n"
        "• Hero counters — which heroes are strong against a given pick (for example, questions like “Who counters Phantom Assassin?”)\n"
        "• Item builds — popular and effective itemization for a hero (for example, “Best items for Axe”)\n"
        "• Item counters — how to play around or counter specific items (for example, “How do I counter Black King Bar?”)\n"
        "• Gameplay strategy — tips for playing with or against certain heroes and general match strategy\n\n"
        "You can ask me things like “What counters Sniper?”, “What should I build on Juggernaut?”, or “What does Shiva's Guard do?” — "
        "I'll give you clear, actionable answers with bullet points and short strategy tips.\n\n"
        "Go ahead and ask me anything about Dota 2 strategy; I'm here to help."
    )


def _hero_id_to_entity() -> dict:
    mapping = {}
    for h in get_heroes():
        mapping[h["id"]] = HeroEntity(
            id=h["id"],
            name=h["name"],
            localized_name=h["localized_name"],
        )
    return mapping


def _compute_top_counters(target: HeroEntity, top_n: int = 5) -> List[Tuple[HeroEntity, float]]:
    """
    Use OpenDota matchup data to find heroes with the highest win rate
    against the target hero.
    """
    matchups = get_hero_matchups(target.id)
    id_map = _hero_id_to_entity()

    rows: List[Tuple[HeroEntity, float, int]] = []
    for m in matchups:
        games = m.get("games_played", 0) or 0
        wins = m.get("wins", 0) or 0
        if games < 50:
            continue
        wr = wins / games
        hero = id_map.get(m["hero_id"])
        if hero:
            rows.append((hero, wr, games))

    rows.sort(key=lambda x: x[1], reverse=True)
    return [(h, wr) for (h, wr, _g) in rows[:top_n]]


def _format_counter_hero_reason(counter: HeroEntity, target: HeroEntity) -> str:
    """
    Heuristic explanation for why a given hero counters another.
    """
    c = counter.localized_name
    t = target.localized_name

    if c in {"Spirit Breaker", "Storm Spirit", "Phantom Assassin", "Slark"}:
        return f"{c} – excels at quickly jumping onto {t}, denying them the safe distance they need."
    if c in {"Axe", "Centaur Warrunner", "Mars", "Underlord", "Tidehunter"}:
        return f"{c} – durable initiator that forces {t} into bad fights and punishes overextension."
    if c in {"Lion", "Shadow Shaman", "Disruptor", "Silencer"}:
        return f"{c} – strong disables or silences that prevent {t} from using key abilities."
    return f"{c} – matches up well into {t} based on stats, spell kit, or lane pressure."


def generate_hero_counters_response(hero: HeroEntity) -> str:
    try:
        counters = _compute_top_counters(hero)
    except OpenDotaError:
        return (
            "I tried to pull live matchup data from OpenDota but the service is unavailable right now. "
            "Please try again in a little while."
        )

    intro = (
        f"{hero.localized_name} is significantly easier to manage when you select heroes that interrupt their preferred engagements "
        f"or outlast their primary damage window."
    )

    lines: List[str] = [intro, "", "Effective counters include:"]
    if not counters:
        lines.append("• Heroes with reliable disables, burst damage, or strong lane pressure.")
    else:
        for h, wr in counters:
            reason = _format_counter_hero_reason(h, hero)
            lines.append(f"• {reason} (win rate vs {hero.localized_name}: ~{wr*100:.1f}%).")

    lines.append("")
    lines.append(
        "These picks either survive the target hero's first big timing or force them into fights they do not want to take."
    )
    return _ensure_readable_only("\n".join(lines))


# --- Items to counter a specific hero (e.g. "best items to counter PA") ---

# Curated counter items per hero: (item_display_name, short_reason).
# Optional "situational" and "tips" for that hero.
_HERO_COUNTER_ITEMS_CURATED: dict = {
    "phantom assassin": {
        "items": [
            ("Monkey King Bar (MKB)", "Provides true strike to bypass her evasion."),
            ("Silver Edge", "Breaks Blur and other passives; provides burst damage."),
            ("Bloodthorn", "Silences PA and ensures critical hits land."),
            ("Assault Cuirass", "Reduces her armor and helps your team deal more physical damage."),
            ("Heaven's Halberd", "Disarms PA during fights to reduce her damage output."),
        ],
        "situational": "Ghost Scepter on supports when PA is diving you; Blade Mail can punish her burst if you are tanky.",
        "tips": [
            "Focus on disabling her in teamfights before she can blink and initiate.",
            "Combine physical damage items to take advantage of her low armor in the early–mid game.",
        ],
    },
    "anti-mage": {
        "items": [
            ("Abyssal Blade", "Lockdown through Blink; prevents escape."),
            ("Orchid Malevolence / Bloodthorn", "Burns mana and silences so he cannot Blink away."),
            ("Scythe of Vyse", "Instant hex to lock him down."),
            ("Bloodthorn", "Silence and true strike against his evasion talent."),
            ("Rod of Atos", "Root prevents Blink."),
        ],
        "situational": "If AM is split-pushing, consider Maelstrom or Battle Fury for wave clear; Nullifier later to remove his Manta/BKB.",
        "tips": [
            "Chain disables so he cannot Blink; burst him before he can react.",
            "Control the map so he cannot freely farm; fight before he reaches his late-game timing.",
        ],
    },
    "bristleback": {
        "items": [
            ("Silver Edge", "Breaks Bristleback passive, drastically reducing his damage reduction."),
            ("Spirit Vessel", "Reduces his regeneration and punishes his high HP pool."),
            ("Orchid Malevolence / Bloodthorn", "Silence stops him from stacking Quill Spray."),
            ("Shiva's Guard", "Attack speed slow and armor; reduces his physical output."),
            ("Eye of Skadi", "Slows his movement and reduces regen."),
        ],
        "situational": "Magic burst before he gets too tanky; Blade Mail can punish if your team has high damage.",
        "tips": [
            "Kite him and avoid facing him head-on so Bristleback passive does not trigger.",
            "Kill him in one chain of disables; prolonged fights favor him.",
        ],
    },
    "sniper": {
        "items": [
            ("Blink Dagger", "Close the gap to get on top of him."),
            ("Shadow Blade / Silver Edge", "Initiate from invisibility so he cannot kite."),
            ("Force Staff", "Reposition yourself or allies out of Shrapnel and Assassinate range."),
            ("Black King Bar", "Walk through his damage to reach him."),
            ("Hurricane Pike", "Range and escape to duel or disengage."),
        ],
        "situational": "Smoke and vision to catch him; Heaven's Halberd if he is the main right-click threat.",
        "tips": [
            "Jump him with gap-close or invisibility; he is weak when closed on.",
            "Control high ground and vision so he cannot sit safely in the back.",
        ],
    },
    "phantom lancer": {
        "items": [
            ("Maelstrom / Mjollnir", "Clears illusions quickly with chain lightning."),
            ("Battle Fury", "Cleave and regen; helps clear illusions and sustain."),
            ("Radiance", "Burn damage reveals real hero and clears illusions."),
            ("Shiva's Guard", "AOE slow and armor; helps identify the real PL."),
            ("Gem of True Sight", "Reveals the real PL if he uses Doppelganger to escape."),
        ],
        "situational": "Spirit Vessel and Silver Edge against his regen and passives; Gem for his invisibility.",
        "tips": [
            "Prioritize items that hit multiple units to clear illusions and find the real PL.",
            "Do not let the game go late without illusion-clear; he outscales if you cannot identify him.",
        ],
    },
    "templar assassin": {
        "items": [
            ("Gem of True Sight / Dust", "Reveal her in Refraction meld."),
            ("Monkey King Bar", "True strike against Refraction block."),
            ("Force Staff", "Reposition out of Psi Blades and Trap slow."),
            ("Orchid Malevolence / Bloodthorn", "Silence prevents Blink and burst."),
            ("Scythe of Vyse", "Hex to lock her down."),
        ],
        "situational": "Magic burst before Refraction; armor reduction (AC, Desolator) to break through her defenses.",
        "tips": [
            "Reveal her before she can meld-strike; burst her in one disable chain.",
            "Respect her Trap slow and Psi Blades range; do not clump in lanes.",
        ],
    },
    "riki": {
        "items": [
            ("Gem of True Sight", "Reveals him in permanent invisibility."),
            ("Dust of Appearance", "Reveal and slow so he cannot escape."),
            ("Sentry Wards", "Vision to see and kill him around the map."),
            ("Force Staff", "Escape his Smoke and backstab burst."),
            ("Ghost Scepter", "Avoid physical damage from Backstab."),
        ],
        "situational": "BKB to walk out of Smoke; instant disables (Hex, Abyssal) so he cannot blink away.",
        "tips": [
            "Invest in true sight early; one Gem or Sentries can shut down his pickoffs.",
            "Stay grouped so he cannot isolate a target; punish him when revealed.",
        ],
    },
    "faceless void": {
        "items": [
            ("Linken's Sphere", "Blocks Chronosphere or initiation on one target."),
            ("Force Staff", "Reposition allies out of Chrono or yourself to safety."),
            ("Black King Bar", "If you are inside Chrono, BKB lets you act (depending on patch)."),
            ("Aeon Disk", "Prevents being burst inside Chrono."),
            ("Scythe of Vyse", "Hex him before or after Chrono to lock him down."),
        ],
        "situational": "Dispel for Time Dilation; armor and HP to survive Chrono if you are caught.",
        "tips": [
            "Spread out so Chrono cannot catch multiple heroes; save disables for when Chrono ends.",
            "Fight when Chronosphere is on cooldown; track his ultimate timing.",
        ],
    },
    "storm spirit": {
        "items": [
            ("Orchid Malevolence / Bloodthorn", "Silence prevents Ball Lightning escape."),
            ("Scythe of Vyse", "Instant hex to stop his zip."),
            ("Rod of Atos", "Root stops Ball Lightning."),
            ("Abyssal Blade", "Stun through his mobility."),
            ("Ancient Seal / Silencer", "Not an item but draft silences to lock him down."),
        ],
        "situational": "Magic resistance (Pipe, BKB) to survive his burst; mana burn to limit his zip.",
        "tips": [
            "Save instant disables for when he commits; do not let him zip in and out for free.",
            "Pressure the map when his Ball is on cooldown or he is low on mana.",
        ],
    },
    "juggernaut": {
        "items": [
            ("Ghost Scepter", "Omnislash does not hit ethereal units."),
            ("Eul's Scepter", "Cyclone yourself or him to dodge or interrupt Omnislash."),
            ("Force Staff", "Reposition out of Blade Fury or Omnislash range."),
            ("Scythe of Vyse", "Hex him during or before Omnislash."),
            ("Heaven's Halberd", "Disarm reduces his right-click after spin."),
        ],
        "situational": "Blade Mail can punish Omnislash if you are tanky; armor (AC, Shiva's) to reduce his physical damage.",
        "tips": [
            "Disable or ghost through Omnislash; do not let him get free kills with spin + slash.",
            "Fight when Blade Fury or Omnislash is on cooldown.",
        ],
    },
    "axe": {
        "items": [
            ("Black King Bar", "Prevents Culling Blade and reduces Call damage if spell immunity blocks the execute."),
            ("Force Staff", "Reposition out of Berserker's Call or to save a called ally."),
            ("Glimmer Cape", "Save allies from Culling Blade with invisibility and magic resist."),
            ("Ghost Scepter", "Call does not prevent ethereal; can avoid some follow-up damage."),
            ("Linken's Sphere", "Blocks one Call or Culling Blade on the carrier."),
        ],
        "situational": "Armor and HP so you are not an easy Culling Blade target; kite him when Call is down.",
        "tips": [
            "Do not clump so Call hits multiple heroes; save instant saves for Culling Blade targets.",
            "Kite Axe and fight when Berserker's Call is on cooldown.",
        ],
    },
    "pudge": {
        "items": [
            ("Force Staff", "Reposition out of Dismember or to escape after Hook."),
            ("Linken's Sphere", "Blocks Hook on one target."),
            ("Black King Bar", "Prevents Dismember and Rot slow."),
            ("Glimmer Cape", "Save allies from Dismember or Hook follow-up."),
            ("Eul's Scepter", "Cyclone to dodge Hook or interrupt Dismember."),
        ],
        "situational": "Vision to spot Hook; mobility so you are not an easy Hook target.",
        "tips": [
            "Stay behind creeps to block Hook; save disables for when he Hooks an ally.",
            "Do not stand in fog or predictable spots where he can land Hooks.",
        ],
    },
    "windranger": {
        "items": [
            ("Monkey King Bar", "True strike against Windrun evasion."),
            ("Scythe of Vyse", "Hex to lock her down through Windrun."),
            ("Orchid Malevolence / Bloodthorn", "Silence stops Shackleshot and escape."),
            ("Blade Mail", "Punishes Focus Fire if she commits on you."),
            ("Heaven's Halberd", "Disarm during Focus Fire."),
        ],
        "situational": "Magic burst before Windrun; root or hex so she cannot escape.",
        "tips": [
            "Lock her down before she can Windrun and Focus Fire; burst her in one disable chain.",
            "Do not let her get free Shackleshots; position so she cannot double-stun.",
        ],
    },
    "ursa": {
        "items": [
            ("Ghost Scepter", "Fury Swipes do not apply to ethereal units."),
            ("Force Staff", "Reposition out of melee range and Overpower."),
            ("Eul's Scepter", "Cyclone to dodge Enrage or escape."),
            ("Heaven's Halberd", "Disarm him during Enrage."),
            ("Blade Mail", "Punishes his high physical damage if you are tanky."),
        ],
        "situational": "Kite him; do not let him get multiple hits; armor and HP for when you are caught.",
        "tips": [
            "Do not stand and trade hits; kite and disable so he cannot stack Fury Swipes.",
            "Fight when Enrage is on cooldown; burst him before he can Enrage.",
        ],
    },
    "lifestealer": {
        "items": [
            ("Spirit Vessel", "Reduces his regeneration and Rage healing."),
            ("Orchid Malevolence / Bloodthorn", "Silence prevents Rage and Open Wounds."),
            ("Scythe of Vyse", "Hex locks him down."),
            ("Heaven's Halberd", "Disarm reduces his right-click."),
            ("Shiva's Guard", "Attack speed slow and armor."),
        ],
        "situational": "Break (Silver Edge) to reduce Feast; kite him when Rage is down.",
        "tips": [
            "Do not let him free-hit; disable and burst before he sustains through Rage.",
            "Avoid letting him Infest a key target; control the Infest carrier.",
        ],
    },
    "bloodseeker": {
        "items": [
            ("Force Staff", "Reposition out of Rupture or to break Thirst vision."),
            ("Eul's Scepter", "Cyclone to purge Rupture or dodge Blood Rite."),
            ("Black King Bar", "Walk through Rupture and Blood Rite."),
            ("Ghost Scepter", "Rupture damage is partially mitigated when ethereal; avoid right-click."),
            ("Linken's Sphere", "Blocks Rupture on one target."),
        ],
        "situational": "Stay at high HP so Thirst does not give him bonus; TP scroll to base when Ruptured if safe.",
        "tips": [
            "Do not move when Ruptured if it will kill you; Force Staff or stand still and fight.",
            "Deny him Thirst by staying healthy; burst him before he heals from Blood Rite.",
        ],
    },
    "slark": {
        "items": [
            ("Gem of True Sight", "Reveals him in Shadow Dance."),
            ("Dust of Appearance", "Reveal and slow so he cannot purge and escape."),
            ("Scythe of Vyse", "Instant hex; he cannot purge Hex with Dark Pact."),
            ("Orchid Malevolence / Bloodthorn", "Silence prevents Pounce and Shadow Dance escape."),
            ("Spirit Vessel", "Reduces his regeneration in and out of Shadow Dance."),
        ],
        "situational": "AOE disables so he cannot dodge with Dark Pact; burst him before he can steal stats.",
        "tips": [
            "Reveal him in fights so Shadow Dance does not make him untargetable.",
            "Do not let him get repeated Essence Shift stacks; lock him down and kill him.",
        ],
    },
    "medusa": {
        "items": [
            ("Spirit Vessel", "Reduces her mana shield and regeneration."),
            ("Diffusal Blade", "Burns mana to break Mana Shield."),
            ("Eye of Skadi", "Slows and prevents mana regen."),
            ("Abyssal Blade", "Lockdown through Stone Gaze."),
            ("Monkey King Bar", "Burst through evasion if she has Butterfly."),
        ],
        "situational": "Magic burst before she is too tanky; Nullifier to remove her defensive items.",
        "tips": [
            "Burn her mana to break Mana Shield; do not look at Stone Gaze if you cannot kill her.",
            "Focus her in teamfights before she gets multiple items; she scales very hard.",
        ],
    },
    "invoker": {
        "items": [
            ("Orchid Malevolence / Bloodthorn", "Silence prevents spell combos and Ghost Walk."),
            ("Scythe of Vyse", "Hex to lock him down."),
            ("Black King Bar", "Walk through his magic damage and Tornado EMP."),
            ("Rod of Atos", "Root prevents movement and some invokes."),
            ("Nullifier", "Dispels Ghost Walk and defensive items."),
        ],
        "situational": "Gap close (Blink, Force) to cancel his long cast times; vision to catch him.",
        "tips": [
            "Jump him before he can set up combos; silence or hex is critical.",
            "Track his Invoke cooldown and key spells (Tornado, EMP, Cataclysm) so you can play around them.",
        ],
    },
    "morphling": {
        "items": [
            ("Spirit Vessel", "Reduces his regeneration and Morph sustain."),
            ("Orchid Malevolence / Bloodthorn", "Silence prevents Waveform and Morph."),
            ("Scythe of Vyse", "Hex locks him down so he cannot Morph or replicate."),
            ("Ancient Seal", "Not an item but silences are very strong."),
            ("Eye of Skadi", "Slows and prevents full Morph toggle."),
        ],
        "situational": "Burst him in one stun so he cannot Morph strength; mana burn to limit his waveform.",
        "tips": [
            "Chain disables so he cannot Morph to strength; kill him in one window.",
            "Control the Replicate illusion and do not let him escape with it.",
        ],
    },
    "weaver": {
        "items": [
            ("Gem of True Sight", "Reveals him in Shukuchi."),
            ("Dust of Appearance", "Reveal and slow so he cannot escape."),
            ("Radiance", "Burn reveals him in invisibility."),
            ("Spirit Vessel", "Reduces regeneration and punishes Time Lapse."),
            ("Scythe of Vyse", "Hex so he cannot Time Lapse or Shukuchi."),
        ],
        "situational": "Instant disables (Hex, Abyssal) so he cannot Time Lapse; AOE to hit him in Shukuchi.",
        "tips": [
            "Reveal him so Shukuchi does not give free escape; burst him before Time Lapse.",
            "Do not let him get free Geminate hits; armor and positioning matter.",
        ],
    },
    "broodmother": {
        "items": [
            ("Gem of True Sight", "Reveals her in webs and invisibility."),
            ("Battle Fury / Maelstrom", "Clears spiderlings and reduces her push."),
            ("Radiance", "Burn clears spiders and reveals her."),
            ("Shiva's Guard", "AOE slow and armor against spiders."),
            ("Force Staff", "Escape her slow and spider burst."),
        ],
        "situational": "AOE clears spiders; do not let her take over the map with webs.",
        "tips": [
            "Clear her spiderlings so she loses damage and gold; control her web areas with vision.",
            "Fight her when her spiders are dead; do not feed the spiders.",
        ],
    },
    "necrophos": {
        "items": [
            ("Spirit Vessel", "Reduces his regeneration and counters Heartstopper."),
            ("Glimmer Cape", "Save allies from Reaper's Scythe with magic resist."),
            ("Pipe of Insight", "Reduces Death Pulse and ultimate magic damage."),
            ("Black King Bar", "Reduces magic damage from his spells."),
            ("Linken's Sphere", "Blocks Reaper's Scythe on one target."),
        ],
        "situational": "Stay above Reaper's Scythe threshold; burst him before he can heal from Death Pulse.",
        "tips": [
            "Do not sit in Heartstopper Aura; save instant saves for Reaper's Scythe.",
            "Kill him first in teamfights so he cannot spam Death Pulse and reset with Scythe.",
        ],
    },
    "tinker": {
        "items": [
            ("Blink Dagger", "Close the gap to cancel his Rearm and kill him."),
            ("Orchid Malevolence / Bloodthorn", "Silence prevents Rearm and Laser Rockets."),
            ("Scythe of Vyse", "Hex to lock him down."),
            ("Black King Bar", "Walk through his magic burst."),
            ("Abyssal Blade", "Stun to cancel Rearm."),
        ],
        "situational": "Vision to catch him in the jungle; burst him before he can Rearm and TP.",
        "tips": [
            "Jump him when he is channeling Rearm; do not let him get free Laser and Rockets from fog.",
            "Control the map so he cannot farm multiple lanes and jungle; fight when he is not at his strongest.",
        ],
    },
    "drow ranger": {
        "items": [
            ("Blink Dagger", "Close the gap so she cannot kite."),
            ("Shadow Blade / Silver Edge", "Initiate from invisibility."),
            ("Black King Bar", "Walk through Gust and her damage."),
            ("Heaven's Halberd", "Disarm to reduce her damage output."),
            ("Monkey King Bar", "True strike if she has evasion talent or Butterfly."),
        ],
        "situational": "Gap close and lockdown; she is weak when closed on.",
        "tips": [
            "Jump her before she can Gust and kite; do not let her free-hit from range.",
            "Break her passive (Silver Edge) if she has Marksmanship; control high ground.",
        ],
    },
    "earthshaker": {
        "items": [
            ("Black King Bar", "Prevents Fissure and Echo Slam stuns."),
            ("Force Staff", "Reposition out of Fissure or to escape after Blink Echo."),
            ("Linken's Sphere", "Blocks Fissure on one target."),
            ("Glimmer Cape", "Save allies from Echo Slam burst."),
            ("Eul's Scepter", "Cyclone to dodge Fissure or Enchant Totem."),
        ],
        "situational": "Do not clump for Echo Slam; spread and save for his initiation.",
        "tips": [
            "Spread out so Echo Slam does not hit multiple heroes; save disables for after his Blink.",
            "Fight when Fissure is on cooldown; ward to see his Blink initiation.",
        ],
    },
    "zeus": {
        "items": [
            ("Pipe of Insight", "Reduces his magic burst."),
            ("Black King Bar", "Walk through Thundergod's Wrath and Arc Lightning."),
            ("Glimmer Cape", "Magic resist for allies."),
            ("Hood of Defiance", "Early magic resistance."),
            ("Rubick / Lotus", "Not items but reflect or absorb his damage."),
        ],
        "situational": "Gap close to kill him; he is fragile when closed on.",
        "tips": [
            "Invest in magic resistance early; do not let him get free vision and damage with Lightning Bolt.",
            "Jump him in fights; he has no escape.",
        ],
    },
}


def _get_hero_roles(hero: HeroEntity) -> List[str]:
    """Return list of role strings for the hero from OpenDota."""
    try:
        for h in get_heroes():
            if h.get("id") == hero.id:
                return list(h.get("roles") or [])
    except Exception:
        pass
    return []


def _get_counter_items_for_hero(hero: HeroEntity) -> Tuple[List[Tuple[str, str]], str, List[str]]:
    """
    Return (list of (item_name, reason), situational_notes, strategy_tips) for the hero.
    Uses curated data when available; otherwise builds from roles.
    """
    name_lower = hero.localized_name.lower().strip()
    curated = _HERO_COUNTER_ITEMS_CURATED.get(name_lower)
    if curated:
        items = curated.get("items") or []
        situational = curated.get("situational") or ""
        tips = curated.get("tips") or []
        return (items, situational, tips)

    # Role-based fallback: suggest items by common threats
    roles = _get_hero_roles(hero)
    items: List[Tuple[str, str]] = []
    name = hero.localized_name

    if "Carry" in roles or "Nuker" in roles:
        items.append(("Black King Bar", "Reduces magic damage and prevents disables so you can fight or escape."))
    if "Carry" in roles:
        items.append(("Heaven's Halberd", "Disarms the carry to reduce their right-click damage."))
        items.append(("Ghost Scepter", "Avoids physical damage when the carry is focusing you."))
    if "Durable" in roles or "Initiator" in roles:
        items.append(("Spirit Vessel", "Reduces regeneration and punishes high-HP heroes."))
        items.append(("Silver Edge", "Break reduces passive damage reduction and other strong passives."))
    if "Escape" in roles or "Nuker" in roles:
        items.append(("Orchid Malevolence / Bloodthorn", "Silence prevents escape and key spell combos."))
        items.append(("Scythe of Vyse", "Hex to lock down mobile or spell-reliant heroes."))
    if "Disabler" in roles:
        items.append(("Black King Bar", "Lets you act through disables when you need to commit."))
        items.append(("Linken's Sphere", "Blocks one targeted disable on the carrier."))
    if "Pusher" in roles:
        items.append(("Shiva's Guard", "AOE slow and armor to defend against push."))
        items.append(("Maelstrom / Mjollnir", "Clears summoned units and illusions."))

    if not items:
        items = [
            ("Black King Bar", "Reduces magic damage and prevents disables."),
            ("Force Staff", "Reposition yourself or allies to escape or initiate."),
            ("Scythe of Vyse", "Hex to lock down key targets."),
            ("Heaven's Halberd", "Disarm to reduce physical damage."),
            ("Spirit Vessel", "Reduces regeneration on high-HP or healing heroes."),
        ]

    situational = (
        "Consider which of these fits your role (core vs support) and the enemy draft; "
        "adjust for heavy magic, physical, or illusion-based lineups."
    )
    tips = [
        f"Identify {name}'s main strength (burst, sustain, or control) and itemize to counter it.",
        "Fight when their key spells or ultimates are on cooldown.",
    ]
    return (items, situational, tips)


def generate_hero_counter_items_response(hero: HeroEntity) -> str:
    """
    Human-readable list of items that counter the given hero, with reasons,
    situational notes, and strategy tips. No numeric IDs or raw data.
    """
    try:
        items_with_reasons, situational, tips = _get_counter_items_for_hero(hero)
    except OpenDotaError:
        return (
            "I tried to pull data from OpenDota but the service is unavailable right now. "
            "Please try again later."
        )
    except Exception:
        return (
            "I could not generate counter items for that hero at the moment. "
            "Please try again or rephrase your question."
        )

    name = hero.localized_name
    lines: List[str] = [
        f"Counter Items Against {name}",
        "",
    ]
    for item_name, reason in items_with_reasons:
        lines.append(f"• {item_name} – {reason}")
    lines.append("")
    if situational:
        lines.append("Situational Notes")
        lines.append("")
        lines.append(situational)
        lines.append("")
    lines.append("Tips")
    lines.append("")
    for tip in tips:
        lines.append(f"• {tip}")
    return _ensure_readable_only("\n".join(lines))


# --- Response formatting layer: all outputs are human-readable text only ---

def _ensure_readable_only(text: str) -> str:
    """
    Ensure the final response never contains raw code, JSON, or data structures.
    If the text looks like serialized data, return a safe fallback message.
    """
    if not text or not isinstance(text, str):
        return "I could not generate a readable answer for that. Please try rephrasing your question."
    # Detect accidental inclusion of dict/list repr or JSON
    trim = text.strip()
    if (trim.startswith("{") and "}" in trim) or (trim.startswith("[") and "]" in trim):
        return "I could not format that information properly. Please try asking again in a different way."
    if '": "' in text and "{" in text and text.count("{") > 2:
        return "Something went wrong formatting the response. Please try again."
    return text


@lru_cache(maxsize=1)
def _build_item_id_and_key_maps() -> Tuple[Tuple[dict, dict]]:
    """
    Build id -> display name and key -> display name from OpenDota constants.
    Item popularity API uses numeric IDs (as string keys); constants/items uses string keys.
    Returns ((id_to_name, key_to_name),) for lru_cache compatibility. Never expose raw IDs to the user.
    """
    id_to_name: dict = {}
    key_to_name: dict = {}
    try:
        items = get_items()
        if not isinstance(items, dict):
            return ((id_to_name, key_to_name),)
        for key, data in items.items():
            if not isinstance(data, dict):
                continue
            dname = data.get("dname")
            if isinstance(dname, str) and dname:
                key_to_name[str(key)] = dname
                item_id = data.get("id")
                if item_id is not None:
                    id_to_name[int(item_id)] = dname
                    id_to_name[str(item_id)] = dname
    except Exception:
        pass
    return ((id_to_name, key_to_name),)


def _get_item_maps() -> Tuple[dict, dict]:
    """Unpack cached (id_to_name, key_to_name)."""
    packed = _build_item_id_and_key_maps()
    return packed[0]


def _get_item_data_by_key_or_id(key_or_id) -> dict:
    """Return the OpenDota item dict for lookup by string key or numeric ID. Never expose to user."""
    try:
        items = get_items()
        if not isinstance(items, dict):
            return {}
        if isinstance(key_or_id, str) and key_or_id.isdigit():
            key_or_id = int(key_or_id)
        if isinstance(key_or_id, int):
            for k, data in items.items():
                if isinstance(data, dict) and data.get("id") == key_or_id:
                    return data
            return {}
        return items.get(str(key_or_id), {}) if isinstance(key_or_id, str) else {}
    except Exception:
        return {}


def _item_name_from_key(key) -> str:
    """
    Resolve item key or numeric ID to in-game display name.
    Unknown items return "Unknown Item (id)" so IDs are never bare; the label is human-readable.
    """
    try:
        id_map, key_map = _get_item_maps()
        if key is None:
            return "Unknown Item (?)"
        if isinstance(key, int):
            name = id_map.get(key) or key_map.get(str(key))
            return name if name else f"Unknown Item ({key})"
        if isinstance(key, str):
            key = key.strip()
            if not key:
                return "Unknown Item (?)"
            name = None
            if key.isdigit():
                name = id_map.get(int(key)) or id_map.get(key) or key_map.get(key)
            else:
                name = key_map.get(key)
            return name if name else f"Unknown Item ({key})"
    except Exception:
        id_fallback = key if key is not None else "?"
        return f"Unknown Item ({id_fallback})"
    return "Unknown Item (?)"


def _item_reason_for_hero(item_key, hero: HeroEntity) -> str:
    """
    One short sentence why this item is useful for the hero. item_key may be string key or numeric ID.
    Uses item description and simple heuristics; output is always natural language.
    """
    hero_name = hero.localized_name
    item_data = _get_item_data_by_key_or_id(item_key)
    if not isinstance(item_data, dict):
        return f"Commonly built to strengthen {hero_name}'s impact in fights."
    desc = (item_data.get("desc") or item_data.get("lore") or "").lower()
    name = (item_data.get("dname") or "").lower()
    # Short heuristic reasons based on common item roles (use name; item_key may be numeric ID)
    if "blink" in name or (isinstance(item_key, str) and "blink" in item_key):
        return f"Lets {hero_name} initiate or escape quickly with a targeted teleport."
    if "black king bar" in name or "bkb" in name:
        return f"Grants spell immunity so {hero_name} can commit in fights without being locked down."
    if "blade mail" in name or "blademail" in name:
        return f"Reflects damage when {hero_name} is focused, punishing attackers."
    if "force staff" in name or "force" in name:
        return f"Adds mobility and save potential for {hero_name} or an ally."
    if "aghanim" in name or "scepter" in name:
        return f"Upgrades {hero_name}'s abilities for stronger teamfight or utility."
    if "boots" in name or "travel" in name:
        return f"Improves {hero_name}'s movement and map presence."
    if "maelstrom" in name or "mjollnir" in name or "manta" in name:
        return f"Increases {hero_name}'s damage or attack speed for faster farming and fights."
    if "dragon lance" in name or "hurricane pike" in name:
        return f"Adds range and stats so {hero_name} can hit safely and survive dives."
    if "treads" in name or "power treads" in name:
        return f"Mobility and attack speed for {hero_name} in the early and mid game."
    if "tango" in name or "branch" in name or "iron branch" in name:
        return f"Early lane regeneration and stats for {hero_name}."
    if "wraith band" in name or "bracer" in name or "null talisman" in name:
        return f"Early stats and damage for {hero_name}."
    if "magic wand" in name:
        return f"Burst HP and mana recovery when {hero_name} is pressured in lane or fights."
    if "daedalus" in name or "monkey king bar" in name:
        return f"Critical strike or accuracy and extra damage for {hero_name} in the late game."
    if "satanic" in name or "heart" in name:
        return f"Sustain and tankiness so {hero_name} can stay in long fights."
    if "glimmer" in name or "cape" in name:
        return f"Protection or utility for {hero_name} or an ally."
    if desc:
        first_sentence = desc.split(".")[0].strip()[:80]
        if first_sentence:
            return first_sentence + "." if not first_sentence.endswith(".") else first_sentence
    return f"Popular choice to round out {hero_name}'s build and power spikes."


def _get_items_by_phase(hero_id: int, top_per_phase: int = 5) -> List[Tuple[str, List[Tuple[str, int]]]]:
    """
    Get item popularity grouped by game phase. Returns a list of (phase_label, [(item_key, count), ...]).
    Handles missing or malformed data gracefully; never raises.
    """
    try:
        raw = get_hero_item_popularity(hero_id)
    except Exception:
        return []
    if not isinstance(raw, dict):
        return []
    phase_config = [
        ("Starting items", "start_game_items"),
        ("Early game items", "early_game_items"),
        ("Core / Mid game items", "mid_game_items"),
        ("Late game items", "late_game_items"),
    ]
    result: List[Tuple[str, List[Tuple[str, int]]]] = []
    for label, key in phase_config:
        phase_data = raw.get(key)
        if not isinstance(phase_data, dict):
            result.append((label, []))
            continue
        items_with_count = []
        for k, v in phase_data.items():
            if k is None:
                continue
            try:
                count = int(v) if isinstance(v, (int, float)) else 0
            except (ValueError, TypeError):
                count = 0
            items_with_count.append((k, count))
        items_with_count.sort(key=lambda x: x[1], reverse=True)
        result.append((label, items_with_count[:top_per_phase]))
    return result


def _format_hero_build_as_readable(hero: HeroEntity, phase_items: List[Tuple[str, List[Tuple[str, int]]]]) -> str:
    """
    Convert structured phase item data into a single human-readable guide.
    Skips empty sections. All item keys/IDs resolved to display names; unknown items omitted.
    """
    hero_name = hero.localized_name
    lines: List[str] = [f"Item Build Guide for {hero_name}", ""]

    section_labels = [
        ("Starting items", "Starting Items"),
        ("Early game items", "Early Game Items"),
        ("Core / Mid game items", "Core / Mid Game Items"),
        ("Late game items", "Late Game Items"),
    ]

    has_any = False
    safe_phase_items = phase_items[: len(section_labels)] if phase_items else []
    for (_internal_label, display_label), (phase_label, items_list) in zip(section_labels, safe_phase_items):
        section_bullets: List[str] = []
        for item_key, _ in (items_list if isinstance(items_list, list) else []):
            try:
                name = _item_name_from_key(item_key)
            except Exception:
                name = f"Unknown Item ({item_key})"
            try:
                reason = _item_reason_for_hero(item_key, hero)
            except Exception:
                reason = f"Commonly built for {hero_name}."
            section_bullets.append(f"• {name} – {reason}")
            has_any = True
        if section_bullets:
            lines.append(display_label)
            lines.append("")
            lines.extend(section_bullets)
            lines.append("")

    if not has_any:
        lines.append("• No detailed build data is available right now for this hero.")
        lines.append("")

    lines.append("Situational Items")
    lines.append("")
    lines.append("• Force Staff – Positioning or saves for you or an ally.")
    lines.append("• Glimmer Cape – Protection or utility against magic burst.")
    lines.append("• Heart of Tarrasque – Extra survivability in long games.")
    lines.append("• Black King Bar – Spell immunity when the enemy has heavy lockdown.")
    lines.append("• Hurricane Pike – Mobility and survival against divers.")
    lines.append("")
    lines.append("Strategy Tips")
    lines.append("")
    lines.append("• Prioritize farming efficiently in the early game so you hit your core timings.")
    lines.append("• Fight around key items like BKB or your main damage item so you have the biggest impact.")
    lines.append("• Adapt situational items depending on enemy heroes and threats (e.g. evasion, magic, or lockdown).")
    return "\n".join(lines).strip()


def generate_hero_build_response(hero: Optional[HeroEntity]) -> str:
    """
    Return a human-readable item build guide for the hero. Handles missing hero,
    empty sections, and API errors gracefully. Never raises; always returns readable text.
    """
    if hero is None:
        return (
            "Sorry, I don't have item build information for that hero right now. "
            "Please check the hero name and try again."
        )
    try:
        phase_items = _get_items_by_phase(hero.id)
    except OpenDotaError:
        return (
            "I tried to pull live item data from OpenDota but the service is unavailable right now. "
            "Please try again later."
        )
    except Exception:
        return (
            "I could not load item build data for this hero at the moment. "
            "Please try again or ask for a different hero."
        )
    try:
        response = _format_hero_build_as_readable(hero, phase_items)
        return _ensure_readable_only(response)
    except Exception:
        return (
            "I couldn't format the build guide for this hero. "
            "Please try again or ask about a different hero."
        )


def _describe_item(item: ItemEntity) -> str:
    data = get_items().get(item.key, {})
    desc = (data.get("desc") or "").strip()
    cost = data.get("cost")
    pieces = [f"{item.display_name} is an item that {desc}"]
    if cost:
        pieces.append(f"It costs {cost} gold.")
    return " ".join(pieces).strip()


def _format_attrib(attrib: list) -> List[str]:
    """Turn OpenDota attrib list into readable stat lines."""
    lines: List[str] = []
    for a in attrib or []:
        display = a.get("display")
        value = a.get("value")
        key = a.get("key", "")
        if display and value is not None:
            try:
                line = display.replace("{value}", str(value))
            except Exception:
                line = f"{key}: {value}"
            lines.append(f"• {line}")
        elif value is not None:
            lines.append(f"• {key}: {value}")
    return lines


def _format_abilities(abilities: list) -> Tuple[List[str], List[str]]:
    """Return (active_lines, passive_lines) from OpenDota abilities."""
    active: List[str] = []
    passive: List[str] = []
    for ab in abilities or []:
        title = ab.get("title") or "Ability"
        desc = (ab.get("description") or "").strip().replace("\n\n", " ")
        line = f"{title}: {desc}" if desc else title
        if ab.get("type") == "active":
            active.append(line)
        else:
            passive.append(line)
    return active, passive


def generate_item_info_response(item: ItemEntity) -> str:
    """
    Structured item explanation: name, cost, stats, active/passive effects,
    and gameplay tips. Used when the user asks what an item is or what it does.
    """
    try:
        data = get_items().get(item.key, {})
    except OpenDotaError:
        return (
            "I tried to fetch this item's data from OpenDota but the service is unavailable right now. "
            "Please try again later."
        )
    if not data:
        return f"I could not find detailed data for {item.display_name}."

    name = data.get("dname") or item.display_name
    cost = data.get("cost")
    desc = (data.get("desc") or data.get("lore") or "").strip()
    if not desc and data.get("abilities"):
        first_ab = data["abilities"][0]
        desc = (first_ab.get("description") or "").strip().replace("\n", " ")[:300]
    notes = (data.get("notes") or "").strip()
    attrib = data.get("attrib") or []
    abilities = data.get("abilities") or []
    behavior = data.get("behavior")

    lines: List[str] = []

    lines.append(name)
    lines.append("")

    if cost is not None:
        lines.append(f"Cost: {cost} gold")
        lines.append("")

    if desc:
        lines.append("Description")
        lines.append(desc)
        lines.append("")

    stats = _format_attrib(attrib)
    if stats:
        lines.append("Stats / Attributes")
        lines.extend(stats)
        lines.append("")

    active_lines, passive_lines = _format_abilities(abilities)
    if active_lines:
        lines.append("Active Ability")
        for a in active_lines:
            lines.append(f"• {a}")
        lines.append("")
    if passive_lines:
        lines.append("Passive Effects")
        for p in passive_lines:
            lines.append(f"• {p}")
        lines.append("")

    if notes:
        lines.append("Notes")
        lines.append(notes)
        lines.append("")

    lines.append("Gameplay Tips")
    lines.append("• Consider this item when it fits your role (survival, damage, or control) and your current timing.")
    lines.append("• Check whether your team needs the active effect in fights or the passive stats for farming and scaling.")
    lines.append("• Coordinate with your team so you are not duplicating the same utility (e.g., multiple Shivas).")

    return _ensure_readable_only("\n".join(lines))


def _infer_item_counters(item: ItemEntity) -> List[str]:
    data = get_items().get(item.key, {})
    text = ((data.get("desc") or "") + " " + (data.get("notes") or "")).lower()
    tips: List[str] = []

    if "ethereal" in text:
        tips.append("Use magical burst damage while the target is ethereal to punish the increased magic damage taken.")
        tips.append("Bring dispels or purge effects to remove ethereal form when used defensively.")
    if "spell immunity" in text:
        tips.append("Play around the duration of spell immunity, kiting the target until it expires.")
        tips.append("Draft heroes whose key abilities pierce spell immunity or rely more on right-click damage.")
    if "invisible" in text or "invisibility" in text:
        tips.append("Buy true sight items such as Sentry Wards, Dust of Appearance, or Gem of True Sight.")
        tips.append("Place aggressive vision so the enemy cannot safely abuse invisibility to farm or escape.")
    if "lifesteal" in text or "life steal" in text:
        tips.append("Pick up heal reduction or burst damage to kill through lifesteal.")
    if "evasion" in text:
        tips.append("Purchase True Strike or accuracy-focused items to bypass evasion.")
    if not tips:
        tips.append("Look for silences, dispels, or hard disables to prevent the item from being used at a critical moment.")
        tips.append("Adapt your build to outscale or bypass the main strength this item provides.")

    return tips


def generate_item_explanation_response(item: ItemEntity) -> str:
    try:
        description = _describe_item(item)
    except OpenDotaError:
        return (
            "I tried to fetch this item's data from OpenDota but the service is unavailable right now. "
            "Please try again later."
        )

    lines = [description, "", "Key points:", f"• {item.display_name} fits into lineups that benefit from its specific stats or active effect."]
    lines.append(
        "• Think about whether this helps you survive, deal damage, or control fights, and buy it when that lines up with your role."
    )
    return _ensure_readable_only("\n".join(lines))


def generate_item_counter_response(item: ItemEntity) -> str:
    try:
        description = _describe_item(item)
        tips = _infer_item_counters(item)
    except OpenDotaError:
        return (
            "I tried to fetch this item's data from OpenDota but the service is unavailable right now. "
            "Please try again later."
        )

    lines: List[str] = [
        f"{item.display_name} can swing fights heavily if you ignore it.",
        "",
        description,
        "",
        "Ways to counter it:",
    ]
    for tip in tips:
        lines.append(f"• {tip}")

    lines.append("")
    lines.append(
        "If you respect the item's strengths and plan your fights around its cooldown and limitations, it becomes much less threatening."
    )
    return _ensure_readable_only("\n".join(lines))


def _generate_tier_items_response(tier: int) -> str:
    """
    Answer questions about 'best tier 5 item' by listing Tier 5 neutral items
    from live OpenDota data and explaining that the best choice is situational.
    """
    try:
        items = get_items()
    except OpenDotaError:
        return (
            "I tried to fetch Tier 5 items from OpenDota but the service is unavailable right now. "
            "Please try again later."
        )

    tier_items: List[str] = []
    if isinstance(items, dict):
        for key, data in items.items():
            if not isinstance(data, dict):
                continue
            tier_val = data.get("tier")
            if tier_val == tier:
                name = data.get("dname")
                if isinstance(name, str) and name:
                    tier_items.append(name)
                else:
                    tier_items.append(key.replace("_", " ").title())

    tier_items = sorted(set(tier_items))

    if tier == 5:
        intro = (
            "There is no single objectively best Tier 5 neutral item; the optimal choice depends strongly on your hero, role, and game state. "
            "Several Tier 5 items are, however, extremely powerful in specific scenarios."
        )
    else:
        intro = (
            f"Tier {tier} neutral items provide meaningful power spikes when they drop, "
            "and the best option is the one that aligns precisely with your hero's role and your lineup's current needs."
        )

    lines: List[str] = [intro, ""]
    if tier_items:
        lines.append(f"Available Tier {tier} neutral items include:")
        for name in tier_items:
            lines.append(f"• {name}")
        lines.append("")

    if tier >= 3:
        lines.append(
            "In practice, prioritize neutral items that reinforce your hero's primary responsibility: "
            "damage dealers prefer items that amplify right‑click or spell output, frontliners benefit from durability and control, "
            "and supports gain the most from utility and save mechanics."
        )
    else:
        lines.append(
            "In practice, lower‑tier neutral items provide modest advantages; favor those that clearly improve your lane stability, "
            "farming speed, or survivability until higher‑tier items become available."
        )
    return _ensure_readable_only("\n".join(lines))


def generate_generic_strategy_response(hero: Optional[HeroEntity], question: str) -> str:
    if hero is None:
        # Special cases: questions about neutral item tiers
        q = question.lower()
        if "tier 5" in q or "tier five" in q:
            return _generate_tier_items_response(5)
        if "tier 4" in q or "tier four" in q:
            return _generate_tier_items_response(4)
        if "tier 3" in q or "tier three" in q:
            return _generate_tier_items_response(3)
        if "tier 2" in q or "tier two" in q:
            return _generate_tier_items_response(2)
        if "tier 1" in q or "tier one" in q:
            return _generate_tier_items_response(1)

        lines = [
            "Good Dota decisions revolve around timings, vision, and playing to your lineup's strengths.",
            "",
            "General tips:",
            "• Fight around your team's key item and level timings instead of taking random brawls.",
            "• Use wards and smoke to force favorable engagements instead of walking into fog blindly.",
            "• Make sure your draft has clear win conditions (teamfight, pickoff, push, or scaling carry).",
        ]
        return _ensure_readable_only("\n".join(lines))

    name = hero.localized_name
    vs = "against" in question.lower()
    if vs:
        intro = f"Playing against {name} is about denying their ideal fights and punishing their weak moments."
        points = [
            f"• Identify {name}'s strongest timing (key levels or items) and avoid fair fights during that window.",
            f"• Use smoke ganks and smart vision to catch {name} when key spells or items are on cooldown.",
            f"• Draft tools that either kite {name} or burst them quickly before they can fully commit.",
        ]
    else:
        intro = f"To play {name} well, you need to understand your role in the lineup and your main timing."
        points = [
            "• Decide whether you are the frontliner, damage dealer, or utility hero for your team.",
            f"• Play for your first big item/level timing on {name} and coordinate fights around it.",
            "• Avoid unnecessary deaths before major objectives so that your spells and items are ready for key fights.",
        ]

    lines = [intro, "", "Key points:"]
    lines.extend(points)
    return _ensure_readable_only("\n".join(lines))

