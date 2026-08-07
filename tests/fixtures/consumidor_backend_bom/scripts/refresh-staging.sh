#!/usr/bin/env bash
# O dump de producao so entra em staging depois de perder o titular.
set -euo pipefail

pg_dump "$PROD_DATABASE_URL" > /tmp/dump_prod.sql
python scripts/anonimizar_dump.py /tmp/dump_prod.sql /tmp/dump_anon.sql
psql "$STAGING_DATABASE_URL" < /tmp/dump_anon.sql

echo "staging atualizado com base descaracterizada"
