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
    _init_session()
    u = current_user()

    st.markdown("### 🔐 Giriş")
    if u["role"] == "admin":
        st.success("Admin olarak giriş yapıldı ✅")
        if st.button("Çıkış", key="logout_btn"):
            logout()
            st.rerun()
        return

    if u["role"] == "staff":
        st.success(f'Personel olarak giriş yapıldı ✅  ({u["staff_name"]})')
        if st.button("Çıkış", key="logout_btn"):
            logout()
            st.rerun()
        return

    tabA, tabB = st.tabs(["👑 Admin", "👩‍⚕️ Personel"])
    with tabA:
        pw = st.text_input("Admin şifre", type="password", key="admin_pw")
        if st.button("Admin giriş", type="primary", key="admin_login_btn"):
            if login_admin(pw):
                st.success("Giriş başarılı ✅")
                st.rerun()
            else:
                st.error("Şifre yanlış ❌")

    with tabB:
        st.caption("PIN'i admin Personel sekmesinden görebilir. (Şimdilik demo)")
        pin = st.text_input("PIN (4 haneli)", max_chars=4, key="staff_pin")
        if st.button("Personel giriş", type="primary", key="staff_login_btn"):
            if login_staff(pin):
                st.success("Giriş başarılı ✅")
                st.rerun()
            else:
                st.error("PIN bulunamadı / pasif personel ❌")
