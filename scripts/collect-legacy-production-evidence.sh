#!/usr/bin/env bash
set -euo pipefail

OUTPUT_DIR="${1:-legacy-production-evidence-$(date -u +%Y%m%dT%H%M%SZ)}"
REPO_ROOT="${LEGACY_REPO_ROOT:-/opt/variable-global}"
mkdir -p "$OUTPUT_DIR"
umask 077

{
  printf 'collected_at_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'hostname=%s\n' "$(hostname 2>/dev/null || true)"
  printf 'kernel=%s\n' "$(uname -srmo 2>/dev/null || true)"
  printf 'repo_root=%s\n' "$REPO_ROOT"
} > "$OUTPUT_DIR/metadata.txt"

{
  systemctl is-active variable-global-auth variable-global-data nginx mysql mariadb 2>&1 || true
  systemctl is-enabled variable-global-auth variable-global-data nginx mysql mariadb 2>&1 || true
} > "$OUTPUT_DIR/service-state.txt"

ss -lnt 2>&1 > "$OUTPUT_DIR/listening-ports.txt" || true

{
  if [[ -d "$REPO_ROOT/.git" ]]; then
    echo 'repo_present=true'
    git -C "$REPO_ROOT" status --short --branch || true
    git -C "$REPO_ROOT" rev-parse HEAD || true
    git -C "$REPO_ROOT" branch --show-current || true
  else
    echo 'repo_present=false'
  fi
} > "$OUTPUT_DIR/repository-state.txt"

{
  for file in /etc/variable-global/auth.env /etc/variable-global/data.env; do
    printf '## %s\n' "$file"
    if [[ ! -e "$file" ]]; then
      echo 'missing'
      continue
    fi
    stat --printf='mode=%a owner=%U group=%G size=%s modified=%y\n' "$file" || true
    sha256sum "$file" || true
    echo 'keys:'
    awk -F= '/^[A-Za-z_][A-Za-z0-9_]*=/{print $1}' "$file" | sort -u
  done
} > "$OUTPUT_DIR/environment-file-metadata.txt"

if command -v nginx >/dev/null 2>&1; then
  nginx -t > "$OUTPUT_DIR/nginx-test.txt" 2>&1 || true
fi

if command -v mysql >/dev/null 2>&1 && \
  mysql --batch --skip-column-names -e 'SELECT 1' >/dev/null 2>&1; then
  mysql --batch --skip-column-names -e \
    "SELECT TABLE_NAME,TABLE_TYPE,ENGINE,TABLE_ROWS,CREATE_TIME,UPDATE_TIME FROM information_schema.TABLES WHERE TABLE_SCHEMA='risk_control' ORDER BY TABLE_NAME" \
    > "$OUTPUT_DIR/mysql-tables.txt" 2>&1 || true
  mysql --batch --skip-column-names -e \
    "SELECT TABLE_NAME,ORDINAL_POSITION,COLUMN_NAME,COLUMN_TYPE,IS_NULLABLE,COLUMN_DEFAULT,EXTRA FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='risk_control' ORDER BY TABLE_NAME,ORDINAL_POSITION" \
    > "$OUTPUT_DIR/mysql-columns.txt" 2>&1 || true
  mysql --batch --skip-column-names -e \
    "SELECT TABLE_NAME,INDEX_NAME,SEQ_IN_INDEX,COLUMN_NAME,NON_UNIQUE FROM information_schema.STATISTICS WHERE TABLE_SCHEMA='risk_control' ORDER BY TABLE_NAME,INDEX_NAME,SEQ_IN_INDEX" \
    > "$OUTPUT_DIR/mysql-indexes.txt" 2>&1 || true
else
  echo 'mysql_socket_auth_unavailable=true' > "$OUTPUT_DIR/mysql-status.txt"
fi

find "$OUTPUT_DIR" -type f -print0 | sort -z | xargs -0 sha256sum \
  > "$OUTPUT_DIR/MANIFEST.sha256"

printf 'Evidence directory: %s\n' "$OUTPUT_DIR"
printf 'Review every file before sharing. No Secret value should be present.\n'
