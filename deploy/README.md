# 65.49.234.98 原生部署手册（不使用 Docker）

运行结构：宿主机 Nginx 提供前端，systemd 管理两个 Go 服务，本机 MySQL 保存数据。
公网只开放 22、80（启用 HTTPS 后再开放 443）；Go 服务仅监听 `127.0.0.1:8080` 和
`127.0.0.1:8082`。

> HTTP 只适合首次验收。正式使用登录功能前应绑定域名并配置 HTTPS。

## 一、首次准备服务器

以下命令以 Ubuntu/Debian、root 用户为例：

```bash
ssh root@65.49.234.98
apt-get update
apt-get install -y git curl ca-certificates nginx mysql-server rsync nodejs npm golang-go
npm install -g pnpm@8.1.0

node --version   # 要求 >= 16.15
pnpm --version
go version       # 要求 >= 1.20
nginx -v
mysql --version
```

如果系统软件源里的 Go 低于 1.20，请先从 `https://go.dev/dl/` 安装新版，再继续。安全组和
UFW 只放行必要端口：

```bash
ufw allow OpenSSH
ufw allow 80/tcp
ufw enable
```

不要放行 3306、8080、8082。

## 二、把主分支最新版放到固定目录

新安装：

```bash
mkdir -p /opt
cd /opt
git clone -b main https://github.com/Lucasmingyu/Variable-Global.git variable-global
cd /opt/variable-global
```

服务器已有旧版项目时，先备份本地修改，再替换成远程主分支最新版：

```bash
cd /opt/variable-global
git status
git stash push -u -m "server backup before native deployment"
git fetch origin
git switch main
git pull --ff-only origin main
```

旧项目不在 `/opt/variable-global` 也可以：进入它的实际根目录运行 `deploy/install-native.sh`
即可。后续示例中的 `/opt/variable-global` 替换为实际路径。

## 三、配置本机 MySQL

先生成一个只包含字母数字的数据库密码：

```bash
openssl rand -hex 24
mysql -uroot -p
```

在 MySQL 中执行，并替换密码：

```sql
CREATE DATABASE IF NOT EXISTS risk_control
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'risk_app'@'127.0.0.1'
  IDENTIFIED BY '替换为刚生成的数据库密码';
GRANT ALL PRIVILEGES ON risk_control.* TO 'risk_app'@'127.0.0.1';
FLUSH PRIVILEGES;
EXIT;
```

如果服务器原版已经使用 `risk_control` 数据库，不要删除它。先备份：

```bash
mysqldump -uroot -p --single-transaction risk_control | \
  gzip > "/root/risk_control-before-upgrade-$(date +%F-%H%M%S).sql.gz"
```

## 四、配置两个服务的密钥

```bash
install -d -m 0700 /etc/variable-global
cp /opt/variable-global/deploy/auth.env.example /etc/variable-global/auth.env
cp /opt/variable-global/deploy/data.env.example /etc/variable-global/data.env
openssl rand -hex 32
nano /etc/variable-global/auth.env
nano /etc/variable-global/data.env
chmod 600 /etc/variable-global/*.env
```

配置要求：

- 两个文件的 `DB_DSN` 使用第三步创建的同一密码。
- 两个文件的 `JWT_SECRET` 必须完全相同。
- `ACCOUNT_ENCRYPTION_KEY` 使用另一个独立随机值。
- 首次创建管理员时，`auth.env` 保持 `SEED_ADMIN=true` 并设置强密码。
- 暂时不接 Bybit 时保持 `SCHEDULER_ENABLED=false`。

## 五、构建并安装

```bash
cd /opt/variable-global
chmod +x deploy/install-native.sh
sudo bash deploy/install-native.sh
```

脚本会自动完成：前端构建、Go 编译、静态文件安装、systemd 安装、Nginx 安装、服务启动和
健康检查。

Nginx 项目源文件是：

```text
/opt/variable-global/deploy/nginx-variable-global.conf
```

服务器实际生效文件是：

```text
/etc/nginx/sites-available/variable-global.conf
/etc/nginx/sites-enabled/variable-global.conf
```

## 六、验收与关闭初始管理员

```bash
systemctl status variable-global-auth variable-global-data nginx --no-pager
curl -fsS http://127.0.0.1:8080/health
curl -fsS http://127.0.0.1:8082/health
curl -fsS http://127.0.0.1/healthz
curl -fsS http://65.49.234.98/healthz
```

浏览器临时访问 `http://65.49.234.98`。首次管理员登录成功后：

```bash
sed -i 's/^SEED_ADMIN=.*/SEED_ADMIN=false/' /etc/variable-global/auth.env
systemctl restart variable-global-auth
```

## 七、以后用主分支最新版替换旧版

```bash
ssh root@65.49.234.98
cd /opt/variable-global
git status
git fetch origin
git switch main
git pull --ff-only origin main
sudo bash deploy/install-native.sh
```

这会替换前端静态文件和两个 Go 二进制，不会删除 MySQL 数据或覆盖 `/etc/variable-global`
中的生产密钥。

## 八、日志和故障排查

```bash
journalctl -u variable-global-auth -f
journalctl -u variable-global-data -f
journalctl -u nginx -f
nginx -t
ss -lntp | grep -E ':80|:8080|:8082|:3306'
```

- 502：检查两个 `variable-global-*` 服务是否启动。
- 数据库拒绝连接：核对 MySQL 用户、密码和两个 `DB_DSN`。
- 外网超时：检查云安全组和 UFW 的 80 端口。
- 前端未更新：确认安装脚本成功执行，并强制刷新浏览器缓存。

## 九、回滚

```bash
cd /opt/variable-global
git log --oneline -10
git switch --detach <上一个正常提交ID>
sudo bash deploy/install-native.sh
```

确认恢复后再决定是否切回 `main`。数据库回滚必须使用升级前的 SQL 备份，不能只靠 Git。
