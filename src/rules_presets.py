# src/rules_presets.py
from typing import Dict, List

from src.rules_repo import add_rule, list_rules, set_rule_active

# Kural formatı: prev_type -> next_type (apply_day: ANY/WEEKDAY/WEEKEND)
# Not: burada sadece "YASAK" geçişleri tanımlanır.

# Preset adları (TR):
# - Varsayılan
# - Katı
# - Esnek
PRESETS: Dict[str, List[Dict[str, str]]] = {
    "Varsayılan": [
        {"prev_type": "NIGHT", "next_type": "DAY", "apply_day": "ANY", "note": "Gece sonrası gündüz olmaz"},
        {"prev_type": "D24",   "next_type": "ANY", "apply_day": "ANY", "note": "24 saat sonrası ertesi gün çalışma yok"},
        {"prev_type": "RAPOR", "next_type": "ANY", "apply_day": "ANY", "note": "Rapor ertesi gün çalışamaz"},
        {"prev_type": "YILLIK_IZIN", "next_type": "ANY", "apply_day": "ANY", "note": "İzin ertesi gün çalışamaz"},
    ],
    "Katı": [
        {"prev_type": "NIGHT", "next_type": "DAY", "apply_day": "ANY", "note": "Gece sonrası gündüz olmaz"},
        {"prev_type": "D24",   "next_type": "ANY", "apply_day": "ANY", "note": "24 saat sonrası ertesi gün çalışma yok"},
        {"prev_type": "NIGHT", "next_type": "NIGHT", "apply_day": "ANY", "note": "Arka arkaya gece yok"},
        {"prev_type": "DAY",   "next_type": "NIGHT", "apply_day": "ANY", "note": "Gündüz sonrası gece yok"},
        {"prev_type": "RAPOR", "next_type": "ANY", "apply_day": "ANY", "note": "Rapor ertesi gün çalışamaz"},
        {"prev_type": "YILLIK_IZIN", "next_type": "ANY", "apply_day": "ANY", "note": "İzin ertesi gün çalışamaz"},
    ],
    "Esnek": [
        {"prev_type": "NIGHT", "next_type": "DAY", "apply_day": "ANY", "note": "Gece sonrası gündüz olmaz"},
        {"prev_type": "D24",   "next_type": "DAY", "apply_day": "ANY", "note": "24 saat sonrası ertesi gün gündüz olmaz"},
        {"prev_type": "RAPOR", "next_type": "ANY", "apply_day": "ANY", "note": "Rapor ertesi gün çalışamaz"},
        {"prev_type": "YILLIK_IZIN", "next_type": "ANY", "apply_day": "ANY", "note": "İzin ertesi gün çalışamaz"},
    ],
}

def _key(prev_type: str, next_type: str, apply_day: str) -> str:
    return f"{prev_type}|{next_type}|{apply_day}"

def apply_preset(preset_name: str, deactivate_others: bool = False) -> int:
    """
    Preset kurallarını DB'ye uygular:
    - yoksa ekler
    - varsa aktif eder
    - deactivate_others=True ise preset dışında kalan aktif kuralları pasif yapar
    Dönüş: değişen/etkilenen kural sayısı (yaklaşık)
    """
    rules = PRESETS.get(preset_name, [])
    if not rules:
        return 0

    existing = list_rules(active_only=None)
    by_key = {}
    for r in existing:
        k = _key(r["prev_type"], r["next_type"], r.get("apply_day","ANY"))
        by_key[k] = r

    touched = 0
    preset_keys = set()

    # preset kurallarını uygula
    for rr in rules:
        prev_type = rr["prev_type"]
        next_type = rr["next_type"]
        apply_day = rr.get("apply_day","ANY")
        note = rr.get("note","")
        k = _key(prev_type, next_type, apply_day)
        preset_keys.add(k)

        if k in by_key:
            rid = int(by_key[k]["id"])
            if not bool(by_key[k].get("is_active", 1)):
                set_rule_active(rid, True)
                touched += 1
        else:
            add_rule(prev_type, next_type, apply_day, note)
            touched += 1

    # preset dışındakileri pasif yap (isterse)
    if deactivate_others:
        for r in existing:
            k = _key(r["prev_type"], r["next_type"], r.get("apply_day","ANY"))
            if k not in preset_keys and bool(r.get("is_active", 1)):
                set_rule_active(int(r["id"]), False)
                touched += 1

    return touched
