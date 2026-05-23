def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
    if not username or not password:
        return None
    
    pwd_hash = hash_password(password)
    username_clean = username.strip().lower()
    
    with get_connection() as conn:
        with conn.cursor() as cursor:
            # ใช้ RealDictCursor ที่เราตั้งค่าไว้ใน connection.py
            # มันจะคืนค่าเป็น Dictionary ให้เราโดยอัตโนมัติ ไม่ต้องจัดการ tuple เอง
            query = """
                SELECT id, username, full_name, email, role 
                FROM users 
                WHERE username=%s AND password_hash=%s AND is_active=1
            """
            cursor.execute(query, (username_clean, pwd_hash))
            user = cursor.fetchone()
            
            # ตรวจสอบว่าพบผู้ใช้หรือไม่
            if user:
                # ถ้า user เป็น RealDictRow (ซึ่งทำงานเหมือน dict) สามารถ return ได้เลย
                return dict(user) if hasattr(user, 'keys') else user
                
    return None