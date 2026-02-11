import streamlit as st
from datetime import date, timedelta

from src.db import init_db
from src.staff_repo import (
    add_staff, add_staff_bulk, list_staff, set_staff_active, delete_staff
)
from src.unavailability_repo import (
    add_unavailability_range, list_unavailability, delete_unavailability
)
from src.requests_repo import (
    add_request, list_requests, set_request_status, delete_request
)
from src.holidays_repo import (
    add_holidays, list_holidays, delete_holiday
)
from src.calendar_utils import (
    iter_month_days, count_weekdays_excluding_holidays
)
from src.blockers import build_blocked_days_with_type

from src.scheduler import build_required_shifts, SHIFT_HOURS, generate_schedule_hard_min_hours
from src.assignments_repo import clear_month, insert_assignments, list_month
from src.rules_repo import ensure_rules_table, add_rule, list_rules, set_rule_active, delete_rule

st.set_page_config(page_title="Nöbet Planlayıcı", layout="wide")
init_db()
ensure_rules_table()

st.title("Akıllı Nöbet / Vardiya Planlayıcı")

tab_staff, tab_unav, tab_req, tab_cal, tab_rules, tab_plan = st.tabs(
    ["👩‍⚕️ Personel", "🩺 Rapor / İzin", "📝 İstek Defteri", "📅 Takvim & Tatiller", "⚙️ Kurallar", "📋 Plan"]
)

# -------------------- PERSONEL --------------------
with tab_staff:
    st.subheader("Personel Yönetimi")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Tek Tek Ekle")
        name = st.text_input("Hemşire adı soyadı", placeholder="Örn: Ayşe Yılmaz")
        if st.button("Ekle", type="primary"):
            add_staff(name)
            st.success("Eklendi ✅")
            st.rerun()

        st.markdown("---")
        st.markdown("### Toplu Ekle (40 kişi için)")
        bulk = st.text_area(
            "Her satıra 1 isim yaz",
            height=200,
            placeholder="Ayşe Yılmaz\nElif Demir\n..."
        )
        if st.button("Toplu Ekle"):
            names = [n.strip() for n in bulk.splitlines() if n.strip()]
            count = add_staff_bulk(names)
            st.success(f"{count} kişi eklendi ✅")
            st.rerun()

    with col2:
        st.markdown("### Liste")
        filter_opt = st.radio("Filtre", ["Hepsi", "Aktif", "Pasif"], horizontal=True, key="staff_filter")

        only_active = None
        if filter_opt == "Aktif":
            only_active = True
        elif filter_opt == "Pasif":
            only_active = False

        rows = list_staff(only_active=only_active)

        if not rows:
            st.info("Henüz personel yok.")
        else:
            for r in rows:
                staff_id = int(r["id"])
                full_name = r["full_name"]
                is_active = bool(r["is_active"])

                c1, c2, c3 = st.columns([6, 2, 2])
                with c1:
                    st.write(f"**{full_name}**  (ID: {staff_id})")
                with c2:
                    if is_active:
                        if st.button("Pasif Yap", key=f"deact_{staff_id}"):
                            set_staff_active(staff_id, False)
                            st.rerun()
                    else:
                        if st.button("Aktif Yap", key=f"act_{staff_id}"):
                            set_staff_active(staff_id, True)
                            st.rerun()
                with c3:
                    if st.button("Sil", key=f"del_{staff_id}"):
                        delete_staff(staff_id)
                        st.rerun()

