-- Аналитические запросы к базе Marketplace (PostgreSQL)
-- Схема таблиц: data/schema.sql

-- 1. Каковы общий масштаб и базовые показатели эффективности: выручка, маржа в рублях, средняя маржа в процентах и средний срок оборота?
SELECT
    COUNT(*) AS sales_count,  --Общее количество продаж
    SUM(sale_price) AS revenue_rub,  --Общая выручка от продаж
    SUM(purchase_price) AS purchase_cost_rub,  --Общая стоимость закупки товаров
    SUM(sale_price - purchase_price) AS gross_margin_rub,  --Общая маржа в рублях
    ROUND(AVG((sale_price - purchase_price) / NULLIF(purchase_price, 0)::numeric *100),2) AS avg_sale_margin_pct,
    --Средняя процентная маржа одной продажи
    ROUND(AVG(sale_date::date - purchase_date::date),2) AS avg_turnover_days --Средний срок оборота товара в днях
FROM sales;

-- Маржа по категориям:
SELECT
    p.category, -- Категория товара
    COUNT(*) AS sales_count, -- Количество продаж
    ROUND(SUM(s.sale_price)::numeric, 2) AS revenue_rub, -- Общая выручка, ₽
    ROUND(SUM(s.sale_price - s.purchase_price)::numeric, 2) AS margin_rub, -- Общая маржа, ₽
    ROUND(AVG((s.sale_price - s.purchase_price)::numeric), 2) AS avg_margin_per_sale_rub, -- Средняя маржа с продажи, ₽
    ROUND(AVG((s.sale_price - s.purchase_price)::numeric / NULLIF(s.purchase_price, 0) * 100), 2) AS avg_margin_pct, -- Средняя маржа, %
    ROUND(AVG((s.sale_date::date - s.purchase_date::date)::numeric), 2) AS avg_turnover_days -- Средний срок оборота, дни
FROM sales s
JOIN products p ON p.product_id = s.product_id
GROUP BY p.category
ORDER BY margin_rub DESC;

-- Маржа по товарам внутри категорий:
SELECT
    p.category, -- Категория товара
    p.product_name, -- Название товара
    COUNT(*) AS sales_count, -- Количество продаж
    ROUND(SUM(s.sale_price - s.purchase_price)::numeric, 2) AS margin_rub, -- Общая маржа, ₽
    ROUND(AVG((s.sale_price - s.purchase_price)::numeric / NULLIF(s.purchase_price, 0) * 100), 2) AS avg_margin_pct, -- Средняя маржа с продажи, %
    ROUND(AVG((s.sale_date::date - s.purchase_date::date)::numeric), 2) AS avg_turnover_days, -- Средний срок оборота, дни
    RANK() OVER (PARTITION BY p.category ORDER BY SUM(s.sale_price - s.purchase_price) DESC) AS margin_rank_in_category -- Ранг по марже в категории
FROM sales s
JOIN products p ON p.product_id = s.product_id
GROUP BY p.category, p.product_name
ORDER BY p.category, margin_rank_in_category;

-- Маржа по брендам:
SELECT
    p.brand, -- Бренд товара
    COUNT(*) AS sales_count, -- Количество продаж
    ROUND(SUM(s.sale_price - s.purchase_price)::numeric, 2) AS margin_rub, -- Общая маржа, ₽
    ROUND(AVG((s.sale_price - s.purchase_price)::numeric / NULLIF(s.purchase_price, 0) * 100), 2) AS avg_margin_pct, -- Средняя маржа с продажи, %
    ROUND(AVG((s.sale_date::date - s.purchase_date::date)::numeric), 2) AS avg_turnover_days, -- Средний срок оборота, дни
    RANK() OVER (ORDER BY SUM(s.sale_price - s.purchase_price) DESC) AS margin_rank -- Ранг бренда по марже
FROM sales s
JOIN products p ON p.product_id = s.product_id
GROUP BY p.brand
ORDER BY margin_rank;

-- 3.Какие товары формируют 80% маржи (ABC-анализ)?
WITH product_margin AS (
    SELECT p.product_id, p.product_name, COUNT(*) AS sales_count, SUM(s.sale_price - s.purchase_price) AS margin_rub
    FROM sales s
    JOIN products p ON p.product_id = s.product_id
    GROUP BY p.product_id, p.product_name)
SELECT
    product_id, -- ID товара
    product_name, -- Название товара
    sales_count, -- Количество продаж
    ROUND(margin_rub::numeric, 2) AS margin_rub, -- Общая маржа, ₽
    ROUND(margin_rub::numeric / NULLIF(SUM(margin_rub) OVER (), 0) * 100, 2) AS margin_pct, -- Доля маржи товара, %
    ROUND(SUM(margin_rub) OVER (ORDER BY margin_rub DESC, product_name ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)::numeric / NULLIF(SUM(margin_rub) OVER (), 0) * 100, 2) AS cumulative_pct, -- Накопительная доля маржи, %
    CASE
        WHEN SUM(margin_rub) OVER (ORDER BY margin_rub DESC, product_name ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)::numeric / NULLIF(SUM(margin_rub) OVER (), 0) <= 0.80 THEN 'A'
        WHEN SUM(margin_rub) OVER (ORDER BY margin_rub DESC, product_name ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)::numeric / NULLIF(SUM(margin_rub) OVER (), 0) <= 0.95 THEN 'B'
        ELSE 'C'
    END AS abc_class -- ABC-класс товара
