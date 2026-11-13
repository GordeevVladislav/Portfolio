-- Тестовые данные для schema_v2.sql
INSERT INTO clients (id, name, email) VALUES
    (1, 'Анна Петрова', 'anna@mail.ru'),
    (2, 'Иван Смирнов', 'ivan@mail.ru');

INSERT INTO products (id, name, price, is_sellable, is_gift) VALUES
    (101, 'Футболка', 1500.00, 1, 0),
    (102, 'Кружка',    800.00, 1, 0),
    (103, 'Наклейки',    0.00, 0, 1);

INSERT INTO inventory (product_id, quantity) VALUES
    (101, 10),
    (102, 5),
    (103, 100);

-- Активная бронь Анны на 2 футболки, истёкшая бронь Ивана на кружку
INSERT INTO reservations (id, client_id, product_id, quantity, created_at, expires_at, status) VALUES
    (1, 1, 101, 2, '2026-05-25 12:00:00', '2026-05-25 12:15:00', 'ACTIVE'),
    (2, 2, 102, 1, '2026-05-25 10:00:00', '2026-05-25 10:15:00', 'ACTIVE');

INSERT INTO orders (id, client_id, status, total_amount, created_at, paid_at) VALUES
    (1001, 1, 'PAID',            2300.00, '2026-05-25 09:30:00', '2026-05-25 09:32:00'),
    (1002, 2, 'PAID',             800.00, '2026-05-25 11:00:00', '2026-05-25 11:02:00'),
    (1003, 1, 'PAID',            1500.00, '2026-05-24 18:00:00', '2026-05-24 18:01:00'),
    (1004, 2, 'PENDING_PAYMENT', 1500.00, '2026-05-25 12:05:00', NULL);

INSERT INTO order_items (id, order_id, product_id, quantity, unit_price, is_gift) VALUES
    (1, 1001, 101, 1, 1500.00, 0),
    (2, 1001, 102, 1,  800.00, 0),
    (3, 1001, 103, 1,    0.00, 1),   -- сумма платных 2300 >= 2000, подарок
    (4, 1002, 102, 1,  800.00, 0),
    (5, 1003, 101, 1, 1500.00, 0),
    (6, 1004, 101, 1, 1500.00, 0);