# -------------------- RAPOR / İZİN --------------------
with tab_unav:
    st.subheader("Rapor / Yıllık İzin (Çalışılamayan Günler)")

    staff_rows = list_staff(only_active=True)
    if not staff_rows:
        st.warning("Önce aktif personel eklemelisin.")
    else:
        staff_map = {f'{r["full_name"]} (ID:{r["id"]})': int(r["id"]) for r in staff_rows}
        selected_label = st.selectbox("Personel seç", list(staff_map.keys()), key="u_staff")
        staff_id = staff_map[selected_label]

        c1, c2 = st.columns(2)
        with c1:
            utype = st.selectbox("Tür", ["rapor", "yillik_izin"], key="u_type")
            note = st.text_input("Not (opsiyonel)", placeholder="Örn: okul / sağlık / özel durum", key="u_note")
        with c2:
            start = st.date_input("Başlangıç", value=date.today(), key="u_start")
            end = st.date_input("Bitiş", value=date.today(), key="u_end")

        if end < start:
            st.error("Bitiş tarihi başlangıçtan önce olamaz.")
        else:
            days = []
            cur = start
            while cur <= end:
                days.append(cur.isoformat())
                cur += timedelta(days=1)

            if st.button("Kaydet", type="primary", key="u_save"):
                add_unavailability_range(staff_id, days, utype, note)
                st.success(f"{len(days)} gün kaydedildi ✅")
                st.rerun()

        st.markdown("---")
        st.markdown("### Kayıtlar")
        filt = st.checkbox("Sadece seçili personeli göster", value=True, key="u_filt")
        rows = list_unavailability(staff_id if filt else None)

        if not rows:
            st.info("Kayıt yok.")
        else:
            for r in rows:
                rid = int(r["id"])
                extra = ((" | " + r["note"]) if r["note"] else "")
                st.write(f'**{r["date"]}** — {r["full_name"]} — `{r["type"]}`{extra}')
                if st.button("Sil", key=f"unav_del_{rid}"):
                    delete_unavailability(rid)
                    st.rerun()

# -------------------- İSTEK DEFTERİ --------------------
with tab_req:
    st.subheader("İstek Defteri (Okul / Eğitim / Çocuk / Özel Durum)")

    staff_rows = list_staff(only_active=True)
    if not staff_rows:
        st.warning("Önce aktif personel eklemelisin.")
    else:
        staff_map = {f'{r["full_name"]} (ID:{r["id"]})': int(r["id"]) for r in staff_rows}
        selected_label = st.selectbox("Personel seç (şimdilik login yerine)", list(staff_map.keys()), key="req_staff")
        staff_id = staff_map[selected_label]

        req_day = st.date_input("İstek günü", value=date.today() + timedelta(days=14), key="req_day")
        req_note = st.text_area(
            "İstek notu",
            height=120,
            placeholder="Örn: Okul var, o gün boş olsun / Eğitim var / Çocuk hastane randevusu…",
            key="req_note"
        )

        days_ahead = (req_day - date.today()).days
        if days_ahead < 14:
            st.warning(
                f"Bu istek {days_ahead} gün sonra. Kural: en az 14 gün önceden bildirim. "
                "Yine de kaydedilebilir, yönetici karar verir."
            )

        if st.button("İstek Kaydet", type="primary", key="req_save"):
            add_request(staff_id, req_day.isoformat(), req_note)
            st.success("İstek kaydedildi ✅")
            st.rerun()

        st.markdown("---")
        st.markdown("### Yönetici Görünümü (İstek Listesi)")

        status_label_map = {"Beklemede": "pending", "Onaylandı": "approved", "Reddedildi": "rejected"}
        status_tr_map = {"pending": "Beklemede", "approved": "Onaylandı", "rejected": "Reddedildi"}

        filter_status = st.radio(
            "Durum filtresi",
            ["Hepsi", "Beklemede", "Onaylandı", "Reddedildi"],
            horizontal=True,
            key="req_filter"
        )
        status = None if filter_status == "Hepsi" else status_label_map[filter_status]
        reqs = list_requests(status=status)

        if not reqs:
            st.info("İstek yok.")
        else:
            for r in reqs:
                rid = int(r["id"])
                st.write(f'**{r["date"]}** — {r["full_name"]} — **{status_tr_map.get(r["status"], r["status"])}**')
                st.caption(f'{r["note"]}  |  Oluşturma: {r["created_at"]}')
                c1, c2, c3 = st.columns([1, 1, 1])
                with c1:
                    if st.button("Onayla", key=f"req_ok_{rid}"):
                        set_request_status(rid, "approved")
                        st.rerun()
                with c2:
                    if st.button("Reddet", key=f"req_no_{rid}"):
                        set_request_status(rid, "rejected")
                        st.rerun()
                with c3:
                    if st.button("Sil", key=f"req_del_{rid}"):
                        delete_request(rid)
                        st.rerun()

