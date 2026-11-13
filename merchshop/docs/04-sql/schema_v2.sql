-- Схема v2: поддерживает остатки, брони, подарок, самовывоз, оплату и несколько позиций в заказе.
-- Синтаксис переносим между PostgreSQL, MySQL 8 и SQLite (проверено на SQLite в tests/test_sql.py).
-- Деньги хранятся как NUMERIC(10,2); время в UTC.

CREATE TABLE clients (
    id    INTEGER PRIMARY KEY,
    name  VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE products (
    id          INTEGER PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    price       NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    is_sellable INTEGER NOT NULL DEFAULT 1 CHECK (is_sellable IN (0, 1)),  -- 0: наклейки, только подарок
    is_gift     INTEGER NOT NULL DEFAULT 0 CHECK (is_gift IN (0, 1))
);

-- Физический остаток. Доступно = quantity - активные брони.
CREATE TABLE inventory (
    product_id INTEGER PRIMARY KEY REFERENCES products (id),
    quantity   INTEGER NOT NULL CHECK (quantity >= 0)
);

-- Бронь: строка корзины с таймером.
CREATE TABLE reservations (
    id         INTEGER PRIMARY KEY,
    client_id  INTEGER NOT NULL REFERENCES clients (id),
    product_id INTEGER NOT NULL REFERENCES products (id),
    quantity   INTEGER NOT NULL CHECK (quantity > 0),
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    status     VARCHAR(16) NOT NULL DEFAULT 'ACTIVE'
               CHECK (status IN ('ACTIVE', 'CONVERTED', 'EXPIRED', 'RELEASED'))
);
CREATE INDEX idx_reservations_active ON reservations (status, expires_at);
CREATE INDEX idx_reservations_product ON reservations (product_id, status);

CREATE TABLE orders (
    id           INTEGER PRIMARY KEY,
    client_id    INTEGER NOT NULL REFERENCES clients (id),
    status       VARCHAR(16) NOT NULL
                 CHECK (status IN ('PENDING_PAYMENT', 'PAID', 'READY', 'ISSUED', 'CANCELLED')),
    delivery     VARCHAR(16) NOT NULL DEFAULT 'PICKUP' CHECK (delivery = 'PICKUP'),   -- только самовывоз
    payment      VARCHAR(16) NOT NULL DEFAULT 'CARD'   CHECK (payment = 'CARD'),      -- только карта онлайн
    total_amount NUMERIC(10, 2) NOT NULL CHECK (total_amount >= 0),
    created_at   TIMESTAMP NOT NULL,
    paid_at      TIMESTAMP
);
CREATE INDEX idx_orders_created ON orders (created_at);

CREATE TABLE order_items (
    id         INTEGER PRIMARY KEY,
    order_id   INTEGER NOT NULL REFERENCES orders (id),
    product_id INTEGER NOT NULL REFERENCES products (id),
    quantity   INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10, 2) NOT NULL CHECK (unit_price >= 0),
    is_gift    INTEGER NOT NULL DEFAULT 0 CHECK (is_gift IN (0, 1))
);
CREATE INDEX idx_order_items_order ON order_items (order_id);
