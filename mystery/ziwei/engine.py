"""Pinned iztro local adapter. No network, npm or AI calls at calculation time."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from ..solar_time import to_true_solar_time
from ..timebase import beijing_clock, resolve_local, time_record, wall_datetime

_ROOT = Path(__file__).resolve().parent


def _run_engine(request, node_binary):
    manifest = json.loads((_ROOT / "vendor" / "manifest.json").read_text(encoding="utf-8"))
    bundle = _ROOT / "vendor" / "iztro-2.6.2.min.js"
    if hashlib.sha256(bundle.read_bytes()).hexdigest() != manifest["bundle_sha256"]:
        raise RuntimeError("iztro bundle checksum mismatch")
    binary = str(node_binary) if node_binary is not None else shutil.which("node")
    if not binary:
        raise RuntimeError("紫微排盘需要本地 Node.js；请安装 Node.js 或指定 node_binary")
    env = dict(os.environ, TZ="Asia/Shanghai")
    kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    try:
        process = subprocess.run([binary, str(_ROOT / "bridge.cjs")],
                                 input=json.dumps(request, ensure_ascii=False),
                                 capture_output=True, text=True, encoding="utf-8",
                                 timeout=10, env=env, shell=False, **kwargs)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError("无法运行本地紫微引擎，请检查 Node.js 路径及运行环境") from error
    if process.returncode:
        raise RuntimeError(f"紫微引擎计算失败：{process.stderr.strip()[:500]}")
    try:
        result = json.loads(process.stdout)
        if result["schema"] != "iztro-bridge-v1" or len(result["natal"]["palaces"]) != 12:
            raise ValueError("invalid bridge response")
    except (ValueError, KeyError, TypeError) as error:
        raise RuntimeError("紫微引擎返回了无效结果") from error
    return result, manifest


def analyze_chart(chart):
    """Deterministic chart facts, without invented auspiciousness scoring."""
    palaces = chart["palaces"]
    soul = next(p for p in palaces if p["name"] == "命宫")
    body = next(p for p in palaces if p["isBodyPalace"])
    mutagens = [{"star": star["name"], "mutagen": star["mutagen"],
                 "palace": palace["name"], "branch": palace["earthlyBranch"]}
                for palace in palaces
                for star in palace["majorStars"] + palace["minorStars"]
                if star.get("mutagen")]
    indices = {(soul["index"] + delta) % 12 for delta in (0, 4, 6, 8)}
    return {"soul_palace": deepcopy(soul), "body_palace": deepcopy(body),
            "natal_mutagens": mutagens,
            "soul_surrounding_palaces": [p["name"] for p in palaces if p["index"] in indices],
            "empty_major_palaces": [p["name"] for p in palaces if not p["majorStars"]]}


def cast(year, month, day, hour, minute=0, gender="男", *,
         tz_name="Asia/Shanghai", fold=None, longitude=None, use_true_solar=False,
         fix_leap=True, day_divide="forward", year_divide="normal",
         target_year=None, node_binary=None):
    """太阳历当地出生时间 → 紫微命盘（1900～2100）。

    Default profile: iztro通行安星、农历正月换年、晚子归次日、闰月分半。
    The engine clock is UTC+08 standard time, optionally true-solar corrected.
    target_year is required for an annual chart; no implicit current date.
    """
    civil = wall_datetime(year, month, day, hour, minute)
    if not 1900 <= year <= 2100:
        raise ValueError("年份须在 1900~2100 之间")
    if not isinstance(gender, str) or gender not in ("男", "女"):
        raise ValueError("gender 须为男或女（用于运限规则）")
    if type(use_true_solar) is not bool or type(fix_leap) is not bool:
        raise ValueError("use_true_solar 和 fix_leap 须为布尔值")
    if day_divide not in ("forward", "current") or year_divide not in ("normal", "exact"):
        raise ValueError("day_divide 须为 forward/current；year_divide 须为 normal/exact")
    if longitude is not None and (isinstance(longitude, bool)
            or not isinstance(longitude, (int, float)) or not -180 <= longitude <= 180):
        raise ValueError("经度须为 -180~180 之间的数值")
    local = resolve_local(civil, tz_name, fold=fold)
    clock = beijing_clock(local)
    solar_detail = None
    if use_true_solar:
        if longitude is None:
            raise ValueError("真太阳时须提供经度")
        clock, solar_detail = to_true_solar_time(clock, longitude)
    if target_year is not None and (type(target_year) is not int or not clock.year <= target_year <= 2200):
        raise ValueError("流年须为出生年到2200之间的整数年份")
    config = {"algorithm": "default", "yearDivide": year_divide,
              "horoscopeDivide": "normal", "ageDivide": "normal", "dayDivide": day_divide}
    time_index = 12 if clock.hour == 23 else (clock.hour + 1) // 2
    payload, manifest = _run_engine({"date": f"{clock.year}-{clock.month}-{clock.day}",
                                    "time_index": time_index, "gender": gender,
                                    "fix_leap": fix_leap, "config": config,
                                    "target_year": target_year}, node_binary)
    birth = payload["natal"]
    palaces = birth.pop("palaces")
    chart = {
        "module": "ziwei",
        "input": {"year": year, "month": month, "day": day, "hour": hour, "minute": minute,
                  "gender": gender, "tz_name": tz_name, "fold": local.fold,
                  "longitude": longitude, "use_true_solar": use_true_solar,
                  "fix_leap": fix_leap, "day_divide": day_divide, "year_divide": year_divide,
                  "target_year": target_year},
        "time": time_record(local, basis="true-solar" if use_true_solar else "utc+08-standard"),
        "calculation_time": {"clock": clock.isoformat(), "time_index": time_index},
        "true_solar": solar_detail,
        "rules": {"schema": "ziwei-rules-v1", "engine": "iztro", "engine_version": "2.6.2",
                  "bundle_sha256": manifest["bundle_sha256"], "config": config,
                  "fix_leap": fix_leap, "language": "zh-CN",
                  "annual_reference": f"{target_year}-06-01 12:00 UTC+08" if target_year else None},
        "birth": birth, "palaces": palaces,
        "decadals": payload["decadals"], "annual": payload["annual"],
        "summary": f"{birth['earthlyBranchOfSoulPalace']}命/{birth['earthlyBranchOfBodyPalace']}身 · {birth['fiveElementsClass']}",
    }
    chart["analysis"] = analyze_chart(chart)
    return chart
