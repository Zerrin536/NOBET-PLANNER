import streamlit as st
import io
import pandas as pd
from datetime import date, timedelta

from src.db import init_db
from src.exporter import export_schedule_xlsx
from src.staff_repo import (
    add_staff, add_staff_bulk, list_staff, set_staff_active, delete_staff
)
from src.unavailability_repo import (
    add_unavailability_range, list_unavailability, delete_unavailability, set_unavailability_status
)
from src.requests_repo import (
    add_request, list_requests, set_request_status, delete_request, list_approved_requests
)
from src.holidays_repo import (
    add_holidays, list_holidays, delete_holiday
)
from src.calendar_utils import (
    iter_month_days, count_weekdays_excluding_holidays
)
from src.blockers import build_blocked_days_with_type
from src.scheduler import build_required_shifts, SHIFT_HOURS, generate_schedule_hard_min_hours, validate_assignments
from src.assignments_repo import clear_month, insert_assignments, list_month
from src.rules_repo import ensure_rules_table, add_rule, list_rules, set_rule_active, update_rule, delete_rule
from src.rules_presets import PRESETS, apply_preset
from src.auth import login_panel, current_user, require_role


# ===== ROLE HELPERS (AUTO SYNC) =====
def _is_admin():
    return bool(st.session_state.get("admin_logged_in", False)) or str(st.session_state.get("role", "")).lower() == "admin"

# -------------------- ROLE HELPERS (FIXED) --------------------
def _role():
    return (st.session_state.get("user_role")
            or st.session_state.get("role")
            or ("staff" if st.session_state.get("staff_logged_in") else None)
            or ("admin" if st.session_state.get("admin_logged_in") else None)
            or "admin")

def _is_staff():
    return str(_role()).lower() == "staff"

def _is_admin():
    return not _is_staff()

# ===== /ROLE HELPERS =====

st.set_page_config(page_title="Nöbet Planlayıcı", layout="wide")

# --- AUTH HELPERS ---
def _role() -> str:
    return str(st.session_state.get("role") or st.session_state.get("auth_role") or "admin").lower()

def _staff_id() -> int | None:
    # Login sisteminin set edebileceği tüm olası anahtarlar
    v = (
        st.session_state.get("staff_id")
        or st.session_state.get("auth_staff_id")
        or st.session_state.get("current_staff_id")
        or st.session_state.get("sid")
    )
    try:
        return int(v) if v not in (None, "", 0, "0") else None
    except Exception:
        return None

def _is_staff() -> bool:
    return _role() == "staff"

def _deny_admin_only():
    st.error("⛔ Bu sayfa sadece **Yönetici** içindir.")
    return
# --- /AUTH HELPERS ---
init_db()

# ===== ROLE SYNC =====
# Admin her zaman öncelikli
if st.session_state.get("admin_logged_in", False):
    st.session_state["role"] = "admin"
else:
    # Staff login anahtarları
    sid = st.session_state.get("staff_id") or st.session_state.get("auth_staff_id") or st.session_state.get("current_staff_id")
    if st.session_state.get("staff_logged_in", False) or (sid not in (None, "", 0, "0")):
        st.session_state["staff_logged_in"] = True
        st.session_state["role"] = "staff"
# ===== /ROLE SYNC =====
ensure_rules_table()


# --- LOGIN PANEL ---
with st.sidebar:
    login_panel()
user = current_user()
# --- /LOGIN PANEL ---

st.title("Akıllı Nöbet / Vardiya Planlayıcı")

tab_staff, tab_unav, tab_req, tab_cal, tab_rules, tab_plan = st.tabs(
    ["👩‍⚕️ Personel", "🩺 Rapor / İzin", "📝 İstek Defteri", "📅 Takvim & Tatiller", "⚙️ Kurallar", "📋 Plan"]
)

# -------------------- PERSONEL --------------------
with tab_staff:
    if _is_staff():
        st.warning('⛔ Bu alan sadece **admin/yönetici** içindir.')
    else:
    
        if _is_staff():
            st.warning("⛔ Bu alan sadece **admin/yönetici** içindir.")
        else:
    
    
            if _is_staff():
                st.caption('👤 Staff modu aktif')
            elif _is_admin():
                st.caption('🛡️ Admin modu aktif')
            if _is_staff():
                st.error('⛔ Bu sayfa sadece **Yönetici** içindir.')
            else:
    
                if current_user().get('role') not in ('admin',):
                    st.warning('Bu alan sadece **admin** içindir.')
                    st.stop()
                st.subheader("Personel Yönetimi")
    
                col1, col2 = st.columns(2)
    
                with col1:
                    st.markdown("### Tek Tek Ekle")
                    name = st.text_input("Hemşire adı soyadı", placeholder="Örn: Ayşe Yılmaz", key="staff_name")
                    if st.button("Ekle", type="primary", key="staff_add_one"):
                        add_staff(name)
                        st.success("Eklendi ✅")
                        st.rerun()
    
                    st.markdown("---")
                    st.markdown("### Toplu Ekle (40 kişi için)")
                    bulk = st.text_area(
                        "Her satıra 1 isim yaz",
                        height=200,
                        placeholder="Ayşe Yılmaz\nElif Demir\n...",
                        key="staff_bulk"
                    )
                    if st.button("Toplu Ekle", key="staff_add_bulk"):
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
                                st.write(f"**{full_name}**  (ID: {staff_id})  |  PIN: `{(r['pin'] if hasattr(r, 'keys') and ('pin' in r.keys()) else '')}`")
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
    if _is_staff():
        st.info("👤 Staff modu: Burada sadece **kendi** rapor/izin kayıtlarını görürsün.")
        sid = _staff_id()
        if not sid:
            st.error("Staff ID bulunamadı. (Giriş tekrar deneyin)")
            st.stop()
    
        st.markdown("#### ➕ Rapor/İzin Talebi Ekle (Admin Onayı Bekler)")
        utype = st.selectbox("Tür", ["rapor", "yillik_izin"], index=0, key="staff_unav_type")
        d1 = st.date_input("Başlangıç", key="staff_unav_d1")
        d2 = st.date_input("Bitiş", key="staff_unav_d2")
        note = st.text_input("Not (opsiyonel)", key="staff_unav_note")
    
        if st.button("✅ Talebi Gönder", type="primary", key="staff_unav_submit"):
            try:
                import inspect
                from src.unavailability_repo import add_unavailability_range
    
                # d1-d2 aralığını gün listesine çevir (ISO string)
                try:
                    d1v = d1
                    d2v = d2
                    if hasattr(d1v, "isoformat") and hasattr(d2v, "isoformat"):
                        pass
                except Exception:
                    pass
    
                if d2 < d1:
                    st.error("Bitiş tarihi başlangıçtan küçük olamaz.")
                    st.stop()
    
                days = []
                cur = d1
                while cur <= d2:
                    days.append(cur.isoformat())
                    cur = cur + timedelta(days=1)
    
                sig = inspect.signature(add_unavailability_range)
                params = list(sig.parameters.keys())
                lower = [p.lower() for p in params]
    
                kw = {}
    
                # staff id
                for name in params:
                    if name.lower() in ("staff_id", "sid"):
                        kw[name] = sid
    
                # days (zorunlu)
                for name in params:
                    if name.lower() in ("days", "dates", "date_list", "day_list"):
                        kw[name] = days
    
                # type
                for name in params:
                    if name.lower() in ("utype", "type", "kind"):
                        kw[name] = utype
    
                # note (varsa)
                for name in params:
                    if name.lower() in ("note", "desc", "comment", "reason"):
                        kw[name] = (note or "").strip()

                for name in params:
                    if name.lower() == "status":
                        kw[name] = "pending"
    
                if kw:
                    add_unavailability_range(**kw)
                else:
                    # fallback: en yaygın positional: (sid, days, utype)
                    try:
                        add_unavailability_range(sid, days, utype, "", "pending")
                    except TypeError:
                        add_unavailability_range(sid, days)
    
                st.success("Talep kaydedildi ✅ (admin onayı bekleniyor)")
                st.rerun()
            except Exception as e:
                st.error(f"Kaydedilemedi: {e}")
    
    
        st.markdown("---")
        st.markdown("#### 📄 Benim Rapor/İzin Kayıtlarım")
    
        try:
            from src.unavailability_repo import list_unavailability
            rows = list_unavailability(None)  # bazı projelerde filtre paramı yok; sonra biz filtreleyeceğiz
            mine = []
            for r in (rows or []):
                try:
                    rr = dict(r)
                except Exception:
                    rr = r if isinstance(r, dict) else {}
                rid = rr.get("id")
                # staff_id alanı yoksa bile full_name bazlı karışmasın diye id yoksa es geç
                if int(rr.get("staff_id") or 0) == int(sid):
                    mine.append(rr)
    
            if not mine:
                st.info("Kayıt yok.")
            else:
                status_tr_map = {"pending": "⏳ Onay bekliyor", "approved": "✅ Onaylı", "rejected": "❌ Reddedildi"}
                for rr in mine:
                    extra = ((" | " + rr.get("note","")) if rr.get("note") else "")
                    status = status_tr_map.get(str(rr.get("status") or "approved").lower(), "✅ Onaylı")
                    st.write(f'**{rr.get("date","")}** — `{rr.get("type","")}` — {status}{extra}')
        except Exception as e:
            st.info("Kayıt yok.")
            st.caption(f"(Detay: {e})")
    else:
    
        if _is_staff():
            st.stop()
    
    
        if _is_staff():
            st.caption('👤 Staff modu aktif')
        elif _is_admin():
            st.caption('🛡️ Admin modu aktif')
        if current_user().get('role') not in ('admin',):
            st.warning('Bu alan sadece **admin** içindir.')
            st.stop()
        st.subheader("Rapor / Yıllık İzin (Çalışılamayan Günler)")
    
        staff_rows = list_staff(only_active=True)
    
        # ROLE_BASED_REQUESTS
        u = current_user()
        if u.get("role") == "staff":
            staff_id = int(u["staff_id"])
            st.info(f'Giriş yapan personel: **{u["staff_name"]}** (ID:{staff_id})')
    
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
                    add_unavailability_range(staff_id, days, utype, note, "approved")
                    st.success(f"{len(days)} gün kaydedildi ✅")
                    st.rerun()
    
            st.markdown("---")
            st.markdown("### Kayıtlar")
            filt = st.checkbox("Sadece seçili personeli göster", value=True, key="u_filt")
            rows = list_unavailability(staff_id if filt else None)
    
            if not rows:
                st.info("Kayıt yok.")
            else:
                status_tr_map = {
                    "pending": "Beklemede",
                    "approved": "Onaylandı",
                    "rejected": "Reddedildi",
                }
                for r in rows:
                    row = dict(r)
                    rid = int(r["id"])
                    extra = ((" | " + r["note"]) if r["note"] else "")
                    status = str(row.get("status") or "approved").lower()
                    st.write(
                        f'**{r["date"]}** — {r["full_name"]} — `{r["type"]}` — '
                        f'**{status_tr_map.get(status, status)}**{extra}'
                    )
                    c1, c2, c3 = st.columns([1, 1, 1])
                    with c1:
                        if status != "approved" and st.button("Onayla", key=f"unav_ok_{rid}"):
                            set_unavailability_status(rid, "approved")
                            st.rerun()
                    with c2:
                        if status != "rejected" and st.button("Reddet", key=f"unav_no_{rid}"):
                            set_unavailability_status(rid, "rejected")
                            st.rerun()
                    with c3:
                        if st.button("Sil", key=f"unav_del_{rid}"):
                            delete_unavailability(rid)
                            st.rerun()
    
    # -------------------- İSTEK DEFTERİ --------------------
