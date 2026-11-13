# 2. BPMN: добавление в корзину, бронь 15 минут, оформление и оплата

## 2.1 Диаграмма BPMN

![Исходная BPMN](../assets/bpmn-original.png)

Покрывает требования задания: проверка наличия, бронь на 15 минут, оформление заказа в срок, снятие брони по таймеру.


## 2.2 Диаграмма последовательности: гонка за последнюю единицу

```mermaid
sequenceDiagram
    participant A as Покупатель A
    participant B as Покупатель B
    participant API as POST /cart/add
    participant DB as Остатки
    A->>API: добавить товар 101 (остаток 1)
    B->>API: добавить товар 101 (остаток 1)
    API->>DB: UPDATE ... WHERE available >= 1 (A)
    DB-->>API: 1 строка изменена
    API-->>A: 200 OK, reserved_until
    API->>DB: UPDATE ... WHERE available >= 1 (B)
    DB-->>API: 0 строк изменено
    API-->>B: 409 PRODUCT_RESERVED, available_at
```
