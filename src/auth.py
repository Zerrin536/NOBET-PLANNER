# src/auth.py
from __future__ import annotations
import streamlit as st
from typing import Optional, Dict

def _as_dict_row(r):
    """sqlite3.Row -> dict (güvenli)"""
    try:
        return dict(r)
    except Exception:
        return r if isinstance(r, dict) else {}


from src.staff_repo import list_staff

ADMIN_PASSWORD = "admin1234"  # istersen sonra .env / settings'e alırız

def _init_session():
    st.session_state.setdefault("role", None)          # "admin" | "staff" | None
    st.session_state.setdefault("staff_id", None)      # int
    st.session_state.setdefault("staff_name", None)    # str

def logout():
    _init_session()
    st.session_state["role"] = None
    st.session_state["staff_id"] = None
    st.session_state["staff_name"] = None

def login_admin(password: str) -> bool:
    _init_session()
    if password == ADMIN_PASSWORD:
        st.session_state["role"] = "admin"
        st.session_state["staff_id"] = None
        st.session_state["staff_name"] = "ADMIN"
        return True
    return False

def login_staff(pin: str) -> bool:
    _init_session()
    pin = (pin or "").strip()
    if not pin:
        return False

    staff_rows = list_staff(only_active=True)
    for r0 in staff_rows:
        try:
            r = dict(r0)
        except Exception:
            r = r0 if isinstance(r0, dict) else {}

        if str((r.get("pin") or "")).zfill(4) == pin.zfill(4):
            st.session_state["role"] = "staff"
            st.session_state["staff_id"] = int(r.get("id") or 0) if (r.get("id") is not None) else None
            st.session_state["staff_name"] = r.get("full_name") or "STAFF"
            return True
    return False

    # aktif personel listesi içinde pin eşleştir
    staff_rows = list_staff(only_active=True)
    for r in staff_rows:
        r_row = _as_dict_row(r)
        if str(r_row.get("pin") or "").zfill(4) == pin.zfill(4):
            rr = _as_dict_row(r)
            # ✅ tek kaynak: rr dict
            st.session_state['role'] = 'staff'
            st.session_state['staff_id'] = int(rr.get('id') or rr.get('staff_id') or 0) or None
            st.session_state['staff_name'] = rr.get('full_name') or rr.get('name') or ''

            st.session_state["role"] = "staff"
            st.session_state["staff_id"] = int(r_row.get("id") or r_row.get("staff_id") or 0)
            st.session_state["staff_name"] = (r_row.get("full_name") or r_row.get("name") or "PERSONEL")
            return True
    return False

def current_user() -> Dict:
    _init_session()
    return {
        "role": st.session_state.get("role"),
        "staff_id": st.session_state.get("staff_id"),
        "staff_name": st.session_state.get("staff_name"),
    }

def require_role(*roles: str) -> bool:
    u = current_user()
    return u["role"] in roles



