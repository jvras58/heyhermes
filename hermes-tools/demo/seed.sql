-- Banco de exemplo do HeyHermes: uma mini-loja para testar relatórios por voz.
-- Rodado automaticamente pelo Postgres na 1ª subida (docker-entrypoint-initdb.d).
-- Experimente pedir: "faturamento por categoria", "top 5 clientes", "vendas por mês".

CREATE TABLE clientes (
  id         serial PRIMARY KEY,
  nome       text NOT NULL,
  cidade     text NOT NULL,
  criado_em  date NOT NULL
);

CREATE TABLE produtos (
  id         serial PRIMARY KEY,
  nome       text NOT NULL,
  categoria  text NOT NULL,
  preco      numeric(10,2) NOT NULL
);

CREATE TABLE vendas (
  id          serial PRIMARY KEY,
  cliente_id  int NOT NULL REFERENCES clientes(id),
  produto_id  int NOT NULL REFERENCES produtos(id),
  quantidade  int NOT NULL,
  vendido_em  date NOT NULL
);

INSERT INTO clientes (nome, cidade, criado_em) VALUES
  ('Ana Souza',      'Recife',        '2026-01-10'),
  ('Bruno Lima',     'São Paulo',     '2026-02-02'),
  ('Carla Mendes',   'Recife',        '2026-02-18'),
  ('Diego Rocha',    'Belo Horizonte','2026-03-05'),
  ('Elaine Prado',   'Curitiba',      '2026-04-21'),
  ('Felipe Nunes',   'São Paulo',     '2026-05-30');

INSERT INTO produtos (nome, categoria, preco) VALUES
  ('Notebook Pro',      'Eletrônicos', 5200.00),  -- 1
  ('Notebook Air',      'Eletrônicos', 4100.00),  -- 2
  ('Monitor 27"',       'Eletrônicos', 1450.00),  -- 3
  ('Mouse sem fio',     'Acessórios',   120.50),  -- 4
  ('Teclado mecânico',  'Acessórios',   380.00),  -- 5
  ('Webcam HD',         'Acessórios',   210.00),  -- 6
  ('Cadeira gamer',     'Móveis',      1899.90),  -- 7
  ('Mesa ajustável',    'Móveis',      2450.00),  -- 8
  ('Luminária LED',     'Móveis',       159.90),  -- 9
  ('Headset Pro',       'Acessórios',   690.00);  -- 10

INSERT INTO vendas (cliente_id, produto_id, quantidade, vendido_em) VALUES
  (1, 1, 1, '2026-05-03'), (1, 4, 2, '2026-05-03'), (1, 5, 1, '2026-05-20'),
  (2, 2, 1, '2026-05-11'), (2, 3, 2, '2026-05-11'), (2, 7, 1, '2026-06-01'),
  (3, 4, 3, '2026-05-14'), (3, 6, 1, '2026-05-14'), (3, 9, 2, '2026-06-09'),
  (4, 7, 1, '2026-05-22'), (4, 8, 1, '2026-05-22'), (4, 10, 1, '2026-06-15'),
  (5, 3, 1, '2026-06-02'), (5, 5, 2, '2026-06-02'), (5, 6, 2, '2026-06-18'),
  (6, 1, 1, '2026-06-04'), (6, 2, 1, '2026-06-25'), (6, 10, 2, '2026-07-01'),
  (1, 8, 1, '2026-06-12'), (2, 9, 3, '2026-06-28'), (3, 1, 1, '2026-07-03'),
  (4, 4, 4, '2026-07-05'), (5, 7, 1, '2026-07-08'), (6, 3, 2, '2026-07-10'),
  (1, 10, 1, '2026-07-12'), (2, 5, 1, '2026-07-15'), (3, 8, 1, '2026-07-18');
