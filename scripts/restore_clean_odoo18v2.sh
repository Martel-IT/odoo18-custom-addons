#!/usr/bin/env bash
set -euo pipefail

DB_NAME="odoo"
DB_USER="odoo"
DUMP="/home/odooadmin/odoo_martel_18_MIGRATED.sql"
FILESTORE_SRC="/home/odooadmin/odoo_martel_16"
TARGET_FILESTORE="/data/odoo/filestore/odoo"
MARTEL_MODULES="custom_martel_theme,custom_hr_timesheet_overtime"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

[[ $EUID -eq 0 ]] || { echo -e "${RED}[ERRORE] Esegui come root.${NC}"; exit 1; }
[[ -f "$DUMP" ]] || { echo -e "${RED}[ERRORE] Dump non trovato: $DUMP${NC}"; exit 1; }
[[ -d "$FILESTORE_SRC" ]] || { echo -e "${RED}[ERRORE] Filestore src non trovato: $FILESTORE_SRC${NC}"; exit 1; }

echo -e "${YELLOW}ATTENZIONE: cancellerò DB '${DB_NAME}' e filestore '${TARGET_FILESTORE}'${NC}"
read -p "Digita YES per procedere: " CONFIRM
[[ "$CONFIRM" == "YES" ]] || { echo "Annullato."; exit 0; }

echo -e "${YELLOW}[STEP 1] Stop Odoo...${NC}"
systemctl stop odoo

echo -e "${YELLOW}[STEP 2] Sostituzione filestore...${NC}"
rm -rf "$TARGET_FILESTORE"
mkdir -p "$(dirname "$TARGET_FILESTORE")"
cp -a "$FILESTORE_SRC" "$TARGET_FILESTORE"
chown -R odoo:odoo "$TARGET_FILESTORE"
chmod -R 750 "$TARGET_FILESTORE"

echo -e "${YELLOW}[STEP 3] Drop e ricreazione db ${DB_NAME}...${NC}"
sudo -u postgres psql -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${DB_NAME}' AND pid <> pg_backend_pid();" >/dev/null
sudo -u postgres dropdb --if-exists "$DB_NAME"
sudo -u postgres createdb -O "$DB_USER" "$DB_NAME"

echo -e "${YELLOW}[STEP 4] Restore dump SQL...${NC}"
sudo -u postgres psql -d "$DB_NAME" < "$DUMP"

echo -e "${YELLOW}[STEP 5] Drop sequenze base_*signaling*...${NC}"
sudo -u postgres psql -d "$DB_NAME" <<'SQL'
DO $$
DECLARE seq record;
BEGIN
    FOR seq IN
        SELECT sequence_name FROM information_schema.sequences
        WHERE sequence_name LIKE 'base_registry_signaling%'
           OR sequence_name LIKE 'base_cache_signaling%'
    LOOP
        EXECUTE 'DROP SEQUENCE IF EXISTS ' || quote_ident(seq.sequence_name) || ' CASCADE';
        RAISE NOTICE 'Dropped: %', seq.sequence_name;
    END LOOP;
END $$;
SQL

echo -e "${YELLOW}[STEP 6] Riassegna ownership a '${DB_USER}'...${NC}"
sudo -u postgres psql -d "$DB_NAME" <<SQL
DO \$\$
DECLARE r record;
BEGIN
    FOR r IN SELECT tablename FROM pg_tables WHERE schemaname='public' LOOP
        EXECUTE 'ALTER TABLE public.'||quote_ident(r.tablename)||' OWNER TO ${DB_USER}';
    END LOOP;
    FOR r IN SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema='public' LOOP
        EXECUTE 'ALTER SEQUENCE public.'||quote_ident(r.sequence_name)||' OWNER TO ${DB_USER}';
    END LOOP;
    FOR r IN SELECT table_name FROM information_schema.views WHERE table_schema='public' LOOP
        EXECUTE 'ALTER VIEW public.'||quote_ident(r.table_name)||' OWNER TO ${DB_USER}';
    END LOOP;
    FOR r IN SELECT matviewname FROM pg_matviews WHERE schemaname='public' LOOP
        EXECUTE 'ALTER MATERIALIZED VIEW public.'||quote_ident(r.matviewname)||' OWNER TO ${DB_USER}';
    END LOOP;
END\$\$;
SQL

OWNERS=$(sudo -u postgres psql -d "$DB_NAME" -tAc "SELECT DISTINCT tableowner FROM pg_tables WHERE schemaname='public';")
if [[ "$OWNERS" != "$DB_USER" ]]; then
    echo -e "${RED}[ERRORE] Owner inattesi nello schema public: ${OWNERS}${NC}"
    exit 1
fi
echo -e "${GREEN}  ownership ok (tutto su ${DB_USER})${NC}"

echo -e "${YELLOW}[STEP 7] Pulizia web assets...${NC}"
sudo -u postgres psql -d "$DB_NAME" -c "DELETE FROM ir_attachment WHERE url LIKE '/web/assets/%';"

