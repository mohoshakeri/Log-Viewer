from datetime import datetime


GREGORIAN_MONTH_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
JALALI_MONTH_DAYS = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]


# ---------- Digit Normalization ----------
def normalize_digits(value: str) -> str:
    table = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    return value.translate(table)


# ---------- Calendar Conversion ----------
def jalali_to_gregorian(jy: int, jm: int, jd: int) -> tuple[int, int, int]:
    jy -= 979
    jm -= 1
    jd -= 1

    jalali_day_no = 365 * jy + (jy // 33) * 8 + ((jy % 33) + 3) // 4
    for month in range(jm):
        jalali_day_no += JALALI_MONTH_DAYS[month]
    jalali_day_no += jd

    gregorian_day_no = jalali_day_no + 79
    gy = 1600 + 400 * (gregorian_day_no // 146097)
    gregorian_day_no %= 146097

    leap = True
    if gregorian_day_no >= 36525:
        gregorian_day_no -= 1
        gy += 100 * (gregorian_day_no // 36524)
        gregorian_day_no %= 36524
        if gregorian_day_no >= 365:
            gregorian_day_no += 1
        else:
            leap = False

    gy += 4 * (gregorian_day_no // 1461)
    gregorian_day_no %= 1461

    if gregorian_day_no >= 366:
        leap = False
        gregorian_day_no -= 1
        gy += gregorian_day_no // 365
        gregorian_day_no %= 365

    month_days = GREGORIAN_MONTH_DAYS[:]
    if leap:
        month_days[1] = 29

    gm = 0
    while gm < 12 and gregorian_day_no >= month_days[gm]:
        gregorian_day_no -= month_days[gm]
        gm += 1

    return gy, gm + 1, gregorian_day_no + 1


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    gy -= 1600
    gm -= 1
    gd -= 1

    gregorian_day_no = 365 * gy + (gy + 3) // 4 - (gy + 99) // 100 + (gy + 399) // 400
    for month in range(gm):
        gregorian_day_no += GREGORIAN_MONTH_DAYS[month]
    if gm > 1 and ((gy + 1600) % 4 == 0 and ((gy + 1600) % 100 != 0 or (gy + 1600) % 400 == 0)):
        gregorian_day_no += 1
    gregorian_day_no += gd

    jalali_day_no = gregorian_day_no - 79
    j_np = jalali_day_no // 12053
    jalali_day_no %= 12053

    jy = 979 + 33 * j_np + 4 * (jalali_day_no // 1461)
    jalali_day_no %= 1461

    if jalali_day_no >= 366:
        jy += (jalali_day_no - 1) // 365
        jalali_day_no = (jalali_day_no - 1) % 365

    jm = 0
    while jm < 11 and jalali_day_no >= JALALI_MONTH_DAYS[jm]:
        jalali_day_no -= JALALI_MONTH_DAYS[jm]
        jm += 1

    return jy, jm + 1, jalali_day_no + 1


def parse_jalali_datetime(value: str, end_of_day: bool = False) -> datetime | None:
    if not value:
        return None
    cleaned = normalize_digits(value.strip()).replace("/", "-").replace("T", " ")
    date_part, _, time_part = cleaned.partition(" ")
    try:
        jy, jm, jd = [int(part) for part in date_part.split("-")]
        gy, gm, gd = jalali_to_gregorian(jy, jm, jd)
        if time_part:
            parts = [int(part) for part in time_part.split(":")]
            hour = parts[0] if len(parts) > 0 else 0
            minute = parts[1] if len(parts) > 1 else 0
            second = parts[2] if len(parts) > 2 else 0
        elif end_of_day:
            hour, minute, second = 23, 59, 59
        else:
            hour, minute, second = 0, 0, 0
        return datetime(gy, gm, gd, hour, minute, second)
    except Exception:
        return None


def format_jalali(dt: datetime | None) -> str | None:
    if not dt:
        return None
    jy, jm, jd = gregorian_to_jalali(dt.year, dt.month, dt.day)
    return f"{jy:04d}/{jm:02d}/{jd:02d} {dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}"
