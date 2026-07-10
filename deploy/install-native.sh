#!/usr/bin/env bash
set -Eeuo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "请使用 root 运行：sudo bash deploy/install-native.sh" >&2
  exit 1
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for command in go node pnpm nginx rsync systemctl curl; do
  command -v "${command}" >/dev/null || {
    echo "缺少命令：${command}，请先按 deploy/README.md 安装依赖" >&2
    exit 1
  }
done

test -s /etc/variable-global/auth.env || {
  echo "缺少 /etc/variable-global/auth.env" >&2
  exit 1
}
test -s /etc/variable-global/data.env || {
  echo "缺少 /etc/variable-global/data.env" >&2
  exit 1
}

id variable-global >/dev/null 2>&1 || \
  useradd --system --home-dir /var/lib/variable-global --shell /usr/sbin/nologin variable-global
install -d -o variable-global -g variable-global -m 0750 /var/lib/variable-global

echo "[1/5] 构建前端"
cd "${PROJECT_ROOT}/admin-risk"
HUSKY=0 pnpm install --frozen-lockfile
pnpm build

echo "[2/5] 构建 Go 服务"
install -d -m 0755 /usr/local/lib/variable-global
cd "${PROJECT_ROOT}/projects/risk-control/auth-service"
go build -trimpath -ldflags="-s -w" -o /tmp/variable-global-auth ./cmd
install -m 0755 /tmp/variable-global-auth /usr/local/lib/variable-global/auth-service
cd "${PROJECT_ROOT}/projects/risk-control/data-service"
go build -trimpath -ldflags="-s -w" -o /tmp/variable-global-data ./cmd
install -m 0755 /tmp/variable-global-data /usr/local/lib/variable-global/data-service
rm -f /tmp/variable-global-auth /tmp/variable-global-data

echo "[3/5] 安装静态文件与服务配置"
install -d -o www-data -g www-data -m 0755 /var/www/variable-global
rsync -a --delete "${PROJECT_ROOT}/admin-risk/dist/" /var/www/variable-global/
chown -R www-data:www-data /var/www/variable-global
install -m 0644 "${PROJECT_ROOT}/deploy/systemd/variable-global-auth.service" /etc/systemd/system/
install -m 0644 "${PROJECT_ROOT}/deploy/systemd/variable-global-data.service" /etc/systemd/system/
install -m 0644 "${PROJECT_ROOT}/deploy/nginx-variable-global.conf" \
  /etc/nginx/sites-available/variable-global.conf
ln -sfn /etc/nginx/sites-available/variable-global.conf \
  /etc/nginx/sites-enabled/variable-global.conf
rm -f /etc/nginx/sites-enabled/default

echo "[4/5] 校验并启动"
systemctl daemon-reload
nginx -t
systemctl enable --now variable-global-auth variable-global-data nginx
systemctl restart variable-global-auth variable-global-data
systemctl reload nginx

echo "[5/5] 健康检查"
sleep 2
curl --fail --silent --show-error http://127.0.0.1:8080/health >/dev/null
curl --fail --silent --show-error http://127.0.0.1:8082/health >/dev/null
curl --fail --silent --show-error http://127.0.0.1/healthz >/dev/null
echo "部署完成：http://65.49.234.98"
