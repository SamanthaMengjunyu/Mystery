"""
八字排盘核心服务

设计理念：八字是一个确定性的符号系统——给定阳历时刻与出生地经度，
四柱、十神、藏干、大运等全部可由历法规则推算，无需任何 LLM 介入。

历法基础采用 lunar-python 的 EightChar 模块，它以「干支历」排盘：
  - 年柱以「立春」换柱（非农历正月初一）
  - 月柱以十二节气的「节」换柱（非农历月）
这与自实现的农历取模算法有本质区别，边界日期才能正确。

时间预处理采用 mystery/solar_time/calculator 的真太阳时校正。
"""
from lunar_python import Solar
from ..solar_time import to_true_solar_time
from ..timebase import resolve_local, beijing_clock, time_record, wall_datetime
from .analysis import analyze_chart

# 五行字符集（用于五行力量统计）
WU_XING = ["木", "火", "土", "金", "水"]

# 性别 → lunar 库大运约定：1=男，0=女
GENDER_TO_CODE = {"男": 1, "女": 0}


def _pillar_info(get_gan, get_zhi, get_nayin, get_hide, get_shishen_gan,
                 get_shishen_zhi, get_dishi, get_wuxing, get_xunkong=None):
    """组装单柱信息（高阶函数，避免四柱重复代码）"""
    gan = get_gan()
    zhi = get_zhi()
    wuxing = get_wuxing()  # 形如 "金火"：天干五行 + 地支五行
    info = {
        "gan": gan,
        "zhi": zhi,
        "ganzhi": gan + zhi,
        "nayin": get_nayin(),
        "gan_wx": wuxing[0] if len(wuxing) >= 1 else "",
        "zhi_wx": wuxing[1] if len(wuxing) >= 2 else "",
        "hide_gan": get_hide(),                 # 全藏干列表
        "shishen_gan": get_shishen_gan(),       # 天干十神（日柱为「日主」）
        "shishen_zhi": get_shishen_zhi(),       # 地支藏干对应十神列表
        "dishi": get_dishi(),                   # 长生十二宫（地势）
    }
    if get_xunkong is not None:
        info["xunkong"] = get_xunkong()
    return info


def _wuxing_stats(ec):
    """统计四柱八字（天干 + 地支主气）的五行分布，纯计数"""
    counts = {wx: 0 for wx in WU_XING}
    for wuxing in (ec.getYearWuXing(), ec.getMonthWuXing(),
                   ec.getDayWuXing(), ec.getTimeWuXing()):
        for ch in wuxing:
            if ch in counts:
                counts[ch] += 1
    return counts


def _da_yun(ec, gender):
    """推算大运列表（前 8 步），含起运信息"""
    code = GENDER_TO_CODE.get(gender, 1)
    yun = ec.getYun(code)
    da_yun_list = []
    # getDaYun()[0] 为起运前的童限阶段（干支为空），从 [1] 起取真正的大运
    for d in yun.getDaYun()[1:9]:
        da_yun_list.append({
            "ganzhi": d.getGanZhi(),
            "start_year": d.getStartYear(),
            "start_age": d.getStartAge(),
            "end_year": d.getEndYear(),
        })
    return {
        "is_forward": yun.isForward(),          # 顺行/逆行
        "start_year": yun.getStartYear(),       # 起运需经过的年数
        "start_month": yun.getStartMonth(),
        "start_day": yun.getStartDay(),
        "list": da_yun_list,
    }