# -------------------- TAKVİM & TATİLLER --------------------
with tab_cal:
    st.subheader("Takvim & Resmî Tatiller")

    today = date.today()
    c1, c2 = st.columns(2)
    with c1:
        year = st.number_input("Yıl", min_value=2020, max_value=2100, value=today.year, step=1, key="cal_year")
    with c2:
        month = st.selectbox("Ay", list(range(1, 13)), index=today.month - 1, key="cal_month")

    days = iter_month_days(int(year), int(month))
    st.caption(f"Seçilen ay gün sayısı: **{len(days)}**")

    holiday_list = list_holidays()
    holiday_set = set(holiday_list)

    st.markdown("### Ay günleri (Tatil seç)")
    options = [d.iso for d in days]
    default_selected = [d for d in options if d in holiday_set]
    selected_holidays = st.multiselect("Resmî tatiller", options=options, default=default_selected, key="cal_hols")

    if st.button("Tatil Kaydet", type="primary", key="cal_save"):
        for d in default_selected:
            delete_holiday(d)
        add_holidays(selected_holidays)
        st.success("Tatiller güncellendi ✅")
        st.rerun()

    st.markdown("---")
    weekday_count = count_weekdays_excluding_holidays(int(year), int(month), set(selected_holidays))
    min_month_hours = weekday_count * 8

    st.markdown("### Minimum aylık mesai hesabı")
    st.write(f"**Hafta içi gün sayısı (tatiller hariç):** {weekday_count}")
    st.write(f"**Minimum aylık mesai (hard):** {weekday_count} × 8 = **{min_month_hours} saat**")

# -------------------- KURALLAR (EKLE/SİL) --------------------
with tab_rules:
    st.subheader("Kural Yönetimi (PrevShift → NextShift yasak)")

    st.info("Buraya sadece 'YASAK' kuralları ekliyoruz. Serbest olanları eklemen gerekmez.")

    c1, c2, c3 = st.columns([2, 2, 4])
    with c1:
        prev_type = st.selectbox("Dün (Prev)", ["DAY", "NIGHT", "D24", "RAPOR", "YILLIK_IZIN", "ANY"], index=1)

    with c2:
        next_type = st.selectbox("Bugün (Next)", ["DAY", "NIGHT", "D24", "ANY"], index=3)
    with c3:
        apply_day = st.selectbox("Hangi günlerde geçerli?", ["ANY", "WEEKDAY", "WEEKEND"], index=0, key="rule_apply_day")

        note = st.text_input("Not (opsiyonel)", placeholder="Örn: 24 sonrası ertesi gün çalışma yok")

    if st.button("Kural Ekle", type="primary"):
        add_rule(prev_type, next_type, apply_day, note)

        st.success("Kural eklendi ✅")
        st.rerun()

    st.markdown("---")
    st.markdown("### Kural Listesi")

    filt = st.radio("Filtre", ["Hepsi", "Aktif", "Pasif"], horizontal=True, key="rules_filter_rules_tab")

    if filt == "Aktif":
        rows = list_rules(active_only=True)
    elif filt == "Pasif":
        rows = list_rules(active_only=False)
    else:
        rows = list_rules(active_only=None)

    if not rows:
        st.info("Henüz kural yok.")
    else:
        for r in rows:
            rid = int(r["id"])
            is_active = bool(r["is_active"])
            label = "✅ Aktif" if is_active else "⛔ Pasif"
            ad = r.get("apply_day", "ANY")
            st.write(f'**#{rid}**  {label}  —  `{r["prev_type"]} -> {r["next_type"]}`  (Gün: **{ad}**)  {(" | " + r["note"]) if r["note"] else ""}')


            b1, b2, b3 = st.columns([1, 1, 1])
            with b1:
                if is_active:
                    if st.button("Pasif Yap", key=f"rule_off_{rid}"):
                        set_rule_active(rid, False)
                        st.rerun()
                else:
                    if st.button("Aktif Yap", key=f"rule_on_{rid}"):
                        set_rule_active(rid, True)
                        st.rerun()
            with b2:
                if st.button("Sil", key=f"rule_del_{rid}"):
                    delete_rule(rid)
                    st.rerun()
            with b3:
                st.caption(r.get("created_at", ""))

