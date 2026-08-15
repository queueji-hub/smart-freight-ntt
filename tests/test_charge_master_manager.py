import managers.charge_master_manager as charges


def test_get_charge_normalizes_code(monkeypatch):
    captured = {}

    class FakeCursor:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def execute(self, query, params=None):
            captured["query"] = query
            captured["params"] = params
        def fetchone(self):
            return None

    class FakeConn:
        def cursor(self):
            return FakeCursor()

    monkeypatch.setattr(charges, "get_connection", lambda: _Ctx(FakeConn()))
    monkeypatch.setattr(charges, "get_current_tenant_id", lambda: "t1")

    assert charges.get_charge(" thc ") is None
    assert captured["params"] == ("t1", "THC")


def test_list_charges_returns_empty_when_migration_is_not_applied(monkeypatch):
    class FakeCursor:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def execute(self, query, params=None):
            raise RuntimeError("relation charge_master does not exist")
        def fetchall(self):
            return []

    class FakeConn:
        def cursor(self):
            return FakeCursor()

    monkeypatch.setattr(charges, "get_connection", lambda: _Ctx(FakeConn()))
    monkeypatch.setattr(charges, "get_current_tenant_id", lambda: "t1")
    assert charges.list_charges() == []


class _Ctx:
    def __init__(self, value):
        self.value = value
    def __enter__(self):
        return self.value
    def __exit__(self, *args):
        return False
