"""答案之书答案池与随机选取功能（纯娱乐）。"""
from .data import ANSWERS
from .oracle import draw_answer, replay

__all__ = ["ANSWERS", "draw_answer", "replay"]
