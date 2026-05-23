"""Page guard — clears session_state when switching between pages.

Prevents stale UI elements and form state from one page leaking into another.
"""
import streamlit as st

# --- CONFIGURATION ---
# รายการ Key ที่ต้องการเก็บไว้ถาวร ห้ามลบเด็ดขาด
_PROTECTED_KEYS = {
    "user",          # ข้อมูล User ที่ Login อยู่
    "settings",      # การตั้งค่าระบบ
    "theme",         # ธีมของ App
    "_current_page_id"
}

# Prefix ที่จะถูกยกเว้นจากการลบ (เช่น "__" สำหรับ internal variables)
_PROTECTED_PREFIXES = ("__",)

def enforce_page(page_id: str) -> None:
    """
    เรียกใช้ที่บรรทัดแรกของทุกหน้า (หลัง st.set_page_config)
    เพื่อล้าง Session State เมื่อมีการเปลี่ยนหน้า
    """
    last_page = st.session_state.get("_current_page_id")
    
    if last_page != page_id:
        # เก็บรายการ Key ทั้งหมดที่มีอยู่ในขณะนี้
        all_keys = list(st.session_state.keys())
        
        # คัดกรองเฉพาะ Key ที่ต้องลบ
        keys_to_clear = [
            k for k in all_keys
            if not k.startswith(_PROTECTED_PREFIXES)
            and k not in _PROTECTED_KEYS
        ]
        
        # ทำการลบ Key ที่เป็นค่าค้าง (Stale State)
        for k in keys_to_clear:
            try:
                del st.session_state[k]
            except KeyError:
                pass
        
        # อัปเดต ID หน้าปัจจุบัน
        st.session_state["_current_page_id"] = page_id
        
        # กรณีมีการเปลี่ยนหน้า ให้ทำการ Rerun เพื่อให้ UI สะอาดทันที
        # st.rerun() # เปิดใช้งานบรรทัดนี้หากพบว่า Widget หน้าเก่าแสดงผลแวบขึ้นมา