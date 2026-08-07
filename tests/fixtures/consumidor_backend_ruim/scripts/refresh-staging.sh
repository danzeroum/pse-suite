#!/usr/bin/env bash
# S-14: restaura o dump de producao em staging, cru.
set -euo pipefail

pg_dump "$PROD_DATABASE_URL" > /tmp/dump_prod.sql
psql "$STAGING_DATABASE_URL" < /tmp/dump_prod.sql

echo "staging atualizado"
