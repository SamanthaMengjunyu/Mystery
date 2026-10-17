"""可选 LLM 配置、提示词、流式解读与追问；不依赖 Flask 或数据库。"""
from .client import list_models, ping_model
from .config import make_config
from .prompts import (build_prompt, build_astro_prompt, build_tarot_prompt,
                      build_liuyao_prompt, build_ziwei_prompt, build_jyotish_prompt,
                      build_meihua_prompt, build_lenormand_prompt,
                      build_followup_messages)
from .service import (interpret_chart, interpret_chart_stream, interpret_astro_stream,
                      interpret_tarot_stream, interpret_liuyao_stream,
                      interpret_ziwei_stream, interpret_jyotish_stream,
                      interpret_meihua_stream, interpret_lenormand_stream,
                      interpret_followup_stream)

__all__ = ["list_models", "ping_model", "make_config", "build_prompt",
           "build_astro_prompt", "build_tarot_prompt", "build_liuyao_prompt",
           "build_ziwei_prompt", "build_jyotish_prompt",
           "build_meihua_prompt", "build_lenormand_prompt",
           "build_followup_messages", "interpret_chart", "interpret_chart_stream",
           "interpret_astro_stream", "interpret_tarot_stream", "interpret_liuyao_stream",
           "interpret_ziwei_stream", "interpret_jyotish_stream",
           "interpret_meihua_stream", "interpret_lenormand_stream",
           "interpret_followup_stream"]
