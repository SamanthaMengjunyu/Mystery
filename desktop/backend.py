"""Local calculation boundary, durable records and opt-in AI jobs."""
from __future__ import annotations

from collections import OrderedDict
from contextlib import contextmanager
from datetime import datetime
import importlib
import json
import math
import re
from pathlib import Path
import secrets
import sqlite3
import threading
import time

from . import VERSION
from .runtime import bundled_node

MODULES = {
    "bazi": "四柱八字", "ziwei": "紫微斗数", "astro": "西方占星",
    "jyotish": "印度占星", "liuyao": "六爻", "meihua": "梅花易数",
    "tarot": "塔罗", "lenormand": "雷诺曼", "answers": "答案之书",
    "solar": "真太阳时",
}


class Backend:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "records.sqlite3"
        self.lock = threading.RLock()
        self.sessions = OrderedDict()
        self.rituals = OrderedDict()
        self.finished_rituals = OrderedDict()
        self.jobs = {}
        from .music import MusicLibrary
        self.music=MusicLibrary(self.data_dir)
        self.ui_testing=False
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, created TEXT, module TEXT, label TEXT, payload TEXT)")
            db.execute("CREATE TABLE IF NOT EXISTS birthdays (id TEXT PRIMARY KEY, name TEXT, created TEXT, updated TEXT, payload TEXT)")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.db_path, timeout=15)
        try:
            with db:
                yield db
        finally:
            db.close()

    def catalog(self):
        from mystery.tarot import get_deck, get_spread
        from mystery.lenormand.data import get_deck as lenormand_deck
        from mystery.solar_time.calculator import CITY_LONGITUDE
        return {"version": VERSION, "modules": MODULES, "cities": CITY_LONGITUDE,
                "tarot_deck": [{k: c[k] for k in ("id", "cn", "en", "arcana")} for c in get_deck()],
                "lenormand_deck": lenormand_deck(),
                "spreads": {k: get_spread(k) for k in ("single", "three", "celtic")},
                "data_dir": str(self.data_dir), "preferences": self.preferences(), "birthdays": self.birthdays(),
                'native_dialogs':bool(self.music.folder_picker),'ui_testing':self.ui_testing}

    def preferences(self, values=None):
        path = self.data_dir / "preferences.json"
        with self.lock:
            if values is not None:
                safe = {k: v for k, v in values.items() if k in ("quality", "reduced", "pinned", "api_base", "model", "active_birth_id", "birth_onboarding_done", "effects_default",'location_enabled','location_consent','birthday_reminders_enabled','reminders_last_shown','focus_scene','atlas_filters')
                        and isinstance(v, (str, bool))}
                temp = path.with_suffix(".tmp")
                temp.write_text(json.dumps(safe, ensure_ascii=False), encoding="utf-8")
                temp.replace(path)
                return safe
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return {}

    def birthdays(self, query=""):
        with self.connect() as db:
            people = [json.loads(row[0]) for row in db.execute("SELECT payload FROM birthdays ORDER BY name COLLATE NOCASE, created, id")]
        query = str(query).strip().casefold()[:120]
        return [p for p in people if not query or query in " ".join(str(p.get(k, "")) for k in ("name", "birth_place", "current_place", "notes", "datetime")).casefold()]

    def birthday(self, person_id):
        with self.connect() as db:
            row = db.execute("SELECT payload FROM birthdays WHERE id=?", (person_id,)).fetchone()
        if not row:
            raise ValueError("这份生辰资料不存在")
        return json.loads(row[0])

    @staticmethod
    def selected_places(p):
        """Resolve selected IDs on the server; legacy snapshots retain their original inputs."""
        values = dict(p)
        from .places import get_place
        for target in ('birth', 'current'):
            prefix = 'birth_' if target == 'birth' else 'current_'
            identity = values.get(prefix + 'place_id')
            if not identity: continue
            place = get_place(identity)
            values[prefix + 'place'] = place['display_name']
            values[prefix + 'place_kind'] = place['kind']
            for name in ('latitude', 'longitude', 'tz_name'):
                values[('current_' if target == 'current' else '') + name] = place[name]
        return values

    def save_birthday(self, p):
        from mystery.timebase import resolve_local
        p = self.selected_places(p)
        name = p.get("name", "")
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 80:
            raise ValueError("请填写 1～80 字的姓名或称呼")
        dt = datetime.fromisoformat(p.get("datetime", ""))
        if dt.tzinfo is not None or not 1900 <= dt.year <= 2100:
            raise ValueError("请填写 1900～2100 年的当地出生日期与时间，并单独指定时区")
        tz = str(p.get("tz_name", "Asia/Shanghai")).strip()
        fold = p.get("fold", "")
        if fold not in ("", None, 0, 1, "0", "1"):
            raise ValueError("请选择有效的夏令时重复时刻")
        try:
            resolve_local(dt, tz, fold=None if fold in ("", None) else int(fold))
        except ValueError as error:
            message = str(error)
            if "ambiguous" in message:
                raise ValueError("这个当地时刻因夏令时出现两次，请在时间规则中选择第一次或第二次") from error
            if "nonexistent" in message:
                raise ValueError("这个当地时刻被夏令时跳过，请核对出生时间") from error
            if "timezone" in message:
                raise ValueError("无法识别这个 IANA 时区，请填写如 Asia/Shanghai 的时区名称") from error
            raise ValueError("所选重复时刻规则不适用于这个出生时间，请改为自动校验") from error
        lon, lat = float(p.get("longitude", 116.41)), float(p.get("latitude", 39.90))
        if not math.isfinite(lon) or not math.isfinite(lat) or not -180 <= lon <= 180 or not -90 <= lat <= 90:
            raise ValueError("出生地经纬度超出范围")
        gender = p.get("gender", "男")
        if gender not in ("男", "女"):
            raise ValueError("请选择运限规则使用的性别")
        for key, limit in (("birth_place", 200), ("current_place", 200), ("notes", 1000)):
            if not isinstance(p.get(key, ""), str) or len(p.get(key, "")) > limit:
                raise ValueError("出生地或备注过长")
        if not isinstance(p.get("use_true_solar", False), bool):
            raise ValueError("真太阳时选项格式错误")
        color = p.get('color')
        if color is not None and (not isinstance(color, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', color)):
            raise ValueError('请选择有效的代表色')
        current_lon, current_lat = p.get('current_longitude'), p.get('current_latitude')
        current_tz=None
        if current_lon in (None, '') and current_lat in (None, ''):
            current_lon = current_lat = None
        else:
            try:
                current_lon, current_lat = float(current_lon), float(current_lat)
            except (TypeError, ValueError):
                raise ValueError('现居地经纬度须成对填写') from None
            if not math.isfinite(current_lon) or not math.isfinite(current_lat) or abs(current_lon) > 180 or abs(current_lat) > 90:
                raise ValueError('现居地经纬度超出范围')
            from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
            from .reminders import residence_zone
            current_tz=p.get('current_tz_name') or residence_zone(current_lon,current_lat)
            if current_tz:
                try:ZoneInfo(current_tz)
                except (ValueError,ZoneInfoNotFoundError):raise ValueError('现居地时区无法识别') from None
        with self.lock, self.connect() as db:
            person_id = p.get("id") or secrets.token_hex(12)
            previous = db.execute("SELECT created, payload FROM birthdays WHERE id=?", (person_id,)).fetchone()
            if p.get("id") and not previous:
                raise ValueError("这份生辰资料不存在，请重新打开生日簿")
            now = datetime.now().astimezone().isoformat(timespec="seconds")
            person = {"id": person_id, "name": name.strip(), "datetime": dt.isoformat(timespec="minutes"),
                      "tz_name": tz, "fold": "" if fold in ("", None) else str(fold), "longitude": lon, "latitude": lat,
                      "gender": gender, "use_true_solar": p.get("use_true_solar", False),
                      "birth_place": p.get("birth_place", "").strip(), "notes": p.get("notes", "").strip(),
                      "current_place": p.get('current_place', '').strip(), 'current_longitude': current_lon, 'current_latitude': current_lat,
                      'current_tz_name':current_tz,
                      'birth_place_id': p.get('birth_place_id', ''), 'birth_place_kind': p.get('birth_place_kind', 'city'),
                      'current_place_id': p.get('current_place_id', ''), 'current_place_kind': p.get('current_place_kind', 'city'),
                      'color': (color or (json.loads(previous[1]).get('color') if previous else None) or '#e6c795').lower(),
                      "created": previous[0] if previous else now, "updated": now}
            db.execute("INSERT OR REPLACE INTO birthdays VALUES (?, ?, ?, ?, ?)",
                       (person_id, person["name"], person["created"], now, json.dumps(person, ensure_ascii=False)))
        return person

    def save_birthday_note(self,p):
        notes=p.get('notes','')
        if not isinstance(notes,str) or len(notes)>1000:raise ValueError('备注最多 1000 字')
        with self.lock,self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT payload FROM birthdays WHERE id=?',(p['id'],)).fetchone()
            if not row:raise ValueError('这份生辰资料不存在')
            person=json.loads(row[0]);person['notes']=notes.strip();person['updated']=datetime.now().astimezone().isoformat(timespec='seconds')
            db.execute('UPDATE birthdays SET updated=?,payload=? WHERE id=?',(person['updated'],json.dumps(person,ensure_ascii=False),p['id']))
        return person

    def delete_birthday(self, person_id):
        with self.lock:
            with self.connect() as db:
                if not db.execute("DELETE FROM birthdays WHERE id=?", (person_id,)).rowcount:
                    raise ValueError("这份生辰资料不存在")
            prefs = self.preferences()
            if prefs.get("active_birth_id") == person_id:
                prefs["active_birth_id"] = ""
                self.preferences(prefs)
        return {"deleted": True}

    @staticmethod
    def random_options(p):
        value = p.get("seed")
        if value not in (None, ""):
            return {"seed": int(value)}
        return {"interaction": Backend.evidence(p)}

    @staticmethod
    def birth(p):
        dt = datetime.fromisoformat(p["datetime"])
        if dt.tzinfo is not None:
            raise ValueError("请输入当地钟表时间，并单独选择时区")
        return [dt.year, dt.month, dt.day, dt.hour, dt.minute]

    @staticmethod
    def evidence(p):
        from mystery.randomness import interaction_evidence
        samples = p.get("interaction") or []
        location = p.get("random_location")
        return interaction_evidence(samples, app_version=VERSION, location=location) if samples or location is not None else None

    def shuffle(self, p):
        module = p["module"]
        if module not in ("tarot", "lenormand"):
            raise ValueError("仅塔罗与雷诺曼支持选牌")
        engine = importlib.import_module("mystery." + module)
        kwargs = self.random_options(p)
        if module == "tarot":
            kwargs["reversals"] = p.get("reversals", True)
        private = engine.prepare_shuffle(**kwargs)
        token = secrets.token_urlsafe(24)
        with self.lock:
            now = time.monotonic()
            self.sessions = OrderedDict((k, v) for k, v in self.sessions.items() if now - v[2] < 1800)
            while len(self.sessions) >= 32:
                self.sessions.popitem(last=False)
            self.sessions[token] = (module, private, now)
        return {"session": token, "count": 78 if module == "tarot" else 36}

    def cut_deck(self, p):
        with self.lock:
            entry = self.sessions.get(p.get("session"))
            if not entry or time.monotonic() - entry[2] > 1800:
                raise ValueError("牌堆已过期，请重新洗牌")
            private = entry[1]
            at = p.get("at")
            if type(at) is not int or not 1 <= at < len(private["card_ids"]):
                raise ValueError("切牌位置超出范围")
            if "desktop_cut" in private and private["desktop_cut"] != at:
                raise ValueError("本次牌堆已经切好")
            if "desktop_cut" not in private:
                for key in ("card_ids", "orientations"):
                    if key in private:
                        private[key] = private[key][at:] + private[key][:at]
                private["desktop_cut"] = at
            return {"cut": at, "count": len(private["card_ids"])}

    def start_ritual(self, p):
        module = p.get("module")
        if module not in ("liuyao", "meihua", "answers"):
            raise ValueError("未知卜筮过程")
        values = {k: v for k, v in p.items() if k not in ("session", "step")}
        result = self.calculate(values, persist=False)
        total = {"liuyao": 6, "meihua": 3, "answers": 1}[module]
        token = secrets.token_urlsafe(24)
        with self.lock:
            now = time.monotonic()
            self.rituals = OrderedDict((k, v) for k, v in self.rituals.items() if now - v["at"] < 1800)
            while len(self.rituals) >= 32:
                self.rituals.popitem(last=False)
            self.rituals[token] = {"module": module, "inputs": values, "result": result,
                                   "step": 0, "total": total, "at": now}
        return {"session": token, "total": total}

    def ritual_step(self, p):
        with self.lock:
            entry = self.rituals.get(p.get("session"))
            if not entry or time.monotonic() - entry["at"] > 1800:
                raise ValueError("卜筮过程已过期，请重新准备")
            step = p.get("step")
            if type(step) is not int or not 1 <= step <= min(entry["step"] + 1, entry["total"]):
                raise ValueError("请按顺序完成每一步")
            entry["step"] = max(entry["step"], step)
            result = entry["result"]
            if entry["module"] == "liuyao":
                return {"step": step, "tosses": result["replay"]["tosses"][:step]}
            if entry["module"] == "meihua":
                return {"step": step, "upper": result["ben"]["upper"], "upper_bits": result["ben"]["bits"][3:],
                        **({"ben": result["ben"]} if step >= 2 else {}),
                        **({"moving": result["moving_line"], "bian": result["bian"]} if step == 3 else {})}
            return {"step": step, "page": result["page"], "answer": result["answer"]}

    def finish_ritual(self, p):
        with self.lock:
            completed = self.finished_rituals.get(p.get("session"))
            if completed and time.monotonic() - completed[1] < 1800:
                return self.get(completed[0])
            entry = self.rituals.get(p.get("session"))
            if not entry or time.monotonic() - entry["at"] > 1800 or entry["step"] != entry["total"]:
                raise ValueError("请先完成卜筮过程")
            record = self.save(entry["module"], entry["result"], entry["inputs"])
            self.finished_rituals[p["session"]] = (record["id"], time.monotonic())
            while len(self.finished_rituals) > 32:
                self.finished_rituals.popitem(last=False)
            del self.rituals[p["session"]]
            return record

    def cancel_ritual(self, p):
        with self.lock:
            self.rituals.pop(p.get("session"), None)
            self.finished_rituals.pop(p.get("session"), None)
            self.sessions.pop(p.get("session"), None)
        return {"cancelled": True}

    def calculate(self, p, *, persist=True):
        p = self.selected_places(p)
        module = p["module"]
        if module not in MODULES:
            raise ValueError("未知功能")
        tz = p.get("tz_name", "Asia/Shanghai")
        fold = None if p.get("fold", "") == "" else int(p["fold"])
        question = str(p.get("question", ""))[:4000]
        if module in ("bazi", "ziwei", "astro", "jyotish", "solar"):
            birth = self.birth(p)
            opts = {"tz_name": tz, "fold": fold}
            lon = float(p.get("longitude", 116.41))
            if module == "bazi":
                from mystery.bazi import calculate_bazi
                result = calculate_bazi(*birth, **opts, gender=p.get("gender", "男"), longitude=lon,
                                        use_true_solar=p.get("use_true_solar", False), sect=int(p.get("sect", 2)))
            elif module == "ziwei":
                from mystery.ziwei import cast
                result = cast(*birth, **opts, gender=p.get("gender", "男"), longitude=lon,
                              use_true_solar=p.get("use_true_solar", False), fix_leap=p.get("fix_leap", True),
                              day_divide=p.get("day_divide", "forward"), year_divide=p.get("year_divide", "normal"),
                              target_year=int(p["target_year"]) if p.get("target_year") else None,
                              node_binary=bundled_node())
            elif module in ("astro", "jyotish"):
                engine = importlib.import_module("mystery.astrology" if module == "astro" else "mystery.jyotish")
                kwargs = {"house_system": p.get("house_system", "P")} if module == "astro" else {
                    "node_mode": p.get("node_mode", "mean"), "dasha_year": p.get("dasha_year", "sidereal")}
                result = engine.cast(*birth, **opts, lat=float(p.get("latitude", 39.90)), lon=lon, **kwargs)
            else:
                from mystery.solar_time import to_true_solar_time
                corrected, detail = to_true_solar_time(datetime(*birth), lon, **opts)
                result = {"module": "solar", "summary": corrected.isoformat(), "detail": detail}
        elif module in ("tarot", "lenormand"):
            engine = importlib.import_module("mystery." + module)
            if module == "lenormand" and p.get("method") == "manual":
                result = engine.cast(p["card_ids"], question, spread_key=p.get("spread", "three"))
            else:
                # A session is consumed once; clients never receive hidden deck order.
                with self.lock:
                    entry = self.sessions.get(p.get("session"))
                    if not entry or entry[0] != module or time.monotonic() - entry[2] > 1800:
                        raise ValueError("洗牌已过期，请重新洗牌并选牌")
                    result = engine.draw(p.get("spread", "three"), question=question,
                                         picks=p.get("picks"), shuffle=entry[1])
                    del self.sessions[p["session"]]
        elif module == "liuyao":
            from mystery.liuyao import cast, draw
            dt = datetime.fromisoformat(p["datetime"])
            kwargs = {"question": question, "category": p.get("category", "zonghe"), "tz_name": tz,
                      "fold": fold, "date": {k: getattr(dt, k) for k in ("year", "month", "day", "hour", "minute", "second")}}
            result = cast(p["tosses"], **kwargs) if p.get("method") == "manual" else draw(**self.random_options(p), **kwargs)
        elif module == "meihua":
            from mystery.meihua import cast, cast_numbers, cast_time, cast_lunar
            opts = {"question": question, "nuclear": p.get("nuclear", "classic")}
            method = p.get("method", "numbers")
            if method == "time":
                result = cast_time(*self.birth(p), tz_name=tz, fold=fold, **opts)
            elif method == "lunar":
                branches = "子丑寅卯辰巳午未申酉戌亥"
                if not all(1 <= int(p[k]) <= 12 for k in ("year_branch", "hour_branch")):
                    raise ValueError("年支与时支序号须在 1～12 之间")
                result = cast_lunar(branches[int(p["year_branch"]) - 1], int(p["lunar_month"]), int(p["lunar_day"]),
                                    branches[int(p["hour_branch"]) - 1], leap_month=p.get("leap_month", False), **opts)
            elif method == "direct":
                result = cast(int(p["upper"]), int(p["lower"]), int(p["moving_line"]), **opts)
            else:
                result = cast_numbers(int(p["first"]), int(p["second"]),
                                      int(p["third"]) if p.get("third") not in (None, "") else None,
                                      hour_number=int(p["hour_number"]) if p.get("hour_number") else None, **opts)
        else:
            from mystery.answers import draw_answer
            result = draw_answer(question, **self.random_options(p))
        return self.save(module, result, p) if persist else result

    def save(self, module, result, inputs=None, label=None):
        record = {"id": secrets.token_hex(12), "created": datetime.now().astimezone().isoformat(timespec="seconds"),
                  "module": module, "label": label or str((inputs or {}).get("label") or (inputs or {}).get("question") or MODULES[module])[:120],
                  "result": result, "inputs": inputs or {}, "interpretation": "", "history": []}
        record["inputs"].pop("interaction", None)
        record["inputs"].pop("random_location", None)
        record["inputs"].pop("session", None)
        self.update(record)
        return record

    def update(self, record):
        with self.lock, self.connect() as db:
            db.execute("INSERT OR REPLACE INTO records VALUES (?, ?, ?, ?, ?)",
                       (record["id"], record["created"], record["module"], record["label"], json.dumps(record, ensure_ascii=False)))

    def records(self):
        with self.connect() as db:
            return [dict(zip(("id", "created", "module", "label"), row)) for row in
                    db.execute("SELECT id, created, module, label FROM records ORDER BY created DESC, rowid DESC")]

    def get(self, record_id):
        with self.connect() as db:
            row = db.execute("SELECT payload FROM records WHERE id=?", (record_id,)).fetchone()
        if not row:
            raise ValueError("记录不存在")
        return json.loads(row[0])

    def delete(self, record_id):
        with self.lock:
            if any(j["record_id"] == record_id and not j["done"] for j in self.jobs.values()):
                raise ValueError("请等待当前解读完成后再删除")
            with self.connect() as db:
                db.execute("DELETE FROM records WHERE id=?", (record_id,))
        return {"deleted": True}

    def replay(self, record_id):
        record = self.get(record_id)
        module = record["module"]
        if module not in ("tarot", "lenormand", "liuyao", "meihua", "answers"):
            raise ValueError("命盘保留原始结果，可在输入页按原参数重算；此功能用于随机／问事快照回放")
        engine = importlib.import_module("mystery." + module)
        restored = engine.replay(record["result"]["replay"], question=record["result"].get("question", ""))
        return {"verified": restored == record["result"], "record": record}

    def import_record(self, p):
        data = p["record"]
        module = data.get("module")
        if module not in MODULES or not isinstance(data.get("result"), dict):
            raise ValueError("不是 Mystery 记录文件")
        result = data["result"]
        if module in ("tarot", "lenormand", "liuyao", "meihua", "answers"):
            result = importlib.import_module("mystery." + module).replay(result["replay"], question=result.get("question", ""))
        inputs = data.get("inputs", {})
        if not isinstance(inputs, dict):
            raise ValueError("记录输入格式错误")
        # Only calculation inputs are imported; credentials never belong in a record.
        inputs = {k: v for k, v in inputs.items() if k not in ("api_key", "api_base", "model", "lite_model")}
        record = self.save(module, result, inputs, label="导入 · " + str(data.get("label", MODULES[module]))[:120])
        interpretation = data.get("interpretation", "")
        history = data.get("history", [])
        if isinstance(interpretation, str):
            record["interpretation"] = interpretation[:500000]
        if isinstance(history, list):
            record["history"] = [{"role": m["role"], "content": m["content"][:100000]}
                                 for m in history[:100] if isinstance(m, dict)
                                 and m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)]
        record["ai_incomplete"] = bool(data.get("ai_incomplete", False))
        self.update(record)
        return record

    def prompt(self, p):
        from mystery import llm
        record = self.get(p["id"])
        funcs = {"bazi": "build_prompt", "astro": "build_astro_prompt"}
        module = record["module"]
        if module in ("answers", "solar"):
            raise ValueError("此功能不需要 AI 提示词")
        system, user = getattr(llm, funcs.get(module, "build_" + module + "_prompt"))(record["result"])
        return {"system": system, "user": user}

    def start_ai(self, p):
        from mystery import llm
        record = self.get(p["id"])
        module = record["module"]
        if module in ("answers", "solar"):
            raise ValueError("此功能不支持 AI 解读")
        config = llm.make_config(p["api_base"], p["api_key"], p["model"], timeout=120, retry=0,
                                 lite_model=p.get("lite_model") or None, fallback=p.get("fallback", False))
        refs = []
        for ref_id in p.get("refs", [])[:4]:
            ref = self.get(ref_id)
            if ref["module"] != module:
                raise ValueError("只能对照同一模块的记录")
            refs.append({k: ref[k] for k in ("label", "result", "interpretation")})
        question = str(p.get("question", "")).strip()[:4000]
        if refs and not question:
            raise ValueError("请选择追问并填写对照问题")
        with self.lock:
            if any(not j["done"] for j in self.jobs.values()):
                raise ValueError("已有解读正在进行，请等待完成")
            self.jobs = {k: v for k, v in self.jobs.items() if not v["done"]}
            job_id = secrets.token_hex(16)
            job = {"events": [], "done": False, "record_id": record["id"]}
            self.jobs[job_id] = job

        def worker():
            text = ""
            failed = False
            try:
                if question:
                    stream = llm.interpret_followup_stream(module, record["result"], record["interpretation"],
                                                          record["history"], question, config, refs=refs)
                else:
                    name = {"bazi": "interpret_chart_stream", "astro": "interpret_astro_stream"}.get(module, "interpret_" + module + "_stream")
                    stream = getattr(llm, name)(record["result"], config)
                for event in stream:
                    event = {k: v.replace(config["api_key"], "[已隐藏]") if isinstance(v, str) else v for k, v in event.items()}
                    with self.lock:
                        job["events"].append(event)
                    if event.get("type") == "delta":
                        text += event.get("text", "")
                    if event.get("type") == "error":
                        failed = True
                    if event.get("type") == "usage":
                        record["usage"] = {k: event[k] for k in ("prompt_tokens", "completion_tokens", "total_tokens") if k in event}
                if text:
                    if question:
                        record["history"].extend([{"role": "user", "content": question}, {"role": "assistant", "content": text}])
                    else:
                        record["interpretation"] = text
                        record["history"] = []
                    record["ai_incomplete"] = failed
                    self.update(record)
            except Exception as error:
                with self.lock:
                    job["events"].append({"type": "error", "text": str(error).replace(config["api_key"], "[已隐藏]")})
                if text:
                    if question:
                        record["history"].extend([{"role": "user", "content": question}, {"role": "assistant", "content": text}])
                    else:
                        record["interpretation"] = text
                    record["ai_incomplete"] = True
                    self.update(record)
            finally:
                with self.lock:
                    job["done"] = True
        threading.Thread(target=worker, daemon=True).start()
        return {"job": job_id}

    def poll(self, p):
        with self.lock:
            job = self.jobs.get(p["job"])
            if not job:
                raise ValueError("解读任务不存在")
            cursor = max(0, int(p.get("cursor", 0)))
            return {"events": job["events"][cursor:], "cursor": len(job["events"]), "done": job["done"]}

    def dispatch(self, action, p):
        if action=='music-library':return self.music.library()
        if action=='music-choose-folder':return self.music.choose()
        if action=='music-settings':return self.music.save(p)
        if action=='birthday-reminders':
            from .reminders import birthday_reminders
            return birthday_reminders(self.birthdays(),p.get('viewer_zone','UTC'),p.get('now'))
        if action=='save-birthday-note':return self.save_birthday_note(p)
        if action=='device-place':
            from .places import resolve,nearby
            result=resolve(p['longitude'],p['latitude']);cities=nearby(result['longitude'],result['latitude'])
            return {'tz_name':result['tz_name'],'label':cities[0]['display_name']+'附近' if cities else '已取得大致位置'}
        if action == 'nearby-places':
            from .places import nearby
            return nearby(p['longitude'], p['latitude'])
        if action == 'search-places':
            from .places import search
            return search(p.get('query', ''))
        if action == 'place-at':
            from .places import resolve
            return resolve(p['longitude'], p['latitude'])
        if action == "catalog": return self.catalog()
        if action == "preferences": return self.preferences(p)
        if action == "birthdays": return self.birthdays(p.get("query", ""))
        if action == "birthday": return self.birthday(p["id"])
        if action == "save-birthday": return self.save_birthday(p)
        if action == "delete-birthday": return self.delete_birthday(p["id"])
        if action == "calculate": return self.calculate(p)
        if action == "shuffle": return self.shuffle(p)
        if action == "cut": return self.cut_deck(p)
        if action == "ritual-start": return self.start_ritual(p)
        if action == "ritual-step": return self.ritual_step(p)
        if action == "ritual-finish": return self.finish_ritual(p)
        if action == "ritual-cancel": return self.cancel_ritual(p)
        if action == "records": return self.records()
        if action == "record": return self.get(p["id"])
        if action == "delete": return self.delete(p["id"])
        if action == "replay": return self.replay(p["id"])
        if action == "import": return self.import_record(p)
        if action == "prompt": return self.prompt(p)
        if action == "ai": return self.start_ai(p)
        if action == "poll": return self.poll(p)
        if action == "models":
            from mystery.llm import list_models
            return list_models(p["api_base"], p["api_key"])
        raise ValueError("未知操作")