with tab_req:
    if _is_staff():
        st.info("👤 Staff modu: Sadece **kendi** isteklerini ekleyebilir ve görüntüleyebilirsin.")
        sid = _staff_id()
    
        def _as_dict(x):
            try:
                return dict(x)
            except Exception:
                return x if isinstance(x, dict) else {}
    
        if not sid:
            st.warning("Staff ID bulunamadı. (Giriş yaptıysan çıkış yapıp tekrar dene)")
            st.stop()
    
        # --- İstek Kaydet ---
        st.markdown("#### ➕ İstek Kaydet")
        req_kind = st.selectbox("İstek tipi", ["HARD", "SOFT"], index=0, key="req_kind_staff")
        req_day = st.date_input("İstek günü", value=date.today() + timedelta(days=7), key="req_day_staff")
        req_note = st.text_area(
            "İstek notu (opsiyonel)",
            height=100,
            placeholder="Örn: O gün randevum var / Eğitim var / Çocuk okulu…",
            key="req_note_staff"
        )
    
        # geçmiş gün engeli
        try:
            if (req_day - date.today()).days < 0:
                st.error("Geçmiş gün için istek girilemez.")
        except Exception:
            pass
    
        if st.button("✅ İsteği Kaydet", type="primary", key="btn_add_req_staff"):
            try:
                from src.requests_repo import add_request

                day_iso = req_day.isoformat() if hasattr(req_day, "isoformat") else str(req_day)
                note2 = (req_note or "").strip()

                # ✅ İmza: (staff_id, day_iso, note, request_kind='HARD')
                add_request(int(sid), day_iso, note2, req_kind)

                st.success("İstek kaydedildi ✅ (admin değerlendirecek)")
                st.rerun()

            except Exception as e:
                st.error(f"Kaydedilemedi: {e}")
    
        st.markdown("---")
        st.markdown("#### 📄 Benim İsteklerim")
    
        try:
            from src.requests_repo import list_requests
    
            # farklı imza ihtimalleri
            try:
                rows = list_requests(active_only=None)
            except TypeError:
                rows = list_requests()
    
            mine = []
            for r in rows or []:
                d = _as_dict(r)
                rid = d.get("id") or d.get("request_id")
                staff_val = d.get("staff_id") or d.get("sid") or d.get("person_id") or d.get("employee_id")
                if str(staff_val or "") == str(sid):
                    mine.append(d)
    
            if not mine:
                st.info("Henüz istek yok.")
            else:
                import pandas as pd
                df = pd.DataFrame(mine)
    
                # kolonları düzenle (varsa)
                col_map = {}
                for c in df.columns:
                    lc = c.lower()
                    if lc in ("date", "day", "req_date", "request_date"):
                        col_map[c] = "Tarih"
                    elif lc in ("type", "kind", "req_type", "request_type"):
                        col_map[c] = "Tip"
                    elif lc in ("status", "state"):
                        col_map[c] = "Durum"
                    elif lc in ("note", "desc", "comment", "reason"):
                        col_map[c] = "Not"
                if col_map:
                    df = df.rename(columns=col_map)
    
                show_cols = [c for c in ["Tarih", "Tip", "Durum", "Not"] if c in df.columns]
                if show_cols:
                    df_show = df[show_cols].copy()
                else:
                    df_show = df.copy()
    
                st.dataframe(df_show, width="stretch", height=260)
    
                st.download_button(
                    "📄 Benim isteklerim (CSV)",
                    data=df_show.to_csv(index=False).encode("utf-8"),
                    file_name=f"isteklerim_{int(sid)}.csv",
                    mime="text/csv",
                    key="dl_my_requests_csv"
                )
        except Exception as e:
            st.info("Henüz istek yok.")
            st.caption(f"(Detay: {e})")
    else:
    
    
    
        if _is_staff():
            st.stop()
    
    
        if _is_staff():
            st.caption('👤 Staff modu aktif')
        elif _is_admin():
            st.caption('🛡️ Admin modu aktif')
        st.subheader("İstek Defteri (Okul / Eğitim / Çocuk / Özel Durum)")
    
        status_tr_map = {"pending": "Beklemede", "approved": "Onaylandı", "rejected": "Reddedildi"}
    
        # STAFF: sadece kendi isteğini ekle + kendi isteklerini gör
        if _is_staff():
            st.info("👤 Staff modu: Sadece **kendi** isteklerini ekleyebilir ve görüntüleyebilirsin.")
    
            sid = _staff_id()
            if sid is None:
                st.error("Staff ID bulunamadı (login).")
                st.stop()
    
            req_kind = st.selectbox("İstek tipi", ["HARD", "SOFT"], index=0, key="req_kind_staff")
            req_day = st.date_input("İstek günü", value=date.today() + timedelta(days=14), key="req_day_staff")
            req_note = st.text_area(
                "İstek notu",
                height=120,
                placeholder="Örn: Okul var, o gün boş olsun / Eğitim var / Çocuk randevusu…",
                key="req_note_staff"
            )
    
            days_ahead = (req_day - date.today()).days
            if days_ahead < 14:
                st.warning(
                    f"Bu istek {days_ahead} gün sonra. Kural: en az 14 gün önceden bildirim. "
                    "Yine de kaydedilebilir, yönetici karar verir."
                )
    
            if st.button("İstek Kaydet", type="primary", key="req_save_staff"):
                add_request(int(sid), req_day.isoformat(), req_note, req_kind)
                st.success("İstek kaydedildi ✅")
                st.rerun()
    
            st.markdown("---")
            st.markdown("### Benim İsteklerim")
    
            # Repo'da staff_id filtresi yoksa: tüm istekleri çekip filtreliyoruz
            all_reqs = list_requests(status=None)
            my_reqs = [r for r in all_reqs if int(r.get("staff_id", -1)) == int(sid)]
    
            if not my_reqs:
                st.info("Henüz isteğin yok.")
            else:
                for r in my_reqs:
                    rid = int(r["id"])
                    kind = (r.get("request_kind") or "HARD").upper()
                    st.write(
                        f'**{r["date"]}** — '
                        f'**{status_tr_map.get(r["status"], r["status"])}**  |  Tip: `{kind}`'
                    )
                    st.caption(f'{r["note"]}  |  Oluşturma: {r["created_at"]}')
    
                    # Staff: sadece kendi kaydını silebilsin
                    if st.button("Sil", key=f"req_del_staff_{rid}"):
                        delete_request(rid)
                        st.rerun()
    
            st.info("Not: Onaylı HARD istekler planlamada 'kesin boş' (hard). Onaylı SOFT istekler ise mümkünse boş bırakılır.")
    
        # ADMIN: eski yönetici ekranı
        else:
            staff_rows = list_staff(only_active=True)
            if not staff_rows:
                st.warning("Önce aktif personel eklemelisin.")
            else:
                staff_map = {f'{r["full_name"]} (ID:{r["id"]})': int(r["id"]) for r in staff_rows}
                selected_label = st.selectbox("Personel seç (şimdilik login yerine)", list(staff_map.keys()), key="req_staff")
                staff_id = staff_map[selected_label]
    
                req_kind = st.selectbox("İstek tipi", ["HARD", "SOFT"], index=0, key="req_kind")
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
                    add_request(staff_id, req_day.isoformat(), req_note, req_kind)
                    st.success("İstek kaydedildi ✅")
                    st.rerun()
    
                st.markdown("---")
                st.markdown("### Yönetici Görünümü (İstek Listesi)")
    
                status_label_map = {"Beklemede": "pending", "Onaylandı": "approved", "Reddedildi": "rejected"}
    
                filter_status = st.radio(
                    "Durum filtresi",
                    ["Hepsi", "Beklemede", "Onaylandı", "Reddedildi"],
                    horizontal=True,
                    key="req_filter_status"
                )
                status = None if filter_status == "Hepsi" else status_label_map[filter_status]
                reqs = list_requests(status=status)
    
                if not reqs:
                    st.info("İstek yok.")
                else:
                    for r in reqs:
                        rid = int(r["id"])
                        kind = (r.get("request_kind") or "HARD").upper()
                        st.write(
                            f'**{r["date"]}** — {r["full_name"]} — '
                            f'**{status_tr_map.get(r["status"], r["status"])}**  |  Tip: `{kind}`'
                        )
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
    
                st.info("Not: Onaylı HARD istekler planlamada 'kesin boş' (hard). Onaylı SOFT istekler ise mümkünse boş bırakılır.")
    
    # -------------------- TAKVİM & TATİLLER --------------------