def calculate_bazi(year, month, day, hour, minute=0, gender="男",
                   longitude=None, use_true_solar=True, sect=2, *,
                   tz_name="Asia/Shanghai", fold=None):
    """
    主入口：计算完整命盘，返回排盘字典。

    参数：
      year/month/day/hour/minute  出生地当地钟表时刻；tz_name 为 IANA 时区
      gender   "男"/"女"，用于大运顺逆
      longitude  出生地经度（东经为正）；use_true_solar 时必填
      use_true_solar  是否做真太阳时校正
      sect  早晚子时流派：2=晚子时归当日（默认），1=晚子时归次日
      fold  夏令时重复时刻须明确选择 0/1，不存在的当地时间拒绝排盘
    """
    civil = wall_datetime(year, month, day, hour, minute)
    if not (1900 <= year <= 2100):
        raise ValueError("年份须在 1900~2100 之间")
    if not (1 <= month <= 12):
        raise ValueError("月份须在 1~12 之间")
    if not (1 <= day <= 31):
        raise ValueError("日期须在 1~31 之间")
    if not (0 <= hour <= 23):
        raise ValueError("小时须在 0~23 之间")
    if not (0 <= minute <= 59):
        raise ValueError("分钟须在 0~59 之间")
    if type(sect) is not int or sect not in (1, 2):
        raise ValueError("sect 须为 1 或 2")
    if not isinstance(gender, str) or gender not in GENDER_TO_CODE:
        raise ValueError("gender 须为男或女（用于大运规则）")
    if type(use_true_solar) is not bool:
        raise ValueError("use_true_solar 须为布尔值")
    if longitude is not None and (isinstance(longitude, bool)
            or not isinstance(longitude, (int, float)) or not -180 <= longitude <= 180):
        raise ValueError("经度须为 -180~180 之间的数值")

    local = resolve_local(civil, tz_name, fold=fold)
    clock_dt = beijing_clock(local)

    # 真太阳时预处理
    solar_detail = None
    if use_true_solar:
        if longitude is None:
            raise ValueError("启用真太阳时需提供出生地经度")
        if not (-180 <= longitude <= 180):
            raise ValueError("经度须在 -180~180 之间")
        chart_dt, solar_detail = to_true_solar_time(clock_dt, longitude)
    else:
        chart_dt = clock_dt

    solar = Solar.fromYmdHms(chart_dt.year, chart_dt.month, chart_dt.day,
                             chart_dt.hour, chart_dt.minute, chart_dt.second)
    lunar = solar.getLunar()
    ec = lunar.getEightChar()
    ec.setSect(sect)

    pillars = {
        "year": _pillar_info(
            ec.getYearGan, ec.getYearZhi, ec.getYearNaYin, ec.getYearHideGan,
            ec.getYearShiShenGan, ec.getYearShiShenZhi, ec.getYearDiShi,
            ec.getYearWuXing, ec.getYearXunKong),
        "month": _pillar_info(
            ec.getMonthGan, ec.getMonthZhi, ec.getMonthNaYin, ec.getMonthHideGan,
            ec.getMonthShiShenGan, ec.getMonthShiShenZhi, ec.getMonthDiShi,
            ec.getMonthWuXing, ec.getMonthXunKong),
        "day": _pillar_info(
            ec.getDayGan, ec.getDayZhi, ec.getDayNaYin, ec.getDayHideGan,
            ec.getDayShiShenGan, ec.getDayShiShenZhi, ec.getDayDiShi,
            ec.getDayWuXing, ec.getDayXunKong),
        "hour": _pillar_info(
            ec.getTimeGan, ec.getTimeZhi, ec.getTimeNaYin, ec.getTimeHideGan,
            ec.getTimeShiShenGan, ec.getTimeShiShenZhi, ec.getTimeDiShi,
            ec.getTimeWuXing, ec.getTimeXunKong),
    }

    lunar_info = {
        "lunar_year": lunar.getYear(),
        "lunar_month": abs(lunar.getMonth()),
        "lunar_day": lunar.getDay(),
        "is_leap": lunar.getMonth() < 0,
        "year_in_chinese": lunar.getYearInChinese(),
        "month_in_chinese": lunar.getMonthInChinese(),
        "day_in_chinese": lunar.getDayInChinese(),
        "sheng_xiao": lunar.getYearShengXiao(),
    }

    chart = {
        "input": {
            "year": year, "month": month, "day": day,
            "hour": hour, "minute": minute,
            "gender": gender, "longitude": longitude,
            "use_true_solar": use_true_solar, "sect": sect,
            "tz_name": tz_name, "fold": local.fold,
        },
        "time": time_record(local, basis="true-solar" if use_true_solar else "utc+08-standard"),
        "rules": {"schema": "bazi-rules-v1", "sect": sect,
                  "year_boundary": "lichun", "month_boundary": "jie"},
        "true_solar": solar_detail,
        "lunar": lunar_info,
        "day_master": ec.getDayGan(),            # 日主（命主天干）
        "pillars": pillars,
        "wuxing_stats": _wuxing_stats(ec),
        "extra": {
            "tai_yuan": ec.getTaiYuan(),         # 胎元
            "ming_gong": ec.getMingGong(),       # 命宫
            "shen_gong": ec.getShenGong(),       # 身宫
            "tai_xi": ec.getTaiXi(),             # 胎息
        },
        "da_yun": _da_yun(ec, gender),
        "summary": f"{ec.getYear()} {ec.getMonth()} {ec.getDay()} {ec.getTime()}",
    }
    # 第 2 层：结构化分析（纯规则，零 LLM）
    chart["analysis"] = analyze_chart(chart)
    return chart
