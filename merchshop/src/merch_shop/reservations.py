"""Эталонная реализация POST /api/v1/cart/add: атомарная бронь на 15 минут.

Реализация в памяти для демонстрации логики и тестов. В продакшене те же правила
выполняются в транзакции БД (см. docs/04-sql/queries.sql, запрос Q5).
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, List, Optional

from .gifts import decide_gift

RESERVATION_TTL = timedelta(minutes=15)
MAX_QUANTITY = 10


# ---------- Ошибки (соответствуют docs/05-api/openapi.yaml) ----------

class ApiError(Exception):
    http_status = 500
    code = "INTERNAL"

    def __init__(self, message: str, **extra):
        super().__init__(message)
        self.message = message
        self.extra = extra

    def to_api(self) -> dict:
        return {"status": "error", "code": self.code, "message": self.message, **self.extra}


class ProductNotFound(ApiError):
    http_status, code = 404, "PRODUCT_NOT_FOUND"


class OutOfStock(ApiError):
    http_status, code = 409, "OUT_OF_STOCK"


class InsufficientStock(ApiError):
    http_status, code = 409, "INSUFFICIENT_STOCK"


class ReservedByOther(ApiError):
    http_status, code = 409, "RESERVED_BY_OTHER"


class ValidationError(ApiError):
    http_status, code = 422, "VALIDATION_ERROR"


# ---------- Модель ----------

@dataclass
class Product:
    id: int
    name: str
    price_kopecks: int
    is_gift: bool = False


@dataclass
class Reservation:
    client_id: int
    product_id: int
    quantity: int
    expires_at: datetime


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ReservationService:
    def __init__(
        self,
        products: List[Product],
        stock: Dict[int, int],
        clock: Optional[Callable[[], datetime]] = None,
    ):
        self._products = {p.id: p for p in products}
        self._stock = dict(stock)
        self._reservations: List[Reservation] = []
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._lock = threading.Lock()

    # ----- вспомогательные -----

    def _active(self, now: datetime) -> List[Reservation]:
        return [r for r in self._reservations if r.expires_at > now]

    def _reserved(self, product_id: int, now: datetime) -> int:
        return sum(r.quantity for r in self._active(now) if r.product_id == product_id)

    def available(self, product_id: int) -> int:
        now = self._clock()
        with self._lock:
            return self._stock.get(product_id, 0) - self._reserved(product_id, now)

    def release_expired(self) -> int:
        """Фоновое задание: удалить истёкшие брони. Возвращает число снятых."""
        now = self._clock()
        with self._lock:
            before = len(self._reservations)
            self._reservations = self._active(now)
            return before - len(self._reservations)

    # ----- основной метод -----

    def add_to_cart(self, client_id: int, product_id, quantity) -> dict:
        self._validate(product_id, quantity)
        now = self._clock()
        with self._lock:  # атомарность проверки и записи
            product = self._products.get(product_id)
            if product is None:
                raise ProductNotFound(f"Товар с id={product_id} не найден")
            if product.is_gift:
                raise ValidationError(
                    "Подарочный товар нельзя добавить вручную",
                    errors=[{"field": "product_id", "message": "gift item"}],
                )

            on_hand = self._stock.get(product_id, 0)
            reserved = self._reserved(product_id, now)
            available = on_hand - reserved

            if on_hand == 0:
                raise OutOfStock("Товара нет в наличии")
            if available <= 0:
                others = [
                    r.expires_at
                    for r in self._active(now)
                    if r.product_id == product_id and r.client_id != client_id
                ]
                if not others:  # весь остаток уже в корзине этого же клиента
                    raise InsufficientStock("Весь доступный остаток уже в вашей корзине", available=0)
                raise ReservedByOther(
                    "Товар зарезервирован другим покупателем", available_at=_iso(min(others))
                )
            if quantity > available:
                raise InsufficientStock(f"Доступно только {available} шт.", available=available)

            expires_at = now + RESERVATION_TTL
            mine = next(
                (r for r in self._active(now)
                 if r.client_id == client_id and r.product_id == product_id),
                None,
            )
            if mine:  # повторное добавление: суммируем и обновляем таймер
                mine.quantity += quantity
                mine.expires_at = expires_at
                total_qty = mine.quantity
            else:
                self._reservations.append(Reservation(client_id, product_id, quantity, expires_at))
                total_qty = quantity

            return self._response(client_id, product, total_qty, expires_at, now)

    # ----- ответ -----

    def _response(self, client_id, product, qty, expires_at, now) -> dict:
        items = [r for r in self._active(now) if r.client_id == client_id]
        subtotal = sum(
            r.quantity * self._products[r.product_id].price_kopecks
            for r in items
            if not self._products[r.product_id].is_gift
        )
        sticker_ids = [p.id for p in self._products.values() if p.is_gift]
        stickers = sum(self._stock.get(i, 0) - self._reserved(i, now) for i in sticker_ids)
        gift = decide_gift(subtotal, stickers)
        return {
            "status": "success",
            "message": "Товар добавлен в корзину",
            "item": {
                "product_id": product.id,
                "quantity": qty,
                "unit_price": product.price_kopecks / 100,
                "reserved_until": _iso(expires_at),
            },
            "cart": {"items_count": sum(r.quantity for r in items), "subtotal": subtotal / 100},
            "gift": gift.to_api(),
        }

    @staticmethod
    def _validate(product_id, quantity) -> None:
        errors = []
        if not isinstance(product_id, int) or isinstance(product_id, bool) or product_id < 1:
            errors.append({"field": "product_id", "message": "Должно быть положительным целым"})
        if (not isinstance(quantity, int) or isinstance(quantity, bool)
                or not 1 <= quantity <= MAX_QUANTITY):
            errors.append({"field": "quantity",
                           "message": f"Должно быть целым числом от 1 до {MAX_QUANTITY}"})
        if errors:
            raise ValidationError("Неверные параметры запроса", errors=errors)
