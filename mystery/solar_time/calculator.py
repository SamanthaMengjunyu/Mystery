"""
真太阳时计算模块（纯数学，无任何 LLM / 外部服务）

八字排盘讲究「真太阳时」：钟表上的北京时间并不等于出生地头顶太阳的真实时刻，
需要做两层校正——

1. 经度时差（地理时差）：北京时间以东经 120°（北京时区标准经线）为基准，
   地球自转 360° 需 24h，故每偏离 1° 经度相差 4 分钟，东偏为正、西偏为负。

2. 均时差（Equation of Time）：地球公转轨道为椭圆且自转轴有黄赤交角，
   导致「真太阳」与「平太阳」存在 ±16 分钟左右、随日期变化的偏差。
   此处采用 NOAA 标准近似公式。

真太阳时 = 北京时间 + 经度时差 + 均时差
"""
import math
from datetime import datetime, timedelta
from ..timebase import beijing_clock, resolve_local

# 北京时区标准经线（东经 120°）
STANDARD_MERIDIAN = 120.0

# 常用城市经度表（东经为正）。下拉用，用户也可手填任意经度。
CITY_LONGITUDE = {
    "北京": 116.41, "上海": 121.47, "天津": 117.20, "重庆": 106.55,
    "广州": 113.26, "深圳": 114.06, "香港": 114.17, "澳门": 113.55,
    "杭州": 120.16, "南京": 118.78, "苏州": 120.62, "武汉": 114.30,
    "成都": 104.07, "西安": 108.95, "郑州": 113.62, "济南": 117.00,
    "长沙": 112.94, "南昌": 115.86, "合肥": 117.23, "福州": 119.30,
    "厦门": 118.08, "昆明": 102.83, "贵阳": 106.71, "南宁": 108.37,
    "海口": 110.20, "石家庄": 114.51, "太原": 112.55, "沈阳": 123.43,
    "长春": 125.32, "哈尔滨": 126.53, "呼和浩特": 111.75, "兰州": 103.83,
    "西宁": 101.78, "银川": 106.27, "乌鲁木齐": 87.62, "拉萨": 91.14,
    "台北": 121.56,
}


def longitude_correction(longitude, standard_meridian=STANDARD_MERIDIAN):
    """经度时差（分钟）：每偏离标准经线 1° 相差 4 分钟，东正西负"""
    return (longitude - standard_meridian) * 4.0


def equation_of_time(dt):
    """均时差（分钟），NOAA 近似公式，结果为「真太阳时 − 平太阳时」"""
    day_of_year = dt.timetuple().tm_yday
    gamma = 2.0 * math.pi / 365.0 * (day_of_year - 1 + (dt.hour - 12) / 24.0)
    return 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )


def to_true_solar_time(dt, longitude, *, tz_name=None, fold=None):
    """
    将钟表时间换算为出生地真太阳时。
    naive 且不传 tz_name 时沿用固定 UTC+08 约定；aware datetime 或
    tz_name 指定的当地时间先转换为 UTC+08 标准钟表时刻，消除夏令时。
    返回 (校正后的 datetime, 明细字典)
    """
    if not isinstance(dt, datetime):
        raise ValueError("dt must be a datetime")
    if dt.tzinfo is not None:
        if tz_name is not None or fold is not None:
            raise ValueError("aware datetime cannot be combined with tz_name or fold")
        dt = beijing_clock(dt)
    elif tz_name is not None:
        dt = beijing_clock(resolve_local(dt, tz_name, fold=fold))
    elif fold is not None:
        raise ValueError("fold requires tz_name")
    if not isinstance(longitude, (int, float)) or isinstance(longitude, bool) or not -180 <= longitude <= 180:
        raise ValueError("longitude must be in -180..180")
    lon_min = longitude_correction(longitude)
    eot_min = equation_of_time(dt)
    total_min = lon_min + eot_min

    mean_solar = dt + timedelta(minutes=lon_min)
    true_solar = dt + timedelta(minutes=total_min)

    detail = {
        "longitude": longitude,
        "longitude_correction_min": round(lon_min, 2),
        "equation_of_time_min": round(eot_min, 2),
        "total_correction_min": round(total_min, 2),
        "clock_time": dt.strftime("%Y-%m-%d %H:%M"),
        "mean_solar_time": mean_solar.strftime("%Y-%m-%d %H:%M"),
        "true_solar_time": true_solar.strftime("%Y-%m-%d %H:%M"),
    }
    return true_solar, detail