with tab_cal:
    can_edit_calendar = not _is_staff()

    # DEBUG_TAB_CAL_TRY_GUARD
    # ADMIN ONLY: staff ise uyarı göster ve bu sekmeyi durdur
    if _is_staff():
        st.info("👤 Staff modu: Takvim ve resmi tatilleri görüntüleyebilirsin.")
        st.caption("Tatil ekleme ve değiştirme yetkisi sadece admin/yönetici hesabındadır.")

    st.markdown(
        """
        <style>
        .cal-shell {
            background: linear-gradient(135deg, #f7f2e8 0%, #fbfaf7 52%, #eef3ef 100%);
            border: 1px solid #ddd4c2;
            border-radius: 24px;
            padding: 22px 24px 10px 24px;
            margin-bottom: 18px;
        }
        .cal-kicker {
            font-family: "Avenir Next", "Segoe UI", sans-serif;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            font-size: 0.74rem;
            color: #7d6a4f;
            margin-bottom: 6px;
        }
        .cal-title {
            font-family: "Iowan Old Style", "Palatino Linotype", serif;
            font-size: 2rem;
            line-height: 1.1;
            color: #1f3328;
            margin: 0;
        }
        .cal-sub {
            font-family: "Avenir Next", "Segoe UI", sans-serif;
            color: #56665e;
            margin-top: 8px;
            margin-bottom: 0;
        }
        .cal-card {
            background: rgba(255, 255, 255, 0.72);
            border: 1px solid #e5ddd0;
            border-radius: 18px;
            padding: 16px 18px;
            min-height: 106px;
            margin-bottom: 12px;
            box-shadow: 0 8px 24px rgba(82, 64, 40, 0.05);
        }
        .cal-card-label {
            font-family: "Avenir Next", "Segoe UI", sans-serif;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 0.72rem;
            color: #876f56;
            margin-bottom: 8px;
        }
        .cal-card-value {
            font-family: "Iowan Old Style", "Palatino Linotype", serif;
            font-size: 1.7rem;
            color: #1f3328;
            line-height: 1;
            margin-bottom: 8px;
        }
        .cal-card-note {
            font-family: "Avenir Next", "Segoe UI", sans-serif;
            font-size: 0.92rem;
            color: #5b635d;
        }
        .cal-section-title {
            font-family: "Avenir Next", "Segoe UI", sans-serif;
            font-size: 1rem;
            font-weight: 700;
            color: #23342c;
            margin: 4px 0 10px 0;
        }
        .cal-legend {
            font-family: "Avenir Next", "Segoe UI", sans-serif;
            font-size: 0.9rem;
            color: #5a635d;
            margin-bottom: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    today = date.today()
    month_names = [
        "Ocak", "Subat", "Mart", "Nisan", "Mayis", "Haziran",
        "Temmuz", "Agustos", "Eylul", "Ekim", "Kasim", "Aralik"
    ]
    st.markdown(
        """
        <div class="cal-shell">
          <div class="cal-kicker">Takvim Yonetimi</div>
          <h2 class="cal-title">Takvim ve Resmi Tatiller</h2>
          <p class="cal-sub">Aylik takvimden tarih sec, resmi tatilleri guncelle ve minimum mesai etkisini aninda gor.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        year = st.number_input("Yıl", min_value=2020, max_value=2100, value=today.year, step=1, key="cal_year")
    with c2:
        month = st.selectbox("Ay", list(range(1, 13)), index=today.month - 1, key="cal_month", format_func=lambda m: month_names[m - 1])

    days = iter_month_days(int(year), int(month))
    holiday_set = set(list_holidays())
    options = [d.iso for d in days]
    default_selected = [d for d in options if d in holiday_set]

    if can_edit_calendar:
        st.session_state.setdefault("holiday_grid_selected", list(default_selected))
        st.session_state["holiday_grid_selected"] = [d for d in st.session_state["holiday_grid_selected"] if d in options]
        selected_set = set(st.session_state["holiday_grid_selected"])
    else:
        selected_set = set(default_selected)
    selected_holidays = sorted(selected_set)
    weekday_count = count_weekdays_excluding_holidays(int(year), int(month), set(selected_holidays))
    min_month_hours = weekday_count * 8

    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown(
            f"""
            <div class="cal-card">
              <div class="cal-card-label">Secili Donem</div>
              <div class="cal-card-value">{month_names[int(month) - 1]} {int(year)}</div>
              <div class="cal-card-note">{len(days)} gunluk takvim uzerinde calisiyorsun.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with s2:
        st.markdown(
            f"""
            <div class="cal-card">
              <div class="cal-card-label">Secili Tatil</div>
              <div class="cal-card-value">{len(selected_holidays)}</div>
              <div class="cal-card-note">Bu ay icin takvimde isaretli resmi tatil sayisi.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with s3:
        st.markdown(
            f"""
            <div class="cal-card">
              <div class="cal-card-label">Minimum Mesai</div>
              <div class="cal-card-value">{min_month_hours} saat</div>
              <div class="cal-card-note">Tatil disi hafta ici gunler uzerinden hesaplandi.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    left, right = st.columns([1.55, 0.95], gap="large")
    with left:
        st.markdown('<div class="cal-section-title">Aylik Takvim</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="cal-legend">Bir gunu secmek veya kaldirmak icin kutuya tikla. Kirmizi nokta tatil olarak isaretli gunu gosterir.</div>',
            unsafe_allow_html=True,
        )

        cols = st.columns(7)
        for i, lab in enumerate(["Pzt", "Sal", "Car", "Per", "Cum", "Cmt", "Paz"]):
            cols[i].markdown(f"**{lab}**")

        import datetime as _dt
        first = _dt.date(int(year), int(month), 1)
        start_pad = first.weekday()
        cells = [""] * start_pad + options[:]
        while len(cells) % 7 != 0:
            cells.append("")

        for r in range(0, len(cells), 7):
            row = st.columns(7)
            for c in range(7):
                d_iso = cells[r + c]
                if not d_iso:
                    row[c].write("")
                    continue

                day_num = int(d_iso.split("-")[2])
                is_sel = d_iso in selected_set
                is_weekend = c >= 5
                label = f"{'• ' if is_sel else ''}{day_num}"
                help_text = f"{d_iso} {'| Tatil secili' if is_sel else '| Normal gun'}{' | Hafta sonu' if is_weekend else ''}"

                if row[c].button(
                    label,
                    key=f"holbtn_{d_iso}",
                    use_container_width=True,
                    help=help_text,
                    disabled=not can_edit_calendar,
                ):
                    if d_iso in selected_set:
                        selected_set.remove(d_iso)
                    else:
                        selected_set.add(d_iso)
                    if can_edit_calendar:
                        st.session_state["holiday_grid_selected"] = sorted(selected_set)
                    st.rerun()

    with right:
        st.markdown('<div class="cal-section-title">Secili Tarihler</div>', unsafe_allow_html=True)
        if selected_holidays:
            for d_iso in selected_holidays:
                st.write(f"`{d_iso}`")
        else:
            st.info("Bu ay icin secili tatil yok.")

        st.markdown('<div class="cal-section-title">Hesap Ozeti</div>', unsafe_allow_html=True)
        st.write(f"Hafta ici gun: **{weekday_count}**")
        st.write(f"Minimum aylik mesai: **{min_month_hours} saat**")
        st.write(f"Takvimdeki toplam gun: **{len(days)}**")

        if st.button("Tatilleri Kaydet", type="primary", key="cal_save", use_container_width=True, disabled=not can_edit_calendar):
            for d in default_selected:
                delete_holiday(d)
            add_holidays(selected_holidays)
            st.success("Tatiller guncellendi.")
            st.rerun()

        if not can_edit_calendar:
            st.caption("Goruntuleme modundasin. Takvim degisiklikleri sadece admin tarafinda kaydedilir.")

    st.markdown("---")
    st.markdown("### Minimum aylik mesai hesabi")
    st.write(f"**Hafta ici gun sayisi (tatiller haric):** {weekday_count}")
    st.write(f"**Minimum aylik mesai (hard):** {weekday_count} x 8 = **{min_month_hours} saat**")


with tab_rules:
    # ADMIN ONLY: staff ise uyarı göster ve bu sekmeyi durdur
    if _is_staff():
        st.warning("⛔ Bu alan sadece **admin/yönetici** içindir.")
        st.caption("Personel hesabıyla giriş yaptın. Bu sekmeye erişim yok.")
    else:
        st.subheader("⚙️ Kurallar")
        st.info("Buraya sadece 'YASAK' kuralları ekliyoruz. Serbest olanları eklemen gerekmez.")

        # --- Preset seçimi ---
        st.markdown("### 🧩 Kural Seti Seç (Hazır Preset)")
        preset_name = st.selectbox(
            "Preset",
            list(PRESETS.keys()),
            index=0,
            key="preset_name"
        )

        default_deactivate = True if preset_name == "Katı" else False
        deactivate_others = st.checkbox(
            "Preset dışındaki aktif kuralları pasif yap (temiz set)",
            value=default_deactivate,
            key="preset_deactivate_others"
        )

        try:
            import pandas as pd
            df_p = pd.DataFrame(PRESETS.get(preset_name, []))
            if not df_p.empty:
                st.dataframe(df_p, width="stretch", height=180)
        except Exception:
            pass

        if st.button("✅ Preset'i Uygula", type="primary", key="apply_preset_btn"):
            touched = apply_preset(preset_name, deactivate_others=deactivate_others)
            st.success(f"Preset uygulandı ✅ (etkilenen kural: {touched})")
            st.rerun()

        st.markdown("---")
        st.markdown("### ➕ Manuel Kural Ekle")
        rule_prev_opts = ["DAY", "NIGHT", "D24", "ANY", "RAPOR", "YILLIK_IZIN"]
        rule_next_opts = ["DAY", "NIGHT", "D24", "ANY"]
        rule_day_opts = ["ANY", "WEEKDAY", "WEEKEND"]

        with st.form("rule_add_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                new_prev = st.selectbox("Önceki gün", rule_prev_opts, key="rule_new_prev")
            with c2:
                new_next = st.selectbox("Sonraki gün", rule_next_opts, key="rule_new_next")
            with c3:
                new_apply = st.selectbox("Uygulama günü", rule_day_opts, key="rule_new_apply")
            new_note = st.text_input("Açıklama", key="rule_new_note", placeholder="Örn: Gece sonrası gündüz yasak")
            submitted = st.form_submit_button("Kuralı Kaydet", type="primary")
            if submitted:
                add_rule(new_prev, new_next, new_apply, new_note)
                st.success("Kural kaydedildi ve aktif hale getirildi.")
                st.rerun()

        st.markdown("---")
        st.markdown("### 📋 Mevcut Kural Seti")
        all_rules = list_rules(active_only=None)
        active_count = sum(1 for r in all_rules if bool(r.get("is_active", 1)))
        passive_count = len(all_rules) - active_count
        st.caption(f"Toplam: {len(all_rules)} | Aktif: {active_count} | Pasif: {passive_count}")

        filter_mode = st.radio(
            "Liste filtresi",
            ["Aktifler", "Tümü", "Pasifler"],
            horizontal=True,
            key="rules_filter_mode",
        )

        if filter_mode == "Aktifler":
            shown_rules = [r for r in all_rules if bool(r.get("is_active", 1))]
        elif filter_mode == "Pasifler":
            shown_rules = [r for r in all_rules if not bool(r.get("is_active", 1))]
        else:
            shown_rules = all_rules

        if not shown_rules:
            st.info("Gösterilecek kural yok.")
        else:
            for r in shown_rules:
                rid = int(r["id"])
                is_active = bool(r.get("is_active", 1))
                status_label = "Aktif" if is_active else "Pasif"
                title = (
                    f'#{rid} | {r["prev_type"]} -> {r["next_type"]} | '
                    f'{r.get("apply_day","ANY")} | {status_label}'
                )
                with st.expander(title):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        edit_prev = st.selectbox(
                            "Önceki gün",
                            rule_prev_opts,
                            index=rule_prev_opts.index(r["prev_type"]) if r["prev_type"] in rule_prev_opts else 0,
                            key=f"rule_prev_{rid}",
                        )
                    with c2:
                        edit_next = st.selectbox(
                            "Sonraki gün",
                            rule_next_opts,
                            index=rule_next_opts.index(r["next_type"]) if r["next_type"] in rule_next_opts else 0,
                            key=f"rule_next_{rid}",
                        )
                    with c3:
                        apply_day_val = r.get("apply_day", "ANY")
                        edit_apply = st.selectbox(
                            "Uygulama günü",
                            rule_day_opts,
                            index=rule_day_opts.index(apply_day_val) if apply_day_val in rule_day_opts else 0,
                            key=f"rule_apply_{rid}",
                        )

                    edit_note = st.text_input("Açıklama", value=r.get("note", "") or "", key=f"rule_note_{rid}")
                    edit_active = st.checkbox("Aktif", value=is_active, key=f"rule_active_{rid}")

                    a1, a2, a3 = st.columns([1, 1, 1])
                    with a1:
                        if st.button("Kaydet", key=f"rule_save_{rid}", type="primary"):
                            update_rule(rid, edit_prev, edit_next, edit_apply, edit_note, edit_active)
                            st.success(f"Kural #{rid} güncellendi.")
                            st.rerun()
                    with a2:
                        toggle_label = "Pasife Al" if is_active else "Aktif Yap"
                        if st.button(toggle_label, key=f"rule_toggle_{rid}"):
                            set_rule_active(rid, not is_active)
                            st.rerun()
                    with a3:
                        if st.button("Sil", key=f"rule_delete_{rid}"):
                            delete_rule(rid)
                            st.rerun()

with tab_plan:
    try:
        # (DEBUG) role/staff_id
            if _is_staff():
                st.info("👤 Staff modu: Burada planı sadece **görüntüleyebilirsin**. Plan üretme admin işidir.")
                sid = _staff_id()
                if not sid:
                    st.error("Staff ID bulunamadı. (Giriş tekrar deneyin)")
                    st.stop()
    
                colA, colB = st.columns(2)
                with colA:
                    year_s = st.number_input("Yıl", min_value=2020, max_value=2100, value=int(date.today().year), step=1, key="staff_plan_year")
                with colB:
                    month_s = st.number_input("Ay", min_value=1, max_value=12, value=int(date.today().month), step=1, key="staff_plan_month")
    
                try:
                    from src.assignments_repo import list_month
                    rows = list_month(int(year_s), int(month_s)) or []
                except Exception as e:
                    st.error(f"Plan okunamadı: {e}")
                    rows = []
    
                if not rows:
                    st.info("Bu ay için plan yok.")
                else:
                    import pandas as pd
                    df = pd.DataFrame([dict(r) if not isinstance(r, dict) else r for r in rows])
                    staff_rows_all = list_staff(only_active=None)
                    staff_name_by_id_staff = {int(r["id"]): r["full_name"] for r in staff_rows_all}
                    name_to_id_staff = {v: k for k, v in staff_name_by_id_staff.items()}
                    day_infos_staff = iter_month_days(int(year_s), int(month_s))
                    day_isos_staff = [d.iso for d in day_infos_staff]
                    day_cols_staff = [str(int(d.iso.split("-")[2])).zfill(2) for d in day_infos_staff]

                    try:
                        unav_rows_staff = list_unavailability(None)
                    except Exception:
                        unav_rows_staff = []

                    month_prefix_staff = f"{int(year_s)}-{int(month_s):02d}-"
                    month_blocked_type_staff = {}
                    for raw in unav_rows_staff or []:
                        try:
                            ur = dict(raw)
                        except Exception:
                            ur = raw if isinstance(raw, dict) else {}
                        d_iso = str(ur.get("date") or ur.get("day") or "").split(" ")[0].split("T")[0]
                        if not d_iso.startswith(month_prefix_staff):
                            continue
                        if str(ur.get("status") or "approved").lower() != "approved":
                            continue
                        staff_val = ur.get("staff_id")
                        if staff_val is None:
                            continue
                        staff_val = int(staff_val)
                        t = ur.get("type") or ur.get("utype")
                        if t in ("rapor", "yillik_izin"):
                            month_blocked_type_staff.setdefault(staff_val, {})[d_iso] = t

                    cell_staff = {}
                    for rr in rows:
                        row_dict = dict(rr) if not isinstance(rr, dict) else rr
                        staff_val = row_dict.get("staff_id")
                        if staff_val is None:
                            staff_val = name_to_id_staff.get(row_dict.get("full_name"))
                        if staff_val is None:
                            continue
                        staff_val = int(staff_val)
                        d_iso = row_dict.get("date")
                        stype = row_dict.get("shift_type")
                        if not d_iso or not stype:
                            continue
                        key = (staff_val, d_iso)
                        if key in cell_staff and stype not in cell_staff[key].split("+"):
                            cell_staff[key] = cell_staff[key] + "+" + stype
                        else:
                            cell_staff.setdefault(key, stype)

                    matrix_rows_staff = []
                    visible_staff_ids = sorted({int(x) for x in df["staff_id"].dropna().astype(int).tolist()}) if "staff_id" in df.columns else [int(sid)]
                    for staff_val in visible_staff_ids:
                        row = {"Personel": staff_name_by_id_staff.get(int(staff_val), f"ID:{staff_val}"), "ID": int(staff_val)}
                        for d_iso, dcol in zip(day_isos_staff, day_cols_staff):
                            bt = month_blocked_type_staff.get(int(staff_val), {}).get(d_iso)
                            if bt == "rapor":
                                row[dcol] = "R"
                                continue
                            if bt == "yillik_izin":
                                row[dcol] = "İ"
                                continue
                            stype = cell_staff.get((int(staff_val), d_iso), "")
                            if stype.startswith("DAY"):
                                row[dcol] = "8"
                            elif stype.startswith("NIGHT"):
                                row[dcol] = "16"
                            elif stype.startswith("D24"):
                                row[dcol] = "24"
                            else:
                                row[dcol] = ""
                        matrix_rows_staff.append(row)

                    df_matrix_staff = pd.DataFrame(matrix_rows_staff)
                    if not df_matrix_staff.empty:
                        weekday_count_staff = count_weekdays_excluding_holidays(
                            int(year_s),
                            int(month_s),
                            set(list_holidays()),
                        )
                        min_required_hours_staff = weekday_count_staff * 8
                        HOURS_MAP = {"DAY": 8, "NIGHT": 16, "D24": 24}
                        worked_staff = {int(staff_val): 0 for staff_val in visible_staff_ids}
                        for rr in rows:
                            row_dict = dict(rr) if not isinstance(rr, dict) else rr
                            staff_val = row_dict.get("staff_id")
                            if staff_val is None:
                                staff_val = name_to_id_staff.get(row_dict.get("full_name"))
                            if staff_val is None:
                                continue
                            staff_val = int(staff_val)
                            stype = str(row_dict.get("shift_type") or "")
                            for part in stype.split("+"):
                                part = part.strip()
                                if part.startswith("DAY"):
                                    worked_staff[staff_val] = worked_staff.get(staff_val, 0) + HOURS_MAP["DAY"]
                                elif part.startswith("NIGHT"):
                                    worked_staff[staff_val] = worked_staff.get(staff_val, 0) + HOURS_MAP["NIGHT"]
                                elif part.startswith("D24"):
                                    worked_staff[staff_val] = worked_staff.get(staff_val, 0) + HOURS_MAP["D24"]

                        from datetime import date as _date
                        holiday_set_staff = set(list_holidays())
                        required_hours_staff = {}
                        note_staff = {}
                        for staff_val in visible_staff_ids:
                            report_days = 0
                            leave_days = 0
                            weekday_off = 0
                            for d_iso, off_type in (month_blocked_type_staff.get(int(staff_val), {}) or {}).items():
                                if off_type == "rapor":
                                    report_days += 1
                                elif off_type == "yillik_izin":
                                    leave_days += 1
                                try:
                                    dt_obj = _date.fromisoformat(str(d_iso)[:10])
                                    if dt_obj.weekday() < 5 and str(d_iso)[:10] not in holiday_set_staff and off_type in ("rapor", "yillik_izin"):
                                        weekday_off += 1
                                except Exception:
                                    pass
                            required_hours_staff[int(staff_val)] = max(0, int(min_required_hours_staff) - weekday_off * 8)
                            notes = []
                            if report_days:
                                notes.append(f"{report_days} gün raporlu")
                            if leave_days:
                                notes.append(f"{leave_days} gün yıllık izinli")
                            note_staff[int(staff_val)] = " | ".join(notes) if notes else ""

                        df_matrix_staff["GerekliMesaiSaati"] = df_matrix_staff["ID"].map(lambda x: int(required_hours_staff.get(int(x), min_required_hours_staff)))
                        df_matrix_staff["ToplamMesaiSaati"] = df_matrix_staff["ID"].map(lambda x: int(worked_staff.get(int(x), 0)))
                        df_matrix_staff["MesaiFarki"] = df_matrix_staff["ToplamMesaiSaati"] - df_matrix_staff["GerekliMesaiSaati"]
                        df_matrix_staff["Not"] = df_matrix_staff["ID"].map(lambda x: note_staff.get(int(x), ""))

                        st.markdown("#### 📊 Aylık Çizelge")
                        COLOR_DAY = "#2F75B5"
                        COLOR_NIGHT = "#C9A100"
                        COLOR_D24 = "#2E8B57"
                        COLOR_BLOCK = "#C00000"

                        def style_staff_matrix(data: pd.DataFrame):
                            styles = pd.DataFrame("", index=data.index, columns=data.columns)
                            for c in day_cols_staff:
                                for i in data.index:
                                    v = str(data.loc[i, c] or "")
                                    if v == "8":
                                        styles.loc[i, c] = f"color: {COLOR_DAY};"
                                    elif v == "16":
                                        styles.loc[i, c] = f"color: {COLOR_NIGHT};"
                                    elif v == "24":
                                        styles.loc[i, c] = f"color: {COLOR_D24};"
                                    elif v in ("R", "İ"):
                                        styles.loc[i, c] = f"color: {COLOR_BLOCK};"
                            return styles

                        df_matrix_staff = df_matrix_staff[
                            ["Personel", "ID"] + day_cols_staff + ["GerekliMesaiSaati", "ToplamMesaiSaati", "MesaiFarki", "Not"]
                        ]
                        st.dataframe(df_matrix_staff.style.apply(style_staff_matrix, axis=None), width="stretch", height=420)
                    else:
                        st.markdown("#### 📅 Aylık Plan")
                        st.dataframe(df, width="stretch", height=280)

                    # Kendi toplam saat
                    try:
                        from src.scheduler import SHIFT_HOURS
                        my = df[df["staff_id"].astype(int) == int(sid)].copy() if "staff_id" in df.columns else pd.DataFrame()
                        if not my.empty and "shift_type" in my.columns:
                            my["Saat"] = my["shift_type"].map(lambda x: int(SHIFT_HOURS.get(str(x), 8)))
                            total = int(my["Saat"].sum())
                            st.success(f"👤 Senin toplam çalışma saatin: **{total}** saat")
                        else:
                            st.info("Bu ay senin için atama bulunamadı.")
                    except Exception:
                        pass
    
                    export_df_staff = df_matrix_staff if 'df_matrix_staff' in locals() and not df_matrix_staff.empty else df
                    st.download_button(
                        "⬇️ Çizelgeyi indir (CSV)",
                        data=export_df_staff.to_csv(index=False).encode("utf-8"),
                        file_name=f"cizelge_{int(year_s)}_{int(month_s):02d}.csv",
                        mime="text/csv",
                        key="dl_staff_plan_csv"
                    )
            else:
    
                if _is_staff():
                    st.stop()
    
    
                if _is_staff():
                    st.caption('👤 Staff modu aktif')
                elif _is_admin():
                    st.caption('🛡️ Admin modu aktif')
                if current_user().get('role') not in ('admin',):
                    st.warning('Bu alan sadece **admin** içindir.')
                    st.stop()
                st.markdown(
                    """
                    <style>
                    .plan-shell {
                        background: linear-gradient(135deg, #eef3ea 0%, #fbfaf6 56%, #f5ece4 100%);
                        border: 1px solid #d8ddd2;
                        border-radius: 24px;
                        padding: 22px 24px 12px 24px;
                        margin-bottom: 18px;
                    }
                    .plan-kicker {
                        font-family: "Avenir Next", "Segoe UI", sans-serif;
                        letter-spacing: 0.14em;
                        text-transform: uppercase;
                        font-size: 0.74rem;
                        color: #6f775e;
                        margin-bottom: 6px;
                    }
                    .plan-title {
                        font-family: "Iowan Old Style", "Palatino Linotype", serif;
                        font-size: 2rem;
                        line-height: 1.1;
                        color: #203028;
                        margin: 0;
                    }
                    .plan-sub {
                        font-family: "Avenir Next", "Segoe UI", sans-serif;
                        color: #58635d;
                        margin-top: 8px;
                        margin-bottom: 0;
                    }
                    .plan-card {
                        background: rgba(255, 255, 255, 0.78);
                        border: 1px solid #e3ddd2;
                        border-radius: 18px;
                        padding: 16px 18px;
                        min-height: 106px;
                        box-shadow: 0 10px 28px rgba(65, 57, 40, 0.05);
                    }
                    .plan-card-label {
                        font-family: "Avenir Next", "Segoe UI", sans-serif;
                        text-transform: uppercase;
                        letter-spacing: 0.08em;
                        font-size: 0.72rem;
                        color: #84715e;
                        margin-bottom: 8px;
                    }
                    .plan-card-value {
                        font-family: "Iowan Old Style", "Palatino Linotype", serif;
                        font-size: 1.7rem;
                        color: #203028;
                        line-height: 1;
                        margin-bottom: 8px;
                    }
                    .plan-card-note {
                        font-family: "Avenir Next", "Segoe UI", sans-serif;
                        font-size: 0.92rem;
                        color: #5c635e;
                    }
                    </style>
                    <div class="plan-shell">
                      <div class="plan-kicker">Planlama Merkezi</div>
                      <h2 class="plan-title">Aylik Nobet Plani</h2>
                      <p class="plan-sub">Kurallar, onayli talepler ve rapor/izin kayitlariyla birlikte plani uret, kontrol et ve raporlarini ayni ekranda incele.</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

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

                    # ---- Onaylı istekler (HARD/SOFT) ----
                    st.markdown("---")
                    st.markdown("### ✅ Onaylı İstekler (HARD / SOFT)")
                    approved = list_approved_requests(int(year), int(month))
                    transition_rules = list_rules(active_only=True)

                    try:
                        raw_unav_rows = list_unavailability(None)
                    except Exception:
                        raw_unav_rows = []

                    month_prefix = f"{int(year)}-{int(month):02d}-"
                    month_blocked_type = {}
                    unav_count = 0
                    for raw in raw_unav_rows or []:
                        try:
                            ur = dict(raw)
                        except Exception:
                            ur = raw if isinstance(raw, dict) else {}
                        d = str(ur.get("date") or ur.get("day") or "").split(" ")[0].split("T")[0]
                        if not d.startswith(month_prefix):
                            continue
                        if str(ur.get("status") or "approved").lower() != "approved":
                            continue
                        sid = ur.get("staff_id")
                        if sid is None:
                            continue
                        sid = int(sid)
                        t = ur.get("type") or ur.get("utype")
                        if t not in ("rapor", "yillik_izin"):
                            continue
                        month_blocked_type.setdefault(sid, {})[d] = t
                        unav_count += 1

                    overview1, overview2, overview3 = st.columns(3)
                    with overview1:
                        st.markdown(
                            f"""
                            <div class="plan-card">
                              <div class="plan-card-label">Toplam Slot</div>
                              <div class="plan-card-value">{len(required)}</div>
                              <div class="plan-card-note">Secili ay icin uretilmesi gereken vardiya adedi.</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    with overview2:
                        st.markdown(
                            f"""
                            <div class="plan-card">
                              <div class="plan-card-label">Aktif Gecis Kurali</div>
                              <div class="plan-card-value">{len(transition_rules)}</div>
                              <div class="plan-card-note">Plan uretiminde su an devrede olan yasak kural sayisi.</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    with overview3:
                        st.markdown(
                            f"""
                            <div class="plan-card">
                              <div class="plan-card-label">Onayli Rapor / Izin</div>
                              <div class="plan-card-value">{unav_count}</div>
                              <div class="plan-card-note">Bu ay plani bloke eden onayli rapor ve yillik izin kaydi.</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    if not approved:
                        st.info("Bu ay için onaylı istek yok.")
                    else:
                        for r in approved:
                            kind = (r.get("request_kind") or "HARD").upper()
                            st.write(f'**{r["date"]}** — {r["full_name"]} — Tip: `{kind}`')
                            if r.get("note"):
                                st.caption(r["note"])
    
                    # ---- SOFT isteğe rağmen atananlar (şeffaflık) ----
                    st.markdown("### ⚠️ SOFT isteğe rağmen atananlar")
                    plan_rows_now = list_month(int(year), int(month))
                    if not plan_rows_now:
                        st.info("Önce plan üretince burada SOFT çatışmalarını göstereceğim.")
                    else:
                        assigned_set = {(r["date"], int(r["staff_id"])) for r in plan_rows_now}
                        soft_conflicts = []
                        for r in approved:
                            kind = (r.get("request_kind") or "HARD").upper()
                            if kind == "SOFT":
                                if (r["date"], int(r["staff_id"])) in assigned_set:
                                    soft_conflicts.append(r)
    
                        if not soft_conflicts:
                            st.success("SOFT isteklerle çakışan atama yok ✅ (mümkün olduğunca boş bırakıldı)")
                        else:
                            st.warning(f"SOFT isteğe rağmen atanan kişi sayısı: {len(soft_conflicts)}")
                            for r in soft_conflicts:
                                st.write(f'**{r["date"]}** — {r["full_name"]} — Tip: `SOFT` (ama atanmış)')
                                if r.get("note"):
                                    st.caption(r["note"])
    
                    st.write(f"Aktif geçiş kuralı sayısı: **{len(transition_rules)}**")
    
                    st.markdown("---")
                    st.markdown("### DOGRULAMA (VALID/INVALID)")
    
                    _val = st.session_state.get("last_validation")
                    if not _val:
                        st.info("Henüz doğrulama yok. Plan üretince burada otomatik kontrol göreceksin.")
                    else:
                        summary = _val.get("summary", {})
                        violations = _val.get("violations", [])
                        deficits = _val.get("deficits", [])
                        unfilled_n = _val.get("unfilled_count", None)
    
                        hard_ok = bool(summary.get("hard_ok", True))
                        min_ok  = bool(summary.get("min_hours_ok", True))
                        unfilled_ok = (unfilled_n == 0) if isinstance(unfilled_n, int) else None
    
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            st.success("Hard ihlal yok ✅" if hard_ok else "Hard ihlal var ❌")
                        with c2:
                            st.success("Min saat tuttu ✅" if min_ok else "Min saat tutmadi ❌")
                        with c3:
                            if unfilled_ok is None:
                                st.info("Unfilled bilgisi yok")
                            else:
                                st.success("Unfilled yok ✅" if unfilled_ok else "Unfilled var ❌")
    
                        if deficits:
                            st.warning("Min saat altinda kalan ID: " + ", ".join(str(x) for x in deficits))
    
                        if violations:
                            import pandas as pd
                            dfv = pd.DataFrame(violations)
                            st.dataframe(dfv, width="stretch", height=260)
                        else:
                            st.caption("Ihlal listesi: bos")
    
    
                    if st.button("Plan Üret (Hard min)", type="primary", key="plan_btn"):
                        blocked_any, blocked_type, soft_avoid = build_blocked_days_with_type(int(year), int(month))
    
                        # kişi-bazlı min saat: rapor/izin (hafta içi) kadar 8 saat düş
                        from datetime import date as _date
                        holiday_set_local = set(list_holidays())
                        off_weekday = {}
                        for sid in staff_ids:
                            cnt = 0
                            for d_iso, t in (blocked_type.get(sid, {}) or {}).items():
                                try:
                                    dt = _date.fromisoformat(str(d_iso)[:10])
                                    if dt.weekday() < 5 and str(d_iso)[:10] not in holiday_set_local:
                                        # rapor veya yıllık izin olan hafta içi gün -> min saatten düş
                                        if t in ('rapor','yillik_izin'):
                                            cnt += 1
                                # FIXED_OUT: except Exception:
                                # FIXED_OUT: pass
                                except Exception:
                                    pass
    
                            off_weekday[sid] = cnt
                        min_by_staff = {sid: max(0, int(min_required_hours) - off_weekday.get(sid,0)*8) for sid in staff_ids}
                        assignments, unfilled, unfilled_debug, hours, swaps = generate_schedule_hard_min_hours(
                            int(year), int(month), staff_ids, blocked_any, min_by_staff,
                            transition_rules=transition_rules,
                            blocked_type=blocked_type,
                            soft_avoid=soft_avoid
                        )
    
                        # --- VALIDATION hesapla (kalıcı) ---
                        try:
                            v_summary, v_violations, v_deficits = validate_assignments(
                                int(year), int(month),
                                assignments,
                                staff_ids,
                                blocked_any,
                                min_required_hours,
                                transition_rules=transition_rules,
                                blocked_type=blocked_type
                            )
                            st.session_state["last_validation"] = {
                                "summary": v_summary,
                                "violations": v_violations,
                                "deficits": v_deficits,
                                "unfilled_count": len(unfilled) if unfilled is not None else None,
                            }
                        # FIXED_OUT: except Exception as e:
                        # FIXED_OUT: st.session_state["last_validation"] = {
                        # FIXED_OUT: "summary": {"hard_ok": False, "min_hours_ok": False},
                        # FIXED_OUT: "violations": [{"type":"VALIDATION_ERROR","date":"","shift_type":"","staff_id":-1,"detail":str(e)}],
                        # FIXED_OUT: "deficits": [],
                        # FIXED_OUT: "unfilled_count": len(unfilled) if unfilled is not None else None,
                        # FIXED_OUT: }
                        # --- /VALIDATION ---
                        except Exception:
                            pass
    
    
                        clear_month(int(year), int(month))
                        if assignments and isinstance(assignments[0], (tuple, list)):
                            assignments = [{"date": a[0], "shift_type": a[1], "staff_id": a[2]} for a in assignments]
                        insert_assignments(assignments)
    
                        st.markdown("---")
    
                        # ✅ Unfilled raporu: ekranda kaybolmasın diye session_state'e yaz
                        st.session_state["last_unfilled"] = unfilled
                        st.session_state["last_unfilled_debug"] = unfilled_debug if 'unfilled_debug' in locals() else []
                        st.session_state["last_unfilled_year"] = int(year)
                        st.session_state["last_unfilled_month"] = int(month)
                        deficits = [sid for sid in staff_ids if hours.get(sid, 0) < int(min_by_staff.get(sid, min_required_hours))]
    
                        if deficits:
                            st.error(
                                f"Hard min hedefi tam sağlanamadı. Eksi kalan kişi sayısı: {len(deficits)}. "
                                "Bu, mevcut kurallar ile %100 mümkün olmayabilir."
                            )
                        else:
                            st.success(f"Plan kaydedildi ✅ (Dengeleme swap sayısı: {swaps})")
    
                        st.rerun()
    
                    st.markdown("---")
    
                    # ================== 🚫 Dolmayan Slotlar (Neden Raporu) ==================
                    st.markdown("---")
                    st.markdown("### 🚫 Dolmayan Slotlar (Neden Raporu)")
    
                    last_y = st.session_state.get("last_unfilled_year")
                    last_m = st.session_state.get("last_unfilled_month")
                    last_unfilled = st.session_state.get("last_unfilled")
                    last_debug = st.session_state.get("last_unfilled_debug")
    
                    if last_unfilled is None or last_y != int(year) or last_m != int(month):
                        st.info("Plan ürettikten sonra burada dolmayan slotlar ve nedeni görünecek.")
                    else:
                        if not last_unfilled:
                            st.success("Bu ay dolmayan slot yok ✅")
                        else:
                            st.warning(f"Doldurulamayan slot: {len(last_unfilled)} (kural çakışması / personel yetersizliği olabilir)")
    
                            # Debug varsa özet tablo
                            if last_debug:
                                df_unfilled = pd.DataFrame(last_debug)
                                g = df_unfilled.groupby(["date", "shift_type"], as_index=False).agg({
                                    "need": "sum",
                                    "assigned": "sum",
                                    "missing": "sum",
                                    "reason": "first",
                                }).sort_values(["date", "shift_type"])
    
                                st.dataframe(g, width="stretch", height=320)
                                st.download_button(
                                    "📄 Dolmayan slot raporu (CSV)",
                                    data=g.to_csv(index=False).encode("utf-8"),
                                    file_name=f"unfilled_{int(year)}_{int(month):02d}.csv",
                                    mime="text/csv",
                                    key="dl_unfilled_csv"
                                )
                            else:
                                df_unfilled = pd.DataFrame(last_unfilled)
                                if "day" in df_unfilled.columns:
                                    df_unfilled.rename(columns={"day": "date"}, inplace=True)
                                st.dataframe(df_unfilled, width="stretch", height=260)
                    # ================== /🚫 Dolmayan Slotlar ==================
    
                            st.markdown("### Plan çıktısı (gün gün)")
    
                    rows = list_month(int(year), int(month))
                    if not rows:
                        st.info("Bu ay için plan yok. 'Plan Üret' butonuna bas.")
                    else:
                        day_infos = iter_month_days(int(year), int(month))
                        day_isos = [d.iso for d in day_infos]
                        name_to_id = {v: k for k, v in staff_name_by_id.items()}
                        cell = {}
                        for r in rows:
                            row_dict = dict(r) if not isinstance(r, dict) else r
                            sid = row_dict.get("staff_id")
                            if sid is None:
                                sid = name_to_id.get(row_dict.get("full_name"))
                            if sid is None:
                                continue
                            sid = int(sid)
                            d_iso = row_dict.get("date")
                            stype = row_dict.get("shift_type")
                            if not d_iso or not stype:
                                continue
                            key = (sid, d_iso)
                            if key in cell and stype not in cell[key].split("+"):
                                cell[key] = cell[key] + "+" + stype
                            else:
                                cell.setdefault(key, stype)

                        # ===== 4+ GÜN BOŞLUK RAPORU =====
                        st.markdown("---")
                        st.markdown("### 💤 4+ Gün Boşluk Raporu")

                        off_runs = []
                        for sid in staff_ids:
                            run_start = None
                            run_len = 0
                            rapor_count = 0
                            izin_count = 0

                            for d_iso in day_isos:
                                worked_flag = (sid, d_iso) in cell
                                bt = month_blocked_type.get(sid, {}).get(d_iso)
                                is_off = (not worked_flag)

                                if is_off:
                                    if run_start is None:
                                        run_start = d_iso
                                        run_len = 1
                                        rapor_count = 1 if bt == "rapor" else 0
                                        izin_count = 1 if bt == "yillik_izin" else 0
                                    else:
                                        run_len += 1
                                        if bt == "rapor":
                                            rapor_count += 1
                                        elif bt == "yillik_izin":
                                            izin_count += 1
                                else:
                                    if run_start is not None and run_len >= 4:
                                        has_blocked = (rapor_count + izin_count) > 0
                                        detail = f"{rapor_count} gün rapor, {izin_count} gün yıllık izin" if has_blocked else "-"
                                        off_runs.append({
                                            "Personel": staff_name_by_id.get(sid, f"ID:{sid}"),
                                            "ID": sid,
                                            "Baslangic": run_start,
                                            "Bitis": (date.fromisoformat(d_iso) - timedelta(days=1)).isoformat(),
                                            "Gun": run_len,
                                            "AraliktaRaporIzinVar": "Evet" if has_blocked else "Hayır",
                                            "RaporGun": rapor_count,
                                            "YillikIzinGun": izin_count,
                                            "RaporIzinDetayi": detail,
                                        })
                                    run_start = None
                                    run_len = 0
                                    rapor_count = 0
                                    izin_count = 0

                            if run_start is not None and run_len >= 4:
                                has_blocked = (rapor_count + izin_count) > 0
                                detail = f"{rapor_count} gün rapor, {izin_count} gün yıllık izin" if has_blocked else "-"
                                off_runs.append({
                                    "Personel": staff_name_by_id.get(sid, f"ID:{sid}"),
                                    "ID": sid,
                                    "Baslangic": run_start,
                                    "Bitis": day_isos[-1],
                                    "Gun": run_len,
                                    "AraliktaRaporIzinVar": "Evet" if has_blocked else "Hayır",
                                    "RaporGun": rapor_count,
                                    "YillikIzinGun": izin_count,
                                    "RaporIzinDetayi": detail,
                                })

                        if not off_runs:
                            st.success("4+ gün boşluk yok ✅")
                        else:
                            df_off = pd.DataFrame(off_runs).sort_values(["Gun", "Personel"], ascending=[False, True])
                            st.warning(f"4+ gün boşluk bulunan kayıt sayısı: {len(df_off)}")
                            st.dataframe(df_off, width="stretch", height=260)
                            st.download_button(
                                "📄 4+ gün boşluk raporu (CSV)",
                                data=df_off.to_csv(index=False).encode("utf-8"),
                                file_name=f"bosluk_4plus_{int(year)}_{int(month):02d}.csv",
                                mime="text/csv",
                                key="dl_gap_csv"
                            )
                        # ===== /4+ GÜN BOŞLUK RAPORU =====
    
                        st.markdown("---")


                        st.markdown("### 📊 Aylık Çizelge (Sadece Yazı Rengi)")
                        st.caption(f"Bu ay rapor/izin kaydı: {unav_count}")
                        day_cols = [str(int(d.iso.split("-")[2])).zfill(2) for d in day_infos]
    
                        staff_df = pd.DataFrame(
                            [{"Personel": staff_name_by_id.get(sid, f"ID:{sid}"), "ID": sid} for sid in staff_ids]
                        ).sort_values(["Personel", "ID"]).reset_index(drop=True)
    
                        matrix_rows = []
                        for _, rr in staff_df.iterrows():
                            sid = int(rr["ID"])
                            row = {"Personel": rr["Personel"], "ID": sid}

                            for d_iso, dcol in zip(day_isos, day_cols):
                                bt = month_blocked_type.get(sid, {}).get(d_iso)
                                if bt == "rapor":
                                    row[dcol] = "R"
                                    continue
                                if bt == "yillik_izin":
                                    row[dcol] = "İ"
                                    continue
    
                                stype = cell.get((sid, d_iso), "")
                                if stype.startswith("DAY"):
                                    row[dcol] = "8"
                                elif stype.startswith("NIGHT"):
                                    row[dcol] = "16"
                                elif stype.startswith("D24"):
                                    row[dcol] = "24"
                                else:
                                    row[dcol] = ""
                            matrix_rows.append(row)
    
                        df_matrix = pd.DataFrame(matrix_rows)
    
                        aciklama = []
                        for sid in df_matrix["ID"].tolist():
                            sid = int(sid)
                            mp = month_blocked_type.get(sid, {})
                            rapor = sum(1 for _, t in mp.items() if t == "rapor")
                            izin  = sum(1 for _, t in mp.items() if t == "yillik_izin")
                            parts = []
                            if rapor:
                                parts.append(f"{rapor} gün raporlu")
                            if izin:
                                parts.append(f"{izin} gün izinli")
                            aciklama.append(" | ".join(parts) if parts else "")
                        df_matrix["Not"] = aciklama
    
                        min_required_hours = weekday_count * 8
    
                        HOURS_MAP = {"DAY": 8, "NIGHT": 16, "D24": 24}
    
                        worked = {sid: 0 for sid in staff_ids}
                        for rr in rows:
                            sid = rr.get("staff_id")
                            if sid is None:
                                sid = name_to_id.get(rr.get("full_name"))
                            if sid is None:
                                continue
                            sid = int(sid)
    
                            stype = (rr.get("shift_type") or "")
                            parts = str(stype).split("+")
                            for part in parts:
                                part = part.strip()
                                if part.startswith("DAY"):
                                    worked[sid] += HOURS_MAP["DAY"]
                                elif part.startswith("NIGHT"):
                                    worked[sid] += HOURS_MAP["NIGHT"]
                                elif part.startswith("D24"):
                                    worked[sid] += HOURS_MAP["D24"]
    
                        # kişi-bazlı MinSaat (çizelge): rapor/izin hafta içi gün * 8 düş
                        from datetime import date as _date
                        holiday_set_local = set(list_holidays())
                        min_by_staff_matrix = {}
                        for _sid in staff_ids:
                            _cnt = 0
                            for _d_iso, _t in (month_blocked_type.get(int(_sid), {}) or {}).items():
                                try:
                                    _dd = _date.fromisoformat(str(_d_iso)[:10])
                                    if _dd.weekday() < 5 and str(_d_iso)[:10] not in holiday_set_local:
                                        if _t in ('rapor','yillik_izin'):
                                            _cnt += 1
                                # FIXED_OUT: except Exception:
                                # FIXED_OUT: pass
                                except Exception:
                                    pass
    
                            min_by_staff_matrix[int(_sid)] = max(0, int(min_required_hours) - _cnt*8)
                        df_matrix["GerekliMesaiSaati"] = df_matrix["ID"].map(lambda x: int(min_by_staff_matrix.get(int(x), min_required_hours)))
                        df_matrix["ToplamMesaiSaati"] = df_matrix["ID"].map(lambda x: worked.get(int(x), 0))
                        df_matrix["MesaiFarki"] = df_matrix["ToplamMesaiSaati"] - df_matrix["GerekliMesaiSaati"]

                        ordered_cols = ["Personel", "ID"] + day_cols + ["GerekliMesaiSaati", "ToplamMesaiSaati", "MesaiFarki", "Not"]
                        df_matrix = df_matrix[ordered_cols]
    
                        COLOR_DAY   = "#2F75B5"
                        COLOR_NIGHT = "#C9A100"
                        COLOR_D24   = "#2E8B57"
                        COLOR_BLOCK = "#C00000"
    
                        def style_text_only(data: pd.DataFrame):
                            styles = pd.DataFrame("", index=data.index, columns=data.columns)
                            for c in day_cols:
                                for i in data.index:
                                    v = str(data.loc[i, c] or "")
                                    if v == "8":
                                        styles.loc[i, c] = f"color: {COLOR_DAY};"
                                    elif v == "16":
                                        styles.loc[i, c] = f"color: {COLOR_NIGHT};"
                                    elif v == "24":
                                        styles.loc[i, c] = f"color: {COLOR_D24};"
                                    elif v in ("R", "İ"):
                                        styles.loc[i, c] = f"color: {COLOR_BLOCK};"
                            return styles
    
                        styler = df_matrix.style.apply(style_text_only, axis=None)
                        st.dataframe(styler, width='stretch', height=680)
    
                        st.markdown("### ⬇️ Çizelgeyi İndir (CSV / Excel)")
                        st.download_button(
                            "📄 CSV indir (Çizelge)",
                            data=df_matrix.to_csv(index=False).encode("utf-8"),
                            file_name=f"cizelge_{int(year)}_{int(month):02d}.csv",
                            mime="text/csv",
                            key="dl_matrix_csv"
                        )
    
                        xlsx_bytes = export_schedule_xlsx(df_matrix, year=int(year), month=int(month))
                        st.download_button("📊 Excel indir (.xlsx)",
                                data=export_schedule_xlsx(df_matrix, int(year), int(month), sheet_name='Cizelge'),
                                file_name=f"cizelge_{int(year)}_{int(month):02d}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key="dl_matrix_xlsx"
                            )
                        # FIXED_OUT: except Exception as e:
                        # FIXED_OUT: st.warning(f"Excel export çalışmadı: {str(e)} (CSV her zaman çalışır)")
    
                        st.markdown("---")
                        st.caption("Not: Aşağıdaki eski uzun listeyi artık göstermiyoruz; çizelge yukarıda.")

    except Exception as e:
        st.error('Bu sekmede hata var (boş görünmesinin sebebi bu olabilir).')
        st.exception(e)