FROM product_margin
ORDER BY margin_rub DESC, product_name;

-- 4. Как менялись по месяцам количество продаж, выручка, маржа, срок оборота и число возвратов, есть ли тренд и сезонность?
WITH monthly AS (
    SELECT
        DATE_TRUNC('month', s.sale_date)::date AS sale_month, -- Месяц продажи
        COUNT(*) AS sales_count, -- Количество продаж
        ROUND(SUM(s.sale_price)::numeric, 2) AS revenue_rub, -- Выручка, ₽
        ROUND(SUM(s.sale_price - s.purchase_price)::numeric, 2) AS margin_rub, -- Общая маржа, ₽
        ROUND(AVG((s.sale_price - s.purchase_price)::numeric / NULLIF(s.purchase_price, 0) * 100), 2) AS avg_margin_pct, -- Средняя маржа, %
        ROUND(AVG((s.sale_date::date - s.purchase_date::date)::numeric), 2) AS avg_tur_days, -- Средний срок оборота, дни
        COUNT(DISTINCT r.return_id) AS returns_count -- Количество возвратов
    FROM sales s
    LEFT JOIN returns r ON r.sale_id = s.sale_id
    GROUP BY DATE_TRUNC('month', s.sale_date)::date
)
SELECT
    sale_month, -- Месяц
    sales_count, -- Количество продаж
    revenue_rub, -- Выручка, ₽
    margin_rub, -- Маржа, ₽
    avg_margin_pct, -- Средняя маржа, %
    avg_tur_days, -- Средний срок оборота, дни
    returns_count, -- Количество возвратов
    ROUND((margin_rub - LAG(margin_rub) OVER (ORDER BY sale_month))::numeric, 2) AS margin_ch_rub, -- Изменение маржи, ₽
    ROUND(AVG(margin_rub) OVER (ORDER BY sale_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)::numeric, 2) AS avg_3_mth_margin -- Скользящая средняя маржа за 3 месяца, ₽
FROM monthly
ORDER BY sale_month;

-- 5.Чем Б2Б отличается от Б2С по марже, сроку оборота и доле возвратов и как менялась доля каналов по месяцам?
-- Сравнение Б2Б и Б2С
SELECT
    c.customer_type AS client_type, -- Тип клиента
    COUNT(*) AS sales, -- Количество продаж
    ROUND(SUM(s.sale_price)::numeric, 2) AS revenue, -- Выручка, ₽
    ROUND(SUM(s.sale_price - s.purchase_price)::numeric, 2) AS margin, -- Общая маржа, ₽
    ROUND(AVG((s.sale_price - s.purchase_price)::numeric), 2) AS avg_margin, -- Средняя маржа с продажи, ₽
    ROUND(AVG((s.sale_price - s.purchase_price)::numeric / NULLIF(s.purchase_price, 0) * 100), 2) AS avg_margin_pct, -- Средняя маржа, %
    ROUND(AVG((s.sale_date::date - s.purchase_date::date)::numeric), 2) AS avg_days, -- Средний срок оборота, дни
    COUNT(DISTINCT r.return_id) AS returns, -- Количество возвратов
    ROUND(COUNT(DISTINCT r.return_id)::numeric / NULLIF(COUNT(DISTINCT s.sale_id), 0) * 100, 2) AS return_pct -- Доля возвратов, %
FROM sales s
JOIN customers c ON c.customer_id = s.customer_id
LEFT JOIN returns r ON r.sale_id = s.sale_id
GROUP BY c.customer_type
ORDER BY c.customer_type;

-- Доля каналов по месяцам
WITH monthly_channel AS (
    SELECT
        DATE_TRUNC('month', s.sale_date)::date AS month, -- Месяц
        c.customer_type AS client_type, -- Тип клиента
        COUNT(*) AS sales, -- Количество продаж
        ROUND(SUM(s.sale_price - s.purchase_price)::numeric, 2) AS margin -- Маржа, ₽
    FROM sales s
    JOIN customers c ON c.customer_id = s.customer_id
    GROUP BY DATE_TRUNC('month', s.sale_date)::date, c.customer_type
)
SELECT
    month, -- Месяц продажи
    client_type, -- B2B или B2C
    sales, -- Количество продаж
    margin, -- Общая маржа, ₽
    ROUND(sales::numeric / NULLIF(SUM(sales) OVER (PARTITION BY month), 0) * 100, 2) AS sales_pct, -- Доля продаж за месяц, %
    ROUND(margin / NULLIF(SUM(margin) OVER (PARTITION BY month), 0) * 100, 2) AS margin_pct -- Доля маржи за месяц, %
FROM monthly_channel
ORDER BY month, client_type;

-- 6. Различаются ли маркетплейсы и города пунктов выдачи по сроку доставки и общему сроку оборота?
SELECT
    sp.marketplace, -- Маркетплейс
    sp.pvz_city AS city, -- Город пункта выдачи
    COUNT(*) AS sales, -- Количество продаж
    ROUND(AVG(s.delivery_days)::numeric, 2) AS avg_delivery, -- Средняя доставка, дни
    ROUND(AVG((s.sale_date::date - s.purchase_date::date)::numeric), 2) AS avg_turnover -- Средний срок оборота, дни
FROM sales s
JOIN suppliers sp ON sp.supplier_id = s.supplier_id
GROUP BY sp.marketplace, sp.pvz_city
ORDER BY sp.marketplace, avg_delivery;

