import re
from typing import List, Dict

from difflib import SequenceMatcher

import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer


_STOPWORDS = None
_LEMMATIZER = None


_CHAT_REPLACEMENTS: Dict[str, str] = {
    # Common chat shortcuts / leetspeak
    "2": "to",
    "u": "you",
    "ur": "your",
    "pls": "please",
    "plz": "please",
    "thx": "thanks",
    "ty": "thanks",
}

# Dota slang expansions (keep this small and high-impact; entity detection handles many more)
_DOTA_ABBREV_EXPANSIONS: Dict[str, str] = {
    "am": "anti-mage",
    "pa": "phantom assassin",
    "wr": "windranger",
    "sf": "shadow fiend",
    "wk": "wraith king",
    "bb": "bristleback",
    "pl": "phantom lancer",
    "ta": "templar assassin",
}

# Tokens we commonly need to recognize reliably for intent routing (typo correction target set)
_KEYWORD_VOCAB: List[str] = [
    "hi",
    "hello",
    "hey",
    "yo",
    "sup",
    "what",
    "whats",
    "who",
    "how",
    "counter",
    "counters",
    "against",
    "versus",
    "beat",
    "deal",
    "item",
    "items",
    "build",
    "buy",
    "best",
    "tips",
    "explain",
    "describe",
    "info",
    "strategy",
    "lane",
    "mid",
]


def _collapse_repeated_chars(token: str) -> str:
    """
    Reduce exaggerated repeated characters: 'heyyy' -> 'heyy', 'hellooo' -> 'helloo'.
    We keep up to 2 repeats so intent can still be inferred.
    """
    return re.sub(r"(.)\1{2,}", r"\1\1", token)


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _fuzzy_correct_token(token: str) -> str:
    """
    Fuzzy typo correction for a single token.
    This is intentionally conservative: only correct when similarity is high.
    """
    if not token:
        return token
    if len(token) <= 2:
        # Handle ultra-short greetings / fast-typed noise
        if token in {"h1", "hi", "yo", "gm", "gn"}:
            return token
        return token

    t = _collapse_repeated_chars(token)

    # Common direct fixes
    direct = {
        "helo": "hello",
        "hellp": "hello",
        "heelo": "hello",
        "heello": "hello",
        "hii": "hi",
        "hiii": "hi",
        "wht": "what",
        "wat": "what",
        "wt": "what",
        "wats": "whats",
        "kounter": "counter",
        "kounters": "counters",
        "cnt": "counter",
        "contr": "counter",
        "itm": "item",
        "itme": "item",
        "itms": "items",
    }
    if t in direct:
        return direct[t]

    # Similarity matching to keyword vocab
    best = t
    best_score = 0.0
    for w in _KEYWORD_VOCAB:
        score = _similar(t, w)
        if score > best_score:
            best_score = score
            best = w

    # Threshold tuned to avoid over-correcting hero/item names
    if best_score >= 0.86:
        return best
    return t


def normalize_user_input(text: str) -> str:
    """
    Normalize messy, informal user input BEFORE any other step.
    - lowercase
    - normalize punctuation noise (????, !!!, ...)
    - collapse repeated characters in tokens
    - fuzzy-correct common intent keywords (what/counter/build/item/etc.)
    - expand a small set of high-impact Dota abbreviations (am/pa/wr/sf/wk/...)
    - keep the output as a human-readable string
    """
    if text is None:
        return ""
    q = str(text).strip().lower()
    if not q:
        return ""

    # Normalize punctuation spam to spaces
    q = re.sub(r"[!?\.]{2,}", " ", q)
    q = re.sub(r"[_\-]{2,}", " ", q)

    # Keep apostrophes (item names), but remove other punctuation noise
    q = re.sub(r"[^a-z0-9\s']+", " ", q)
    q = re.sub(r"\s+", " ", q).strip()

    tokens = [t for t in q.split(" ") if t]
    normalized_tokens: List[str] = []
    for tok in tokens:
        # Leetspeak-lite: 1 -> i, 0 -> o (helps with 'h1'/'he110' style)
        tok = tok.translate(str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t"}))

        # Basic chat replacements
        if tok in _CHAT_REPLACEMENTS:
            tok = _CHAT_REPLACEMENTS[tok]

        # Expand core Dota hero shorthand (context-aware enough for intent routing)
        if tok in _DOTA_ABBREV_EXPANSIONS:
            normalized_tokens.extend(_DOTA_ABBREV_EXPANSIONS[tok].split())
            continue

        tok = _fuzzy_correct_token(tok)
        normalized_tokens.append(tok)

    return " ".join(normalized_tokens).strip()


def _ensure_nltk_data() -> None:
    """
    Ensure that required NLTK resources are available.
    Downloads them on first use if missing.
    """
    try:
        nltk.data.find("corpora/stopwords")
    except LookupError:
        nltk.download("stopwords", quiet=True)
    try:
        nltk.data.find("corpora/wordnet")
    except LookupError:
        nltk.download("wordnet", quiet=True)
    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        nltk.download("punkt", quiet=True)
    # Newer NLTK versions separate punkt tables
    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        nltk.download("punkt_tab", quiet=True)


def _get_tools():
    global _STOPWORDS, _LEMMATIZER
    if _STOPWORDS is None or _LEMMATIZER is None:
        _ensure_nltk_data()
        _STOPWORDS = set(stopwords.words("english"))
        _LEMMATIZER = WordNetLemmatizer()
    return _STOPWORDS, _LEMMATIZER


def preprocess_text(text: str) -> List[str]:
    """
    Basic NLP preprocessing suitable for both intent classification
    and simple entity matching.

    Steps:
    - lowercase
    - remove punctuation
    - tokenize
    - remove stopwords and non-alphabetic tokens
    - lemmatize

    Returns a list of processed tokens, e.g.:
        "How do I counter Phantom Assassin?"
        -> ["counter", "phantom", "assassin"]
    """
    if not text:
        return []

    # CRITICAL: run normalization layer first so every downstream stage
    # sees the same cleaned/expanded form of the user's message.
    text = normalize_user_input(text)
    text = re.sub(r"[^\w\s]", " ", text)

    stop_words, lemmatizer = _get_tools()

    raw_tokens = nltk.word_tokenize(text)
    tokens: List[str] = []
    for tok in raw_tokens:
        if not tok.isalpha():
            continue
        if tok in stop_words:
            continue
        lemma = lemmatizer.lemmatize(tok)
        if lemma:
            tokens.append(lemma)

    return tokens


def preprocess_for_model(text: str) -> str:
    """
    Convenience helper that returns a preprocessed string suitable
    for feeding into a vectorizer (tokens joined by spaces).
    """
    return " ".join(preprocess_text(text))

