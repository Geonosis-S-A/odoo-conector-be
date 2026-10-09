from unittest.mock import patch

from app.shared.utils.ttl_cache import TtlCache


class TestTtlCache:
    def test_guarda_y_devuelve_el_valor(self):
        cache = TtlCache(60)
        cache.set("k", [1, 2])
        assert cache.get("k") == (True, [1, 2])

    def test_miss_si_no_existe(self):
        assert TtlCache(60).get("k") == (False, None)

    def test_distingue_valor_vacio_de_miss(self):
        cache = TtlCache(60)
        cache.set("k", [])
        assert cache.get("k") == (True, [])

    def test_vence_despues_del_ttl(self):
        cache = TtlCache(60)
        with patch("app.shared.utils.ttl_cache.time.monotonic", return_value=1000.0):
            cache.set("k", "v")
        with patch("app.shared.utils.ttl_cache.time.monotonic", return_value=1059.9):
            assert cache.get("k") == (True, "v")
        with patch("app.shared.utils.ttl_cache.time.monotonic", return_value=1060.1):
            assert cache.get("k") == (False, None)

    def test_ttl_cero_la_desactiva(self):
        cache = TtlCache(0)
        cache.set("k", "v")
        assert cache.enabled is False
        assert cache.get("k") == (False, None)

    def test_no_comparte_referencias_con_quien_la_usa(self):
        cache = TtlCache(60)
        original = [1, 2]
        cache.set("k", original)
        original.append(3)
        _, first = cache.get("k")
        first.append(99)
        assert cache.get("k") == (True, [1, 2])

    def test_no_crece_mas_alla_de_max_size(self):
        cache = TtlCache(60, max_size=3)
        for i in range(10):
            cache.set(i, i)
        assert len(cache._data) <= 3

    def test_clear_vacia_todo(self):
        cache = TtlCache(60)
        cache.set("k", "v")
        cache.clear()
        assert cache.get("k") == (False, None)
