#!/usr/bin/env bash
set -euo pipefail

umask 077

OUTPUT_DIR="${1:-legacy-production-evidence-$(date -u +%Y%m%dT%H%M%SZ)}"
REPO_ROOT="${LEGACY_REPO_ROOT:-/opt/variable-global}"
mkdir -p "$OUTPUT_DIR"
chmod 700 "$OUTPUT_DIR"

{
  printf 'collected_at_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'hostname=%s\n' "$(hostname 2>/dev/null || true)"
  printf 'kernel=%s\n' "$(uname -srmo 2>/dev/null || true)"
  printf 'repo_root=%s\n' "$REPO_ROOT"
} > "$OUTPUT_DIR/metadata.txt"

{
  for service in variable-global-auth variable-global-data nginx mysql mariadb; do
    printf '## %s\n' "$service"
    printf 'active='
    systemctl is-active "$service" 2>&1 || true
    printf 'enabled='
    systemctl is-enabled "$service" 2>&1 || true
    fragment="$(systemctl show "$service" --property=FragmentPath --value 2>/dev/null || true)"
    printf 'fragment=%s\n' "$fragment"
    if [[ -n "$fragment" && -f "$fragment" ]]; then
      stat --printf='fragment_mode=%a fragment_owner=%U fragment_group=%G fragment_size=%s fragment_modified=%y\n' "$fragment" || true
      printf 'fragment_sha256='
      sha256sum "$fragment" | awk '{print $1}' || true
    fi
    printf '\n'
  done
} > "$OUTPUT_DIR/service-state.txt"

{
  ss -lntH 2>&1 | grep -E ':(80|443|3306|4373|8000|8080|8082|8100)([[:space:]]|$)' || true
} > "$OUTPUT_DIR/listening-ports.txt"

{
  if [[ -d "$REPO_ROOT/.git" ]]; then
    echo 'repo_present=true'
    git -C "$REPO_ROOT" status --short --branch || true
    git -C "$REPO_ROOT" rev-parse HEAD || true
    git -C "$REPO_ROOT" branch --show-current || true
    echo 'remote_names:'
    git -C "$REPO_ROOT" remote || true
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
    printf 'sha256='
    sha256sum "$file" | awk '{print $1}' || true
    echo 'keys:'
    awk -F= '/^[A-Za-z_][A-Za-z0-9_]*=/{print $1}' "$file" | sort -u
  done
} > "$OUTPUT_DIR/environment-file-metadata.txt"

{
  for binary in \
    /usr/local/lib/variable-global/auth-service \
    /usr/local/lib/variable-global/data-service; do
    printf '## %s\n' "$binary"
    if [[ ! -f "$binary" ]]; then
      echo 'missing'
      continue
    fi
    stat --printf='mode=%a owner=%U group=%G size=%s modified=%y\n' "$binary" || true
    printf 'sha256='
    sha256sum "$binary" | awk '{print $1}' || true
  done
} > "$OUTPUT_DIR/binary-metadata.txt"

if command -v nginx >/dev/null 2>&1; then
  nginx -t > "$OUTPUT_DIR/nginx-test.txt" 2>&1 || true
else
  echo 'nginx_not_installed=true' > "$OUTPUT_DIR/nginx-test.txt"
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

find "$OUTPUT_DIR" -type f ! -name 'MANIFEST.sha256' -print0 \
  | sort -z \
  | xargs -0 -r sha256sum \
  > "$OUTPUT_DIR/MANIFEST.sha256"
chmod 600 "$OUTPUT_DIR"/*

printf 'Evidence directory: %s\n' "$OUTPUT_DIR"
printf 'Review every file before sharing. No Secret value should be present.\n'