echo -e "${YELLOW}[STEP 8] Estraggo path odoo bin + conf dalla unit systemd...${NC}"
EXECSTART=$(systemctl show odoo -p ExecStart --value)
ENV_LINE=$(systemctl show odoo -p Environment --value)

ODOO_BIN=""
ODOO_CONF=""
if [[ "$EXECSTART" =~ (/nix/store/[^[:space:]\;\{\}]+/bin/odoo) ]]; then
    ODOO_BIN="${BASH_REMATCH[1]}"
fi
if [[ "$ENV_LINE" =~ ODOO_RC=([^[:space:]]+) ]]; then
    ODOO_CONF="${BASH_REMATCH[1]}"
fi

if [[ -z "$ODOO_BIN" ]]; then
    echo -e "${RED}[ERRORE] Non sono riuscito a estrarre il binario odoo dall'ExecStart: ${EXECSTART}${NC}"
    exit 1
fi
if [[ -z "$ODOO_CONF" ]]; then
    echo -e "${RED}[ERRORE] ODOO_RC non trovato nell'Environment del servizio.${NC}"
    exit 1
fi
if [[ ! -r "$ODOO_CONF" ]]; then
    echo -e "${RED}[ERRORE] Config file non leggibile: ${ODOO_CONF}${NC}"
    exit 1
fi
echo -e "  odoo bin:  ${ODOO_BIN}"
echo -e "  odoo conf: ${ODOO_CONF}"

echo -e "${YELLOW}[STEP 8a] Install moduli custom Martel (${MARTEL_MODULES})...${NC}"
runuser -u odoo -- "$ODOO_BIN" -c "$ODOO_CONF" \
    -d "$DB_NAME" \
    -i "$MARTEL_MODULES" \
    --stop-after-init \
    --no-http

echo -e "${YELLOW}[STEP 8b] Upgrade moduli custom Martel per ricaricare viste/template XML...${NC}"
runuser -u odoo -- "$ODOO_BIN" -c "$ODOO_CONF" \
    -d "$DB_NAME" \
    -u "$MARTEL_MODULES" \
    --stop-after-init \
    --no-http

