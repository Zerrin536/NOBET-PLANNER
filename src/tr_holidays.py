from datetime import date


def get_default_turkish_holiday_map(year: int, month: int) -> dict[str, str]:
    holiday_map: dict[str, str] = {}

    movable_fallbacks = {
        2026: {
            "2026-03-19": "Ramazan Bayrami Arefesi",
            "2026-03-20": "Ramazan Bayrami 1. Gun",
            "2026-03-21": "Ramazan Bayrami 2. Gun",
            "2026-03-22": "Ramazan Bayrami 3. Gun",
            "2026-05-26": "Kurban Bayrami Arefesi",
            "2026-05-27": "Kurban Bayrami 1. Gun",
            "2026-05-28": "Kurban Bayrami 2. Gun",
            "2026-05-29": "Kurban Bayrami 3. Gun",
            "2026-05-30": "Kurban Bayrami 4. Gun",
            "2026-10-28": "Cumhuriyet Bayrami Arefesi",
        }
    }

    fixed_holidays = {
        (1, 1): "Yilbasi",
        (4, 23): "23 Nisan Ulusal Egemenlik ve Cocuk Bayrami",
        (5, 1): "1 Mayis Emek ve Dayanisma Gunu",
        (5, 19): "19 Mayis Ataturk'u Anma, Genclik ve Spor Bayrami",
        (7, 15): "15 Temmuz Demokrasi ve Milli Birlik Gunu",
        (8, 30): "30 Agustos Zafer Bayrami",
        (10, 29): "29 Ekim Cumhuriyet Bayrami",
    }
    for (mm, dd), name in fixed_holidays.items():
        if mm == int(month):
            holiday_map[date(int(year), mm, dd).isoformat()] = name

    for iso_date, name in movable_fallbacks.get(int(year), {}).items():
        if int(iso_date[5:7]) == int(month):
            holiday_map[iso_date] = name

    try:
        import holidays

        tr_holidays = holidays.country_holidays("TR", years=int(year))
        for holiday_date, holiday_name in tr_holidays.items():
            if int(holiday_date.month) == int(month):
                holiday_map[holiday_date.isoformat()] = str(holiday_name)
    except Exception:
        pass

    return dict(sorted(holiday_map.items()))


def list_default_turkish_holidays(year: int, month: int) -> list[str]:
    return sorted(get_default_turkish_holiday_map(year, month).keys())
