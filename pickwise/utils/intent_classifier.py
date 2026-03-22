from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import joblib

from .text_preprocessing import preprocess_for_model, preprocess_text
from .entity_detection import HeroEntity, ItemEntity, detect_hero, detect_item
from .triggers import match_intent_by_triggers


INTENT_MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "intent_model.pkl"


@dataclass
class IntentResult:
    intent: str
    confidence: float


class IntentClassifier:
    """
    Thin wrapper around a scikit-learn Pipeline that performs
    intent classification on user questions.
    """

    def __init__(self, model_path: Path = INTENT_MODEL_PATH):
        self.model_path = model_path
        self._pipeline = None

    def _ensure_loaded(self) -> None:
        if self._pipeline is not None:
            return
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Intent model not found at {self.model_path}. "
                f"Train it first with train_model.py."
            )
        self._pipeline = joblib.load(self.model_path)

    def predict(self, text: str) -> IntentResult:
        """
        Predict the most likely intent for the given user text.
        """
        self._ensure_loaded()
        processed = preprocess_for_model(text)
        proba = self._pipeline.predict_proba([processed])[0]
        labels = self._pipeline.classes_
        max_idx = int(proba.argmax())
        return IntentResult(intent=str(labels[max_idx]), confidence=float(proba[max_idx]))


def is_greeting(text: str) -> bool:
    """
    Return True if the user message is a short greeting / salutation
    such as "hi", "hey", "hello", "yo", "sup", "👋", etc.
    Case‑insensitive, tolerant of punctuation, and biased toward very short inputs.
    """
    if text is None:
        return False
    q = text.strip().lower()
    if not q:
        return False

    # Common greeting tokens and phrases
    greeting_tokens = {
        "hi",
        "hey",
        "hello",
        "yo",
        "hiya",
        "sup",
        "wassup",
        "whats up",
        "what's up",
        "hola",
        "bonjour",
        "hallo",
        "oi",
        "yo!",
    }

    # Strip simple punctuation around the word
    simplified = "".join(ch for ch in q if ch.isalnum() or ch.isspace())

    if simplified in greeting_tokens:
        return True

    # Single emoji / wave / very short friendly signal
    if q in {"👋", "🤚", "✋", "🖐", "👌", "🙌"}:
        return True

    # Very short messages (1–3 tokens) that contain a greeting word
    tokens = simplified.split()
    if 0 < len(tokens) <= 3 and any(t in greeting_tokens for t in tokens):
        return True

    # Extremely short alphabetic strings like "h", "yo", etc. treated as casual greeting
    if len(q) <= 2 and q.isalpha():
        return True

    return False


def is_self_intro_question(question: str) -> bool:
    """
    Return True if the user is asking about the chatbot itself (who are you,
    what is PickWise, introduce yourself, etc.). Used to prioritize the
    self-introduction response over gameplay advice.
    """
    q = question.lower().strip()
    if not q:
        return False
    phrases = [
        "who are you",
        "what are you",
        "introduce yourself",
        "introduce your self",
        "what is pickwise",
        "whats pickwise",
        "what's pickwise",
        "what do you do",
        "what is this chatbot",
        "what is this bot",
        "what is this assistant",
        "what can you do",
        "what are you for",
        "tell me about yourself",
        "who is pickwise",
        "what kind of bot",
        "what kind of assistant",
        "are you a bot",
        "are you an ai",
        "your name",
        "your purpose",
    ]
    if any(p in q for p in phrases):
        return True
    # Very short questions that are likely about the bot
    if q in ("who are you?", "what are you?", "what do you do?", "intro", "introduction"):
        return True
    tokens = set(preprocess_text(question))
    if tokens & {"who", "what", "you", "yourself", "pickwise", "assistant", "bot", "chatbot"}:
        if len(tokens) <= 5 and ("who" in tokens or "yourself" in tokens or "pickwise" in tokens):
            return True
    return False


def rule_based_intent(question: str, hero: Optional[HeroEntity], item: Optional[ItemEntity]) -> Optional[str]:
    """
    Rule-based intent using trigger phrases and keywords (see triggers.py).
    Handles common variations, synonyms, and phrasing so the AI responds correctly
    without exact training matches.
    """
    if is_self_intro_question(question):
        return "self_intro"
    if is_greeting(question):
        return "self_intro"

    trigger_intent = match_intent_by_triggers(
        question,
        hero_detected=hero is not None,
        item_detected=item is not None,
    )
    if trigger_intent is not None:
        return trigger_intent

    q_lower = question.lower()
    tokens = set(preprocess_text(question))

    counter_keywords = {"counter", "deal", "beat", "answer", "handle", "against", "versus", "vs", "anti"}
    build_keywords = {"build", "itemization", "items", "buy", "purchase", "setup"}
    describe_keywords = {"what", "explain", "meaning", "description", "work", "does"}

    if hero and (counter_keywords & tokens):
        return "counter_heroes"
    if hero and (build_keywords & tokens):
        return "hero_build"
    if item and (counter_keywords & tokens):
        return "counter_items"
    if item and (describe_keywords & tokens):
        return "item_info"
    if item:
        return "item_info"

    return None


def is_item_info_question(question: str, item: Optional[ItemEntity]) -> bool:
    """
    Return True if the user is clearly asking what an item is or what it does.
    Used to prioritize item-info response when an item is detected.
    """
    if item is None:
        return False
    q = question.lower().strip()
    if not q:
        return False
    # If they are asking how to counter the item, do not treat as item info
    counter_phrases = ["counter", "deal with", "beat", "against", "versus", "how to counter"]
    if any(p in q for p in counter_phrases):
        return False
    triggers = [
        "what is",
        "whats ",
        "what's ",
        "what does",
        "how does",
        "explain",
        "tell me about",
        "describe",
        "info about",
        "info on",
    ]
    if any(q.startswith(t) or t in q for t in triggers):
        return True
    # Short message that is mostly the item name -> treat as item info
    words = preprocess_text(question)
    if len(words) <= 4 and item.display_name.lower().replace("'", "") in q.replace("'", ""):
        return True
    return False


def is_dota_related(text: str) -> bool:
    """
    Heuristic check for whether a question is about Dota 2.
    Used to politely decline unrelated questions.
    """
    if text is None:
        return False
    q = (text or "").strip().lower()
    if not q:
        return False

    # If we can detect a hero or item from OpenDota data, treat as Dota-related.
    try:
        if detect_hero(text) is not None or detect_item(text) is not None:
            return True
    except Exception:
        # Ignore API/lookup errors; fall back to keyword heuristics below.
        pass

    # Core Dota vocabulary (roles, lanes, objectives, mechanics, etc.)
    single_token_keywords = {
        "dota",
        "dota2",
        "hero",
        "heroes",
        "mid",
        "safelane",
        "offlane",
        "carry",
        "support",
        "roshan",
        "radiant",
        "dire",
        "mmr",
        "gank",
        "laning",
        "lane",
        "midas",
        "ranked",
        "pubs",
        "matchmaking",
    }

    multi_token_keywords = {
        ("dota", "2"),
        ("safe", "lane"),
        ("off", "lane"),
        ("blink", "dagger"),
        ("neutral", "items"),
        ("tier", "5"),
        ("tier", "five"),
    }

    tokens = [t for t in q.split() if t]
    token_set = set(tokens)

    # Exact single-token matches
    if token_set & single_token_keywords:
        return True

    # Exact multi-token phrase matches (as contiguous sequences)
    for phrase in multi_token_keywords:
        n = len(phrase)
        for i in range(len(tokens) - n + 1):
            if tuple(tokens[i : i + n]) == phrase:
                return True

    return False

