CREATE TABLE products (
  product_id   INTEGER PRIMARY KEY,
  product_name TEXT NOT NULL UNIQUE,
  category     TEXT NOT NULL,
  brand        TEXT NOT NULL,
  memory_gb    INTEGER CHECK (memory_gb IS NULL OR memory_gb IN (128,256,512,1024,2048))
)
CREATE TABLE customers (
  customer_id   INTEGER PRIMARY KEY,
  customer_name TEXT NOT NULL,                       
  customer_type TEXT NOT NULL CHECK (customer_type IN ('Б2Б','Б2С')),
  city          TEXT NOT NULL
)
CREATE TABLE suppliers (
  supplier_id INTEGER PRIMARY KEY,
  marketplace TEXT NOT NULL CHECK (marketplace IN ('Wildberries','Ozon','Яндекс Маркет')),
  pvz_code    TEXT NOT NULL UNIQUE,
  pvz_city    TEXT NOT NULL,
  pvz_address TEXT NOT NULL
)
CREATE TABLE sales (
  sale_id        INTEGER PRIMARY KEY,
  product_id     INTEGER NOT NULL REFERENCES products(product_id),
  customer_id    INTEGER NOT NULL REFERENCES customers(customer_id),
  supplier_id    INTEGER NOT NULL REFERENCES suppliers(supplier_id),
  purchase_price INTEGER NOT NULL,
  sale_price     INTEGER NOT NULL,
  purchase_date  DATE NOT NULL,                      
  delivery_days  INTEGER NOT NULL,  
  sale_date      DATE NOT NULL
)
CREATE TABLE returns (
  return_id   INTEGER PRIMARY KEY,
  sale_id     INTEGER NOT NULL UNIQUE REFERENCES sales(sale_id),
  return_date DATE NOT NULL,
  reason      TEXT NOT NULL CHECK (reason IN ('брак','отмена доставки'))
)