# -------------------- PLAN --------------------
with tab_plan:
    st.subheader("Plan (Basit v0 + HARD min mesai + DB kuralları)")

    today = date.today()
    c1, c2 = st.columns(2)
    with c1:
        year = st.number_input("Yıl", min_value=2020, max_value=2100, value=today.year, step=1, key="p_year")
    with c2:
        month = st.selectbox("Ay", list(range(1, 13)), index=today.month - 1, key="p_month")

    staff_rows = list_staff(only_active=True)
    if not staff_rows:
        st.warning("Önce aktif personel eklemelisin.")
    else:
        staff_ids = [int(r["id"]) for r in staff_rows]
        staff_name_by_id = {int(r["id"]): r["full_name"] for r in staff_rows}

        required = build_required_shifts(int(year), int(month))
        st.caption(f"Bu ay toplam slot: **{len(required)}** (hafta içi 24 kişi/gün, hafta sonu 12 kişi/gün)")

        holiday_set = set(list_holidays())
        weekday_count = count_weekdays_excluding_holidays(int(year), int(month), holiday_set)
        min_required_hours = weekday_count * 8
        st.info(f"Hard kural: Her çalışan en az **{min_required_hours} saat** çalışmalı.")

        transition_rules = list_rules(active_only=True)
        st.write(f"Aktif geçiş kuralı sayısı: **{len(transition_rules)}**")

        if st.button("Plan Üret (Hard min)", type="primary", key="plan_btn"):
            blocked_any, blocked_type = build_blocked_days_with_type()

            assignments, unfilled, hours, swaps = generate_schedule_hard_min_hours(
           int(year), int(month), staff_ids, blocked_any, min_required_hours,
           transition_rules=transition_rules,
           blocked_type=blocked_type
        )


            clear_month(int(year), int(month))
            insert_assignments(assignments)

            if unfilled:
                st.warning(f"Doldurulamayan slot: {len(unfilled)} (kural çakışması / personel yetersizliği olabilir)")

            deficits = [sid for sid in staff_ids if hours.get(sid, 0) < min_required_hours]
            if deficits:
                st.error(
                    f"Hard min hedefi tam sağlanamadı. Eksi kalan kişi sayısı: {len(deficits)}. "
                    "Bu, mevcut kurallar ile %100 mümkün olmayabilir."
                )
            else:
                st.success(f"Plan kaydedildi ✅ (Dengeleme swap sayısı: {swaps})")

            st.rerun()

        st.markdown("---")
        st.markdown("### Plan çıktısı (gün gün)")

        rows = list_month(int(year), int(month))
        if not rows:
            st.info("Bu ay için plan yok. 'Plan Üret' butonuna bas.")
        else:
            st.markdown("### Mesai Özeti (kişi bazlı)")

            total_hours = {sid: 0 for sid in staff_ids}
            for r in rows:
                sid = int(r["staff_id"])
                total_hours[sid] += SHIFT_HOURS.get(r["shift_type"], 0)

            summary = []
            for sid in staff_ids:
                total = total_hours.get(sid, 0)
                diff = total - min_required_hours
                summary.append((staff_name_by_id.get(sid, f"ID:{sid}"), sid, total, min_required_hours, diff))

            summary.sort(key=lambda x: x[4])
            st.write("**Ad Soyad | ID | Toplam Saat | Minimum Saat | Fark (+fazla / -eksik)**")
            for name, sid, total, min_req, diff in summary:
                sign = "+" if diff > 0 else ""
                st.write(f"{name} | {sid} | {total} | {min_req} | {sign}{diff}")

            st.markdown("---")

            by_day = {}
            for r in rows:
                d = r["date"]
                stype = r["shift_type"]
                name = r["full_name"]
                by_day.setdefault(d, {}).setdefault(stype, []).append(name)

            day_infos = iter_month_days(int(year), int(month))
            weekday_names = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]

            for info in day_infos:
                d = info.iso
                w = weekday_names[info.weekday]
                is_weekend = info.is_weekend

                st.markdown(f"#### {d} ({w})" + (" — **Hafta sonu**" if is_weekend else ""))

                shifts = by_day.get(d, {})

                if is_weekend:
                    names_24 = sorted(shifts.get("D24", []))
                    st.write("**24 (08:00–08:00)**")
                    if names_24:
                        st.text("\n".join(names_24))
                    else:
                        st.warning("24 vardiyası boş.")
                else:
                    names_day = sorted(shifts.get("DAY", []))
                    names_night = sorted(shifts.get("NIGHT", []))

                    c1, c2 = st.columns(2)
                    with c1:
                        st.write("**Gündüz (08:00–16:00)**")
                        if names_day:
                            st.text("\n".join(names_day))
                        else:
                            st.warning("Gündüz boş.")
                    with c2:
                        st.write("**Gece (16:00–08:00)**")
                        if names_night:
                            st.text("\n".join(names_night))
                        else:
                            st.warning("Gece boş.")
