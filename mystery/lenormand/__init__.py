"""雷诺曼36张：三／五张线性牌阵、手动录牌、随机抽取与回放。"""
from .data import get_deck, get_spread
from .reading import cast, draw, prepare_shuffle, replay

__all__ = ["get_deck", "get_spread", "cast", "draw", "prepare_shuffle", "replay"]
