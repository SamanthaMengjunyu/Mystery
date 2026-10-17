"""无需联网即可生成各类解读和追问消息。"""
from .bazi import DOMAINS, build_prompt
from .astrology import ASTRO_DOMAINS, build_astro_prompt
from .tarot import build_tarot_prompt
from .liuyao import build_liuyao_prompt
from .ziwei import build_ziwei_prompt
from .jyotish import build_jyotish_prompt
from .meihua import build_meihua_prompt
from .lenormand import build_lenormand_prompt
from .followup import build_followup_messages

__all__ = ["DOMAINS", "ASTRO_DOMAINS", "build_prompt", "build_astro_prompt",
           "build_tarot_prompt", "build_liuyao_prompt", "build_ziwei_prompt",
           "build_jyotish_prompt", "build_meihua_prompt", "build_lenormand_prompt",
           "build_followup_messages"]
