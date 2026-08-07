-- S-15: a aplicacao recebe o schema inteiro em vez da coluna que usa.
CREATE ROLE app_readonly;

GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_readonly;

GRANT ALL PRIVILEGES ON clientes TO app_etl;
