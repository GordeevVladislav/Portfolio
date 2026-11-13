-- Исходная схема из задания (три таблицы). Оставлена для воспроизведения исходного запроса.
CREATE TABLE clients (
    id    INTEGER PRIMARY KEY,
    name  VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL
);

CREATE TABLE products (
    id    INTEGER PRIMARY KEY,
    name  VARCHAR(255) NOT NULL,
    price NUMERIC(10, 2) NOT NULL
);

CREATE TABLE orders (
    id           INTEGER PRIMARY KEY,
    client_id    INTEGER NOT NULL REFERENCES clients (id),
    product_id   INTEGER NOT NULL REFERENCES products (id),
    total_amount NUMERIC(10, 2) NOT NULL,
    date         DATE NOT NULL
);

INSERT INTO clients (id, name, email) VALUES
    (1, 'Анна Петрова', 'anna@mail.ru'),
    (2, 'Иван Смирнов', 'ivan@mail.ru');

INSERT INTO products (id, name, price) VALUES
    (101, 'Футболка', 1500.00),
    (102, 'Кружка',    800.00);

INSERT INTO orders (id, client_id, product_id, total_amount, date) VALUES
    (1001, 1, 101, 1500.00, '2026-05-25'),
    (1002, 2, 102,  800.00, '2026-05-25'),
    (1003, 1, 101, 1500.00, '2026-05-24');
