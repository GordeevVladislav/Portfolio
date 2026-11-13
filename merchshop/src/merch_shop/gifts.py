"""Правило подарка: наклейки бесплатно при заказе от 2000 руб.

Деньги считаются в копейках (int), чтобы избежать ошибок округления float.
"""
from dataclasses import dataclass

GIFT_THRESHOLD_KOPECKS = 2000_00  # "от 2000" означает включительно


@dataclass(frozen=True)
class GiftDecision:
    applied: bool
    threshold_kopecks: int
    remaining_kopecks: int
    reason: str  # OK, BELOW_THRESHOLD, NO_STOCK

    def to_api(self) -> dict:
        return {
            "applied": self.applied,
            "threshold": self.threshold_kopecks / 100,
            "remaining_amount": self.remaining_kopecks / 100,
        }


def decide_gift(paid_subtotal_kopecks: int, stickers_available: int) -> GiftDecision:
    """Решает, выдавать ли подарок.

    paid_subtotal_kopecks: сумма платных товаров после скидок, без подарков.
    stickers_available: сколько наклеек можно выдать (остаток минус брони).
    """
    if paid_subtotal_kopecks < 0:
        raise ValueError("subtotal must be non-negative")
    remaining = max(0, GIFT_THRESHOLD_KOPECKS - paid_subtotal_kopecks)
    if remaining > 0:
        return GiftDecision(False, GIFT_THRESHOLD_KOPECKS, remaining, "BELOW_THRESHOLD")
    if stickers_available < 1:
        return GiftDecision(False, GIFT_THRESHOLD_KOPECKS, 0, "NO_STOCK")
    return GiftDecision(True, GIFT_THRESHOLD_KOPECKS, 0, "OK")
