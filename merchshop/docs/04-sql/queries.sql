-- ============================================================
-- Q0. Исходный запрос из задания (MySQL, схема schema_original.sql)
-- Имя клиента и сумма заказа по заказам за сегодня.
-- ============================================================
-- SELECT clients.name AS 'Имя', SUM(orders.total_amount) AS 'Сумма заказа'
-- FROM orders
-- JOIN clients ON orders.client_id = clients.id
-- WHERE DATE(orders.date) = CURDATE()
-- GROUP BY clients.name;
--
-- Замечания:
-- 1. GROUP BY clients.name склеивает разных клиентов с одинаковым именем. Группировать нужно по clients.id.
-- 2. Задача просит сумму КАЖДОГО заказа, а запрос суммирует заказы клиента. При двух заказах в день
--    клиент увидит одну строку с итогом, а не два заказа.
-- 3. DATE(orders.date) = CURDATE() не использует индекс по date. Эффективнее диапазон.
-- 4. Кавычки-апострофы вокруг псевдонимов нестандартны. Лучше двойные кавычки или без кавычек.

-- ============================================================
-- Q1. Заказы за сегодня, по одному на строку (схема schema_original.sql)
-- Параметры: :day_start (включительно), :day_end (исключая)
-- MySQL: :day_start = CURDATE(), :day_end = CURDATE() + INTERVAL 1 DAY
-- ============================================================
SELECT c.name         AS client_name,
       o.id           AS order_id,
       o.total_amount AS order_amount
FROM orders AS o
JOIN clients AS c ON c.id = o.client_id
WHERE o.date >= :day_start
  AND o.date <  :day_end
ORDER BY o.id;

-- ============================================================
-- Q2. Оплаченные заказы за сегодня и сумма по клиенту (схема v2)
-- ============================================================
SELECT c.id           AS client_id,
       c.name         AS client_name,
       COUNT(*)       AS orders_count,
       SUM(o.total_amount) AS paid_amount
FROM orders AS o
JOIN clients AS c ON c.id = o.client_id
WHERE o.status IN ('PAID', 'READY', 'ISSUED')
  AND o.created_at >= :day_start
  AND o.created_at <  :day_end
GROUP BY c.id, c.name
ORDER BY c.id;

-- ============================================================
-- Q3. Доступный остаток по товарам на момент :now (схема v2)
-- Доступно = физический остаток - активные неистёкшие брони
-- ============================================================
SELECT p.id AS product_id,
       p.name,
       i.quantity AS on_hand,
       COALESCE(SUM(r.quantity), 0) AS reserved,
       i.quantity - COALESCE(SUM(r.quantity), 0) AS available
FROM products AS p
JOIN inventory AS i ON i.product_id = p.id
LEFT JOIN reservations AS r
       ON r.product_id = p.id
      AND r.status = 'ACTIVE'
      AND r.expires_at > :now
GROUP BY p.id, p.name, i.quantity
ORDER BY p.id;

-- ============================================================
-- Q4. Брони к снятию: активные, но уже истёкшие (для фонового задания)
-- ============================================================
SELECT id, client_id, product_id, quantity, expires_at
FROM reservations
WHERE status = 'ACTIVE'
  AND expires_at <= :now
ORDER BY expires_at;

-- ============================================================
-- Q5. Атомарное резервирование (один запрос на заказанную позицию).
-- Если затронуто 0 строк, остатка недостаточно: вернуть 409.
-- Параметры: :product_id, :qty, :now
-- ============================================================
INSERT INTO reservations (client_id, product_id, quantity, created_at, expires_at, status)
SELECT :client_id, :product_id, :qty, :now, :expires_at, 'ACTIVE'
WHERE (
    SELECT i.quantity - COALESCE((
               SELECT SUM(r.quantity)
               FROM reservations AS r
               WHERE r.product_id = i.product_id
                 AND r.status = 'ACTIVE'
                 AND r.expires_at > :now
           ), 0)
    FROM inventory AS i
    WHERE i.product_id = :product_id
) >= :qty;
-- Важно: в PostgreSQL/MySQL выполнять в транзакции с блокировкой строки inventory
-- (SELECT ... FOR UPDATE) или на уровне изоляции SERIALIZABLE, иначе два параллельных запроса
-- могут пройти проверку одновременно.