INSTALLED=$(sudo -u postgres psql -d "$DB_NAME" -tAc "
    SELECT name FROM ir_module_module
     WHERE name IN ('custom_martel_theme','custom_hr_timesheet_overtime')
       AND state = 'installed'
     ORDER BY name;")
EXPECTED=$(printf "custom_hr_timesheet_overtime\ncustom_martel_theme")
if [[ "$INSTALLED" != "$EXPECTED" ]]; then
    echo -e "${RED}[ERRORE] Non tutti i moduli custom Martel risultano installati.${NC}"
    echo -e "${RED}  installati: ${INSTALLED//$'\n'/, }${NC}"
    exit 1
fi
echo -e "${GREEN}  moduli custom installati + upgraded: custom_martel_theme, custom_hr_timesheet_overtime${NC}"

echo -e "${YELLOW}[STEP 9] Disabilita timesheet auto-generation sui leave types...${NC}"
sudo -u postgres psql -d "$DB_NAME" <<'SQL'
UPDATE hr_leave_type
   SET timesheet_generate = FALSE,
       timesheet_project_id = NULL,
       timesheet_task_id = NULL;
SQL

echo -e "${YELLOW}[STEP 10] Disattivazione viste rotte 'l10n_ch_postal' (fix add bank)...${NC}"
FIXED_VIEWS=$(sudo -u postgres psql -d "$DB_NAME" -tAc "
    UPDATE ir_ui_view
       SET active = FALSE
     WHERE active = TRUE
       AND arch_db::text ILIKE '%l10n_ch_postal%'
    RETURNING id || ' (' || name || ')';
")
if [[ -n "$FIXED_VIEWS" ]]; then
    echo -e "${GREEN}  viste disattivate:${NC}"
    echo "$FIXED_VIEWS" | sed 's/^/    - /'
else
    echo -e "${GREEN}  nessuna vista rotta trovata (già pulito)${NC}"
fi

echo -e "${YELLOW}[STEP 11] Fix hr_leave con span degenerato (migration cleanup)...${NC}"
# Idempotente: il WHERE filtra già-fixati (number_of_days dopo l'update non
# è più 0, quindi i run successivi matchano 0 record). Imposta number_of_days = 1
# per i ~84 Compensatory Days dove la migrazione OCA ha collassato
# date_from/date_to sul timestamp di creazione e azzerato sia days che hours.
LEAVE_FIX=$(sudo -u postgres psql -d "$DB_NAME" -tAc "
WITH updated AS (
    UPDATE hr_leave
    SET number_of_days = 1
    WHERE state = 'validate'
      AND number_of_days = 0
      AND number_of_hours = 0
      AND EXTRACT(EPOCH FROM (date_to - date_from)) < 60
    RETURNING id
)
SELECT count(*) FROM updated;")
echo -e "${GREEN}  fixed ${LEAVE_FIX} hr_leave records (number_of_days 0 → 1)${NC}"

echo -e "${YELLOW}[STEP 12] Restore OD16 timesheet snapshots (pre-Dec 2025)...${NC}"
# La OCA migration 16→18 non porta dati hr.leave / resource.calendar.leaves
# abbastanza puliti per ricalcolare accuratamente i duty hours dei sheet
# pre-Dec 2025. Importiamo i valori autoritativi da OD16 production
# (CSV committato in github). Idempotente: re-run su DB già corretto
# scrive valori identici.
SNAPSHOT_URL="https://raw.githubusercontent.com/Martel-IT/odoo18-custom-addons/main/scripts/od16_snapshots.csv"
SNAPSHOT_TMP="/tmp/od16_snapshots.csv"

if ! curl -fsSL "$SNAPSHOT_URL" -o "$SNAPSHOT_TMP"; then
    echo -e "${RED}[ERRORE] Download snapshot OD16 fallito: $SNAPSHOT_URL${NC}"
    exit 1
fi
[[ -s "$SNAPSHOT_TMP" ]] || { echo -e "${RED}[ERRORE] CSV snapshot scaricato vuoto.${NC}"; exit 1; }
chmod 0644 "$SNAPSHOT_TMP"
SNAPSHOT_ROWS=$(($(wc -l < "$SNAPSHOT_TMP") - 1))
echo -e "  scaricato: $SNAPSHOT_TMP ($SNAPSHOT_ROWS data rows)"

sudo -u postgres psql -d "$DB_NAME" -v ON_ERROR_STOP=1 <<SQL
BEGIN;
CREATE TEMP TABLE od16_snapshots (
  id INTEGER PRIMARY KEY,
  total_duty_hours_done DOUBLE PRECISION,
  total_diff_hours DOUBLE PRECISION
);
\COPY od16_snapshots FROM '$SNAPSHOT_TMP' WITH (FORMAT CSV, HEADER true)
UPDATE hr_timesheet_sheet s
   SET total_duty_hours_done = o.total_duty_hours_done,
       total_diff_hours      = o.total_diff_hours
  FROM od16_snapshots o
 WHERE s.id = o.id
   AND s.state = 'done'
   AND s.date_end < '2025-12-01';
COMMIT;
SQL

APPLIED=$(sudo -u postgres psql -d "$DB_NAME" -tAc "
    SELECT count(*) FROM hr_timesheet_sheet
     WHERE state = 'done' AND date_end < '2025-12-01';")
echo -e "${GREEN}  snapshot OD16 applicati su ${APPLIED} sheet pre-cutoff${NC}"

echo -e "${YELLOW}[STEP 13] Backfill snapshot flexitime post-cutoff (total_diff_hours / total_duty_hours_done)...${NC}"
BACKFILL_URL="https://raw.githubusercontent.com/Martel-IT/odoo18-custom-addons/main/scripts/backfill_timesheet_snapshots.py"
BACKFILL_TMP="/tmp/backfill_timesheet_snapshots.py"

if ! curl -fsSL "$BACKFILL_URL" -o "$BACKFILL_TMP"; then
    echo -e "${RED}[ERRORE] Download backfill fallito: $BACKFILL_URL${NC}"
    exit 1
fi
[[ -s "$BACKFILL_TMP" ]] || { echo -e "${RED}[ERRORE] Backfill scaricato vuoto.${NC}"; exit 1; }
chown odoo:odoo "$BACKFILL_TMP"
chmod 0644 "$BACKFILL_TMP"
echo -e "  scaricato: $BACKFILL_TMP ($(wc -l < "$BACKFILL_TMP") righe)"

BACKFILL_LOG="/tmp/backfill_$(date +%Y%m%d_%H%M%S).log"
if ! runuser -u odoo -- bash -c "HOME=/data/odoo '$ODOO_BIN' shell -c '$ODOO_CONF' -d '$DB_NAME' --no-http < '$BACKFILL_TMP'" \
        2>&1 | tee "$BACKFILL_LOG"; then
    echo -e "${RED}[ERRORE] Backfill terminato con errori. Vedi $BACKFILL_LOG${NC}"
    exit 1
fi

STILL_ZERO=$(sudo -u postgres psql -d "$DB_NAME" -tAc "
    SELECT count(*)
      FROM hr_timesheet_sheet
     WHERE state = 'done'
       AND total_duty_hours_done = 0
       AND total_time <> 0;")
if [[ "${STILL_ZERO:-0}" -gt 0 ]]; then
    echo -e "${YELLOW}  ATTENZIONE: $STILL_ZERO fogli 'done' con total_duty_hours_done=0. Vedi $BACKFILL_LOG${NC}"
else
    echo -e "${GREEN}  backfill ok, snapshot ricalcolati${NC}"
fi

echo -e "${YELLOW}[STEP 14] Start Odoo...${NC}"
systemctl start odoo

echo -e "${GREEN}[DONE] Verifica i log: journalctl -u odoo -f${NC}"
echo -e "${GREEN}       Log backfill: $BACKFILL_LOG${NC}"
