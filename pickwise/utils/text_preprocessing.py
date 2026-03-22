import re
from typing import List

import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer


_STOPWORDS = None
_LEMMATIZER = None


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

    text = text.lower()
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

