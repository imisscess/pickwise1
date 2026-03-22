from functools import lru_cache
from typing import Dict, List

import requests

BASE_URL = "https://api.opendota.com/api"


class OpenDotaError(Exception):
    pass


def _get_json(path: str):
    url = f"{BASE_URL}{path}"
    try:
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        raise OpenDotaError(f"Failed to reach OpenDota: {exc}") from exc


@lru_cache(maxsize=1)
def get_heroes() -> List[dict]:
    """
    Return the full list of heroes from OpenDota.
    """
    return _get_json("/heroes")


@lru_cache(maxsize=1)
def get_items() -> Dict[str, dict]:
    """
    Return the full item constants dictionary from OpenDota.
    """
    return _get_json("/constants/items")


def get_hero_matchups(hero_id: int) -> List[dict]:
    """
    Return matchup stats for a hero against all others.
    """
    return _get_json(f"/heroes/{hero_id}/matchups")


def get_hero_item_popularity(hero_id: int) -> dict:
    """
    Return aggregated item popularity data for a given hero.
    """
    return _get_json(f"/heroes/{hero_id}/itemPopularity")

