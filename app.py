import streamlit as st
from datetime import date, timedelta

from src.db import init_db
from src.staff_repo import add_staff, add_staff_bulk, list_staff, set_staff_active, delete_staff
from src.unavailability_repo import add_unavailability_range, list_unavailability, delete_unavailability
from src.requests_repo import add_request, list_requests, set_request_status, delete_request

st.set_page_config(page_title="Nöbet Planlayıcı", layout="wide")
init_db()

st.title("Akıllı Nöbet / Vardiya Planlayıcı")


tab_staff, tab_unav, tab_req, tab_other = st.tabs(
    ["👩‍⚕️ Personel", "🩺 Rapor / İzin", "📝 İstek Defteri", "⚙️ Diğer (sonra)"]
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
            names = bulk.splitlines()
            count = add_staff_bulk(names)
            st.success(f"{count} kişi eklendi ✅")
            st.rerun()

    with col2:
        st.markdown("### Liste")
        filter_opt = st.radio("Filtre", ["Hepsi", "Aktif", "Pasif"], horizontal=True)
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
        selected_label = st.selectbox("Personel seç", list(staff_map.keys()))
        staff_id = staff_map[selected_label]

        c1, c2 = st.columns(2)
        with c1:
            utype = st.selectbox("Tür", ["rapor", "yillik_izin"])
            note = st.text_input("Not (opsiyonel)", placeholder="Örn: okul / sağlık / özel durum")
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
        filt = st.checkbox("Sadece seçili personeli göster", value=True)
        rows = list_unavailability(staff_id if filt else None)

        if not rows:
            st.info("Kayıt yok.")
        else:
            for r in rows:
                rid = int(r["id"])
                st.write(f'**{r["date"]}** — {r["full_name"]} — `{r["type"]}`  {(" | " + r["note"]) if r["note"] else ""}')
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
        req_note = st.text_area("İstek notu", height=120, placeholder="Örn: Okul var, o gün boş olsun / Eğitim var / Çocuk hastane randevusu…")

        days_ahead = (req_day - date.today()).days
        if days_ahead < 14:
            st.warning(f"Bu istek {days_ahead} gün sonra. Kural: en az 14 gün önceden bildirim. Yine de kaydedilebilir, yönetici karar verir.")

        if st.button("İstek Kaydet", type="primary"):
            add_request(staff_id, req_day.isoformat(), req_note)
            st.success("İstek kaydedildi ✅")
            st.rerun()

        st.markdown("---")
        
        st.markdown("### Yönetici Görünümü (İstek Listesi)")

        status_label_map = {
            "Beklemede": "pending",
            "Onaylandı": "approved",
            "Reddedildi": "rejected",
        }

        filter_status = st.radio(
            "Durum filtresi",
            ["Hepsi", "Beklemede", "Onaylandı", "Reddedildi"],
            horizontal=True
        )

        status = None if filter_status == "Hepsi" else status_label_map[filter_status]
        reqs = list_requests(status=status)

        if not reqs:
            st.info("İstek yok.")
        else:
            status_tr_map = {"pending": "Beklemede", "approved": "Onaylandı", "rejected": "Reddedildi"}

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


with tab_other:
    st.info("Sıradaki: Tatiller + Ay seçimi + Planlama algoritması + Raporlar")
