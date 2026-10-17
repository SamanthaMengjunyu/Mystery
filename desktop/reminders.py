"""Upcoming Gregorian birthdays, evaluated by each friend's residence calendar."""
from calendar import isleap
from datetime import datetime,timedelta,timezone
from functools import lru_cache
from zoneinfo import ZoneInfo


@lru_cache(maxsize=512)
def residence_zone(longitude,latitude):
    from .places import resolve
    return resolve(longitude,latitude)['tz_name']


def birthday_reminders(people,viewer_zone='UTC',now=None):
    zone=ZoneInfo(viewer_zone)
    instant=datetime.fromisoformat(now.replace('Z','+00:00')) if isinstance(now,str) else now or datetime.now(timezone.utc)
    if instant.tzinfo is None:raise ValueError('提醒时刻须包含时区')
    viewer=instant.astimezone(zone);result=[]
    for p in people:
        friend_zone=p.get('current_tz_name');source='current'
        if not friend_zone and p.get('current_longitude') is not None and p.get('current_latitude') is not None:
            friend_zone=residence_zone(p['current_longitude'],p['current_latitude'])
        if not friend_zone:friend_zone=p.get('tz_name') or 'UTC';source='birth'
        local=instant.astimezone(ZoneInfo(friend_zone));birth=datetime.fromisoformat(p['datetime'])
        year=local.year;day=28 if birth.month==2 and birth.day==29 and not isleap(year) else birth.day
        event=datetime(year,birth.month,day,tzinfo=ZoneInfo(friend_zone))
        if event.date()<local.date():
            year+=1;day=28 if birth.month==2 and birth.day==29 and not isleap(year) else birth.day
            event=datetime(year,birth.month,day,tzinfo=ZoneInfo(friend_zone))
        days=(event.date()-local.date()).days
        if 0<=days<=5 and year>=birth.year:
            result.append({'id':p['id'],'name':p['name'],'color':p.get('color'),'days':days,'age':year-birth.year,
                           'birthday_date':event.date().isoformat(),'friend_date':local.date().isoformat(),'tz_name':friend_zone,'zone_source':source,
                           'place':p.get('current_place') if source=='current' else p.get('birth_place'),
                           'viewer_start':event.astimezone(zone).isoformat(timespec='minutes'),
                           'difference_minutes':round((local.utcoffset()-viewer.utcoffset()).total_seconds()/60),
                           'leap_adjusted':birth.month==2 and birth.day==29 and not isleap(year)})
    result.sort(key=lambda p:(p['days'],p['viewer_start'],p['name']))
    return {'items':result,'viewer_zone':viewer_zone,'viewer_time':viewer.isoformat(timespec='minutes'),'window_days':5}
