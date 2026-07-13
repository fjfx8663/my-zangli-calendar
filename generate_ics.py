# Generated automatically by GitHub Actions
import os
from concurrent.futures import ProcessPoolExecutor
from datetime import date, timedelta, datetime
try:
    from tyme4py.solar import SolarDay
except ImportError:
    print("请先安装库：pip install tyme4py")
    exit(1)

# ====== ⬇️ 在这里配置你的自定义藏历事件 ⬇️ ======

START_YEAR = 2024
END_YEAR = 2035

# 【升级版格式】：用方括号 [...] 包裹当天的所有事件，中间用逗号隔开
# （如果你以后不小心忘了加方括号，直接写成了一行字符串，程序也能智能识别，不会报错！）
CUSTOM_EVENTS = {
    "一月初一": ["🎉 藏历新年 (Losar)"],
    "四月十五": ["☸️ 萨嘎达瓦节"],
    
    # 👇 看这里：六月初四现在被分成了两个独立的事件！
    "六月初四": [
        "🏔️ 佛陀初转法轮日", 
        "🎂 索达吉堪布生日"
    ],
    
    "九月廿二": ["🕊️ 降凡节"],
    "十月廿五": ["🕯️ 燃灯节"],
}

SHOW_DAILY_DATE = False

# ==================================================

def get_zangli_date(current_date):
    """Convert one Gregorian date in a separate worker process.

    tyme4py's Tibetan-calendar conversion is comparatively expensive. Keeping
    this helper at module level makes it picklable for ProcessPoolExecutor and
    lets the GitHub Actions runner use all available CPU cores.
    """
    try:
        solar = SolarDay.from_ymd(
            current_date.year, current_date.month, current_date.day
        )
        return current_date, str(solar.get_rab_byung_day())
    except Exception:
        return current_date, None

def generate_ics():
    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//My Tibetan Calendar//ZH",
        "CALSCALE:GREGORIAN",
        "X-WR-CALNAME:我的定制藏历",
        "X-APPLE-CALENDAR-COLOR:#FF9500",
        "X-WR-TIMEZONE:Asia/Shanghai"
    ]
    
    current_date = date(START_YEAR, 1, 1)
    end_date = date(END_YEAR, 12, 31)
    dtstamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    
    dates = []
    while current_date <= end_date:
        dates.append(current_date)
        current_date += timedelta(days=1)

    # A serial conversion of 12 years takes longer than the GitHub Actions
    # timeout. executor.map keeps the output ordered, so the ICS file remains
    # deterministic while conversions run in parallel.
    workers = os.cpu_count() or 1
    with ProcessPoolExecutor(max_workers=workers) as executor:
        zangli_dates = executor.map(get_zangli_date, dates, chunksize=16)
        for current_date, zangli_str in zangli_dates:
            if zangli_str is None:
                continue

            short_zangli_str = zangli_str.split("年")[-1] if "年" in zangli_str else zangli_str
            clean_date = short_zangli_str.replace("闰", "").replace("正月", "一月")
            
            events_today = []
            for date_key, names in CUSTOM_EVENTS.items():
                if clean_date == date_key.replace("正月", "一月"):
                    # 兼容多条和单条的写法
                    if isinstance(names, list):
                        events_today.extend(names)
                    else:
                        events_today.append(names)
            
            dtstart = current_date.strftime("%Y%m%d")
            next_date = current_date + timedelta(days=1)
            dtend = next_date.strftime("%Y%m%d")
            
            if events_today:
                for index, event_name in enumerate(events_today):
                    # 加上 index 序号，确保同一天的多个事件都能独立生成色块，不互相覆盖
                    uid = f"zangli-{dtstart}-{index}@mycalendar"
                    summary = f"{event_name} (${short_zangli_str})"
                    
                    ics_lines.extend([
                        "BEGIN:VEVENT",
                        f"UID:{uid}",
                        f"DTSTAMP:{dtstamp}",
                        f"DTSTART;VALUE=DATE:{dtstart}",
                        f"DTEND;VALUE=DATE:{dtend}",
                        f"SUMMARY:{summary}",
                        f"DESCRIPTION:公历 {current_date.strftime('%Y-%m-%d')}\n完整藏历: {zangli_str}\n\n(Data Powered by stonelf/zangli)",
                        "TRANSP:TRANSPARENT",
                        "END:VEVENT"
                    ])
            elif SHOW_DAILY_DATE:
                uid = f"zangli-{dtstart}-daily@mycalendar"
                summary = f"藏历 {short_zangli_str}"
                ics_lines.extend([
                    "BEGIN:VEVENT",
                    f"UID:{uid}",
                    f"DTSTAMP:{dtstamp}",
                    f"DTSTART;VALUE=DATE:{dtstart}",
                    f"DTEND;VALUE=DATE:{dtend}",
                    f"SUMMARY:{summary}",
                    f"DESCRIPTION:公历 {current_date.strftime('%Y-%m-%d')}\n完整藏历: {zangli_str}\n\n(Data Powered by stonelf/zangli)",
                    "TRANSP:TRANSPARENT",
                    "END:VEVENT"
                ])
    ics_lines.append("END:VCALENDAR")
    
    with open("zangli.ics", "w", encoding="utf-8", newline="") as f:
        f.write("\r\n".join(ics_lines) + "\r\n")
        
    print("✅ zangli.ics 已成功生成！")

if __name__ == "__main__":
    generate_ics()