def login_panel():
    import streamlit as st
    import re as _re

    st.markdown("## 🔐 Giriş")

    tab_admin, tab_staff = st.tabs(["👑 Admin", "🧑‍⚕️ Personel"])

    # ---------------- ADMIN ----------------
    with tab_admin:
        admin_name = st.text_input("Admin kullanıcı adı (Ad Soyad)", key="admin_name", placeholder="Örn: Zerrin Aksoy")
        admin_pass = st.text_input("Admin şifre", type="password", key="admin_pass")

        if st.button("Admin giriş", key="btn_admin_login"):
            if not admin_pass:
                st.error("Admin şifre boş olamaz.")
            else:
                st.session_state["admin_logged_in"] = True
                st.session_state["staff_logged_in"] = False
                st.session_state["staff_id"] = None
                st.session_state["role"] = "admin"
                st.session_state["admin_display_name"] = (admin_name or "Admin").strip()
                st.success("Admin olarak giriş yapıldı ✅")
                st.rerun()

        if st.session_state.get("admin_logged_in"):
            st.caption(f"🛡️ Admin modu aktif: **{st.session_state.get('admin_display_name','Admin')}**")
            if st.button("Çıkış", key="btn_admin_logout"):
                for k in ["admin_logged_in","role","admin_display_name"]:
                    st.session_state.pop(k, None)
                st.rerun()

    # ---------------- STAFF ----------------
    with tab_staff:
        # Aktif personeli dropdown ile seç: yazım/harf hatası olmasın
        try:
            from src.staff_repo import list_staff
            staff_rows = list_staff(only_active=True) or []
        except Exception as e:
            staff_rows = []
            st.error(f"Personel listesi okunamadı: {e}")

        staff_map = {}
        for r in staff_rows:
            rr = dict(r) if not isinstance(r, dict) else r
            nm = (rr.get("full_name") or "").strip()
            sid = rr.get("id")
            if nm and sid is not None:
                staff_map[f"{nm} (ID:{sid})"] = rr

        if not staff_map:
            st.warning("Aktif personel yok. (Admin > Personel sekmesinden ekle)")
        else:
            selected = st.selectbox("Ad Soyad", list(staff_map.keys()), key="staff_login_select")
            pin = st.text_input("PIN (4 haneli)", type="password", key="staff_login_pin", placeholder="Örn: 1234")

            if st.button("Personel giriş", key="btn_staff_login"):
                pin = (pin or "").strip()
                if not _re.fullmatch(r"\d{4}", pin):
                    st.error("PIN 4 haneli sayı olmalı.")
                    st.stop()

                rr = staff_map[selected]
                db_pin = str(rr.get("pin") or "").strip()
                if db_pin != pin:
                    st.error("PIN hatalı.")
                    st.stop()

                st.session_state["admin_logged_in"] = False
                st.session_state["staff_logged_in"] = True
                st.session_state["role"] = "staff"
                st.session_state["staff_id"] = int(rr["id"])
                st.session_state["staff_name"] = (rr.get("full_name") or "").strip()
                st.success("Personel girişi başarılı ✅")
                st.rerun()

        # Giriş yaptıysa PIN değiştir göster
        if st.session_state.get("role") == "staff" and st.session_state.get("staff_id"):
            st.caption(f"👤 Giriş yapan: **{st.session_state.get('staff_name','')}** (ID:{st.session_state.get('staff_id')})")

            with st.expander("🔁 PIN Değiştir (4 haneli)", expanded=False):
                old_pin = st.text_input("Eski PIN", type="password", key="chg_old_pin")
                new_pin = st.text_input("Yeni PIN (4 haneli)", type="password", key="chg_new_pin")
                new_pin2 = st.text_input("Yeni PIN (tekrar)", type="password", key="chg_new_pin2")

                if st.button("PIN'i Güncelle", key="btn_change_pin"):
                    if not _re.fullmatch(r"\d{4}", (old_pin or "")):
                        st.error("Eski PIN 4 haneli olmalı.")
                        st.stop()
                    if not _re.fullmatch(r"\d{4}", (new_pin or "")):
                        st.error("Yeni PIN 4 haneli olmalı.")
                        st.stop()
                    if new_pin != new_pin2:
                        st.error("Yeni PIN'ler aynı değil.")
                        st.stop()

                    sid = int(st.session_state["staff_id"])

                    # DB'den eski PIN doğrula
                    try:
                        from src.staff_repo import list_staff
                        rows = list_staff(only_active=None) or []
                        me = None
                        for r in rows:
                            rr = dict(r) if not isinstance(r, dict) else r
                            if int(rr.get("id")) == sid:
                                me = rr
                                break
                        if not me:
                            st.error("Personel kaydı bulunamadı.")
                            st.stop()
                        if str(me.get("pin") or "").strip() != str(old_pin).strip():
                            st.error("Eski PIN yanlış.")
                            st.stop()
                    except Exception as e:
                        st.error(f"Kontrol edilemedi: {e}")
                        st.stop()

                    # Güncelle: repo fonksiyonu varsa kullan; yoksa sqlite ile güncelle
                    updated = False
                    try:
                        from src.staff_repo import set_staff_pin
                        set_staff_pin(sid, new_pin)
                        updated = True
                    except Exception:
                        pass

                    if not updated:
                        try:
                            import sqlite3
                            conn = sqlite3.connect("nobet_planner.sqlite3")
                            cur = conn.cursor()
                            cur.execute("UPDATE staff SET pin=? WHERE id=?", (new_pin, sid))
                            conn.commit()
                            conn.close()
                            updated = True
                        except Exception as e:
                            st.error(f"PIN güncellenemedi: {e}")
                            st.stop()

                    st.success("PIN güncellendi ✅")
                    st.rerun()

            if st.button("Çıkış", key="btn_staff_logout"):
                for k in ["staff_logged_in","role","staff_id","staff_name"]:
                    st.session_state.pop(k, None)
                st.rerun()


