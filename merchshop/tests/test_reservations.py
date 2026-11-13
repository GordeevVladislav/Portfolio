import os
import sys
import threading
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from merch_shop import (  # noqa: E402
    InsufficientStock, OutOfStock, Product, ProductNotFound,
    ReservationService, ReservedByOther, ValidationError, decide_gift,
)

T0 = datetime(2026, 5, 25, 14, 30, tzinfo=timezone.utc)


class FakeClock:
    def __init__(self):
        self.now = T0

    def __call__(self):
        return self.now

    def advance(self, **kw):
        self.now += timedelta(**kw)


def make(stock=None, clock=None):
    products = [
        Product(101, "Футболка", 1500_00),
        Product(102, "Кружка", 800_00),
        Product(103, "Наклейки", 0, is_gift=True),
    ]
    stock = stock or {101: 10, 102: 1, 103: 100}
    return ReservationService(products, stock, clock=clock or FakeClock())


class AddToCartTests(unittest.TestCase):
    def test_success_reserves_for_15_minutes(self):
        r = make().add_to_cart(1, 101, 1)
        self.assertEqual(r["status"], "success")
        self.assertEqual(r["item"]["reserved_until"], "2026-05-25T14:45:00Z")
        self.assertEqual(r["cart"], {"items_count": 1, "subtotal": 1500.0})

    def test_out_of_stock(self):
        svc = make({101: 0, 102: 1, 103: 5})
        with self.assertRaises(OutOfStock) as cm:
            svc.add_to_cart(1, 101, 1)
        self.assertEqual(cm.exception.http_status, 409)

    def test_insufficient_stock_reports_available(self):
        svc = make({101: 2, 102: 1, 103: 5})
        with self.assertRaises(InsufficientStock) as cm:
            svc.add_to_cart(1, 101, 3)
        self.assertEqual(cm.exception.extra["available"], 2)

    def test_reserved_by_other_returns_available_at(self):
        clock = FakeClock()
        svc = make(clock=clock)
        svc.add_to_cart(1, 102, 1)
        clock.advance(minutes=5)
        with self.assertRaises(ReservedByOther) as cm:
            svc.add_to_cart(2, 102, 1)
        self.assertEqual(cm.exception.extra["available_at"], "2026-05-25T14:45:00Z")

    def test_reservation_expires_after_15_minutes(self):
        clock = FakeClock()
        svc = make(clock=clock)
        svc.add_to_cart(1, 102, 1)
        clock.advance(minutes=15)  # ровно 15 минут: бронь уже не действует
        self.assertEqual(svc.available(102), 1)
        self.assertEqual(svc.add_to_cart(2, 102, 1)["status"], "success")

    def test_release_expired_counts_removed(self):
        clock = FakeClock()
        svc = make(clock=clock)
        svc.add_to_cart(1, 101, 1)
        clock.advance(minutes=16)
        self.assertEqual(svc.release_expired(), 1)

    def test_unknown_product(self):
        with self.assertRaises(ProductNotFound):
            make().add_to_cart(1, 999, 1)

    def test_gift_item_cannot_be_added_manually(self):
        with self.assertRaises(ValidationError):
            make().add_to_cart(1, 103, 1)

    def test_validation(self):
        for pid, qty in [(101, 0), (101, 11), (101, "1"), (101, True), (0, 1), ("101", 1)]:
            with self.subTest(pid=pid, qty=qty), self.assertRaises(ValidationError) as cm:
                make().add_to_cart(1, pid, qty)
            self.assertEqual(cm.exception.http_status, 422)

    def test_repeat_add_merges_and_resets_timer(self):
        clock = FakeClock()
        svc = make(clock=clock)
        svc.add_to_cart(1, 101, 1)
        clock.advance(minutes=10)
        r = svc.add_to_cart(1, 101, 2)
        self.assertEqual(r["item"]["quantity"], 3)
        self.assertEqual(r["item"]["reserved_until"], "2026-05-25T14:55:00Z")

    def test_client_holding_all_stock_gets_insufficient_not_crash(self):
        svc = make()
        svc.add_to_cart(1, 102, 1)
        with self.assertRaises(InsufficientStock) as cm:
            svc.add_to_cart(1, 102, 1)
        self.assertEqual(cm.exception.extra["available"], 0)

    def test_last_unit_race_has_exactly_one_winner(self):
        svc = make({101: 1, 102: 1, 103: 5})
        results, barrier = [], threading.Barrier(20)

        def worker(cid):
            barrier.wait()
            try:
                svc.add_to_cart(cid, 101, 1)
                results.append("ok")
            except ReservedByOther:
                results.append("reserved")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(1, 21)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(results.count("ok"), 1)
        self.assertEqual(results.count("reserved"), 19)
        self.assertEqual(svc.available(101), 0)


class GiftTests(unittest.TestCase):
    def test_boundary_2000_inclusive(self):
        self.assertTrue(decide_gift(2000_00, 5).applied)

    def test_1999_99_not_enough(self):
        d = decide_gift(1999_99, 5)
        self.assertFalse(d.applied)
        self.assertEqual(d.remaining_kopecks, 1)

    def test_no_stickers_in_stock(self):
        d = decide_gift(5000_00, 0)
        self.assertFalse(d.applied)
        self.assertEqual(d.reason, "NO_STOCK")

    def test_cart_response_shows_gift_progress(self):
        r = make().add_to_cart(1, 101, 1)
        self.assertFalse(r["gift"]["applied"])
        self.assertEqual(r["gift"]["remaining_amount"], 500.0)
        r = make().add_to_cart(1, 101, 2)  # 3000 руб.
        self.assertTrue(r["gift"]["applied"])
        self.assertEqual(r["gift"]["remaining_amount"], 0.0)


if __name__ == "__main__":
    unittest.main()
