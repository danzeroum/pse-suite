-- Grant por coluna e por finalidade: a role ve o que a finalidade exige.
CREATE ROLE app_readonly;

GRANT SELECT (id, cidade, criado_em) ON clientes TO app_readonly;

GRANT SELECT (id, valor, status) ON pedidos TO app_readonly;
