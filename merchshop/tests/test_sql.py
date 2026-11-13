import os
import re
import sqlite3
import unittest

SQL_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "04-sql")


def read(name):
    with open(os.path.join(SQL_DIR, name), encoding="utf-8") as f:
        return f.read()


def query_block(name):
    """Достаёт SQL-блок запроса Qn из queries.sql (без комментариев)."""
    text = read("queries.sql")
    parts = re.split(r"-- =+\n-- (Q\d+)\.", text)
    blocks = {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}
    lines = blocks[name].splitlines()[1:]  # первая строка: хвост заголовка "Qn. Название"
    body = "\n".join(l for l in lines if not l.strip().startswith("--"))
    return body.strip()


class LegacySchemaTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.executescript(read("schema_original.sql"))

    def test_q1_returns_two_orders_for_the_day(self):
        rows = self.db.execute(
            query_block("Q1"), {"day_start": "2026-05-25", "day_end": "2026-05-26"}
        ).fetchall()
        self.assertEqual(rows, [("Анна Петрова", 1001, 1500.0), ("Иван Смирнов", 1002, 800.0)])

    def test_q1_other_day(self):
        rows = self.db.execute(
            query_block("Q1"), {"day_start": "2026-05-24", "day_end": "2026-05-25"}
        ).fetchall()
        self.assertEqual(rows, [("Анна Петрова", 1003, 1500.0)])

    def test_original_query_merges_namesakes(self):
        """Демонстрация дефекта исходного запроса: GROUP BY по имени склеивает тёзок."""
        self.db.execute("INSERT INTO clients VALUES (3, 'Анна Петрова', 'other@mail.ru')")
        self.db.execute("INSERT INTO orders VALUES (1004, 3, 102, 800.00, '2026-05-25')")
        rows = self.db.execute(
            "SELECT c.name, SUM(o.total_amount) FROM orders o JOIN clients c ON o.client_id = c.id "
            "WHERE o.date = '2026-05-25' GROUP BY c.name ORDER BY c.name"
        ).fetchall()
        self.assertEqual(rows[0], ("Анна Петрова", 2300.0))  # две разные клиентки в одной строке


class V2SchemaTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(read("schema_v2.sql"))
        self.db.executescript(read("seed.sql"))

    def test_q2_paid_orders_per_client(self):
        rows = self.db.execute(
            query_block("Q2"), {"day_start": "2026-05-25", "day_end": "2026-05-26"}
        ).fetchall()
        # заказ 1004 в статусе PENDING_PAYMENT не учитывается
        self.assertEqual(rows, [(1, "Анна Петрова", 1, 2300.0), (2, "Иван Смирнов", 1, 800.0)])

    def test_q3_availability_ignores_expired_reservations(self):
        rows = self.db.execute(query_block("Q3"), {"now": "2026-05-25 12:10:00"}).fetchall()
        by_id = {r[0]: r for r in rows}
        self.assertEqual(by_id[101][4], 8)   # 10 - 2 активные
        self.assertEqual(by_id[102][4], 5)   # бронь Ивана истекла в 10:15
        self.assertEqual(by_id[103][4], 100)

    def test_q4_finds_expired_active_reservations(self):
        rows = self.db.execute(query_block("Q4"), {"now": "2026-05-25 12:10:00"}).fetchall()
        self.assertEqual([r[0] for r in rows], [2])

    def test_q5_atomic_reserve_succeeds_then_refuses(self):
        params = {"client_id": 2, "product_id": 102, "qty": 5,
                  "now": "2026-05-25 12:10:00", "expires_at": "2026-05-25 12:25:00"}
        q = query_block("Q5")
        self.assertEqual(self.db.execute(q, params).rowcount, 1)   # 5 из 5 доступных
        self.assertEqual(self.db.execute(q, params).rowcount, 0)   # остатка больше нет

    def test_pickup_and_card_only_constraints(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "INSERT INTO orders (id, client_id, status, delivery, total_amount, created_at) "
                "VALUES (2000, 1, 'PAID', 'COURIER', 100, '2026-05-25 10:00:00')"
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "INSERT INTO orders (id, client_id, status, payment, total_amount, created_at) "
                "VALUES (2001, 1, 'PAID', 'CASH', 100, '2026-05-25 10:00:00')"
            )


if __name__ == "__main__":
    unittest.main()
