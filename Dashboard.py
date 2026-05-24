def bootstrap():
    try:
        init_database()
    except Exception as e:
        st.warning(f"DB not ready: {e}")
        return

    try:
        from managers.fx_manager import seed_default_rates
        seed_default_rates()
    except Exception:
        pass

    try:
        from managers.db_persistence import push_if_dirty
        push_if_dirty()
    except Exception:
        pass