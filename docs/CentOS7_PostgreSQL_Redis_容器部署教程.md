# PostgreSQL + Redis 容器部署教程（image100）

> **适用系统**：Rocky Linux 8 / AlmaLinux 8 / CentOS Stream 8（本机实测：**Rocky Linux 8.10**）  
> **目标虚拟机**：`node101`，IP 示例：`192.168.137.128`（以你 `hostname -I` 为准）  
> **用途**：为本项目提供业务库（PostgreSQL）与队列/缓存（Redis）  
> **文档版本**：v1.1（2026-10-14，按实机环境修订）  
> **说明**：本教程**只部署中间件两个容器**，不包含 FastAPI / 前端。

---

## 0. 你这台机器的现状（已核对，可跳过安装 Docker）

以下为 `192.168.137.128` 实机检查结果，**Docker 已够用，不必重装**：


| 项                    | 实机结果                           | 结论                                |
| -------------------- | ------------------------------ | --------------------------------- |
| 系统                   | Rocky Linux 8.10               | 合适                                |
| Docker 服务            | `active`                       | 合适                                |
| Docker Engine        | **26.1.3**                     | 合适（远高于要求）                         |
| Compose              | **Docker Compose v2.27.0**（插件） | 合适                                |
| 旧命令 `docker-compose` | 未安装                            | **不用装**；全程用 `docker compose`（有空格） |
| 已有容器                 | MySQL 8 占用 `3306`              | 与本教程端口 **不冲突**，可并存                |


> **命令注意**：全文一律使用 `docker compose`，不要写成 `docker-compose`。

---



## 1. 结论与端口约定


| 问题                          | 答案                                         |
| --------------------------- | ------------------------------------------ |
| 能在虚拟机里用容器存项目数据吗？            | **能**，推荐这样做                                |
| 数据会丢吗？                      | 不会（使用 Docker Volume 持久化）                   |
| 要不要 yum 装原生 postgres/redis？ | **不需要**                                    |
| 端口                          | 宿主机 `7311`**→PostgreSQL**，`7312`**→Redis** |



| 服务         | 容器名                 | 宿主机端口 | 容器内端口 | 账号 / 库（默认）                                    |
| ---------- | ------------------- | ----- | ----- | --------------------------------------------- |
| PostgreSQL | `image100-postgres` | 7311  | 5432  | 用户 `retouch` / 密码 `retouch_dev` / 库 `retouch` |
| Redis      | `image100-redis`    | 7312  | 6379  | 无密码（内网实验）                                     |


---



## 2. 部署前准备（Xshell 登录后做）

建议用 **root** 操作。

### 2.1 确认环境（可选，再确认一遍）

```bash
cat /etc/redhat-release
systemctl is-active docker
docker version
docker compose version
hostname -I
```

期望：

- Docker 为 `active`
- `docker compose version` 能显示版本（如 v2.27.0）
- IP 含 `192.168.137.128`（若变了，后面连接串改用新 IP）



### 2.2 确认端口空闲

```bash
ss -lntp | grep -E '7311|7312' || echo "7311/7312 空闲，可用"
```

若已被占用，记下占用进程，或改第 4 章 `.env` 里的端口。

### 2.3 目标目录

```text
/opt/image100-middleware/
├── docker-compose.yml
└── .env
```

---



## 3. （一般跳过）仅当 Docker 坏了才重装

你当前 **Docker 26.1.3 + Compose v2 已正常**，请直接做 **第 4 章**。

仅当 `systemctl is-active docker` 不是 `active`，或 `docker` / `docker compose` 命令不存在时，再按 Rocky/RHEL 8 方式安装（示例）：

```bash
dnf -y install dnf-plugins-core
dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
dnf -y install docker-ce docker-ce-cli containerd.io docker-compose-plugin
systemctl enable --now docker
docker version
docker compose version
```

---



## 4. 创建配置文件并启动（核心步骤）



### 4.1 建目录

```bash
mkdir -p /opt/image100-middleware
cd /opt/image100-middleware
```



### 4.2 写 `.env`

```bash
cat > /opt/image100-middleware/.env <<'EOF'
# PostgreSQL
POSTGRES_USER=retouch
POSTGRES_PASSWORD=retouch_dev
POSTGRES_DB=retouch
POSTGRES_HOST_PORT=7311

# Redis
REDIS_HOST_PORT=7312
EOF
```

> 课程/实验可用上述默认值（与项目规划书一致）。正式环境请改强密码。  
> **注意**：PostgreSQL 数据卷首次初始化后，只改 `.env` 不会自动改库内密码。



### 4.3 写 `docker-compose.yml`

```bash
cat > /opt/image100-middleware/docker-compose.yml <<'EOF'
services:
  postgres:
    image: postgres:16-alpine
    container_name: image100-postgres
    restart: unless-stopped
    ports:
      - "${POSTGRES_HOST_PORT:-7311}:5432"
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-retouch}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-retouch_dev}
      POSTGRES_DB: ${POSTGRES_DB:-retouch}
      TZ: Asia/Shanghai
    volumes:
      - image100_pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
      interval: 5s
      timeout: 5s
      retries: 10

  redis:
    image: redis:7-alpine
    container_name: image100-redis
    restart: unless-stopped
    ports:
      - "${REDIS_HOST_PORT:-7312}:6379"
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      - image100_redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10

volumes:
  image100_pg_data:
  image100_redis_data:
EOF
```

> Compose V2 可不写顶层 `version:` 字段。



### 4.4 拉取镜像并启动

```bash
cd /opt/image100-middleware
docker compose pull
docker compose up -d
docker compose ps
```

期望两个服务都是 `running` / `healthy`（或至少 `Up`）。

查看日志（出错时用）：

```bash
docker compose logs -f --tail=100 postgres
# Ctrl+C 后
docker compose logs -f --tail=100 redis
```

---



## 5. 验证是否成功



### 5.1 看容器与端口

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

应看到类似：

```text
image100-postgres   ...   0.0.0.0:7311->5432/tcp
image100-redis      ...   0.0.0.0:7312->6379/tcp
mysql8-server       ...   0.0.0.0:3306->3306/tcp    # 原有 MySQL，保留即可
```



### 5.2 测 PostgreSQL

```bash
docker exec -it image100-postgres \
  psql -U retouch -d retouch -c "SELECT version();"
```

可选：写一条测试数据

```bash
docker exec -it image100-postgres \
  psql -U retouch -d retouch -c \
  "CREATE TABLE IF NOT EXISTS deploy_ping(id serial primary key, note text, created_at timestamptz default now());
   INSERT INTO deploy_ping(note) VALUES ('rocky8-ok');
   SELECT * FROM deploy_ping;"
```



### 5.3 测 Redis

```bash
docker exec -it image100-redis redis-cli ping
docker exec -it image100-redis redis-cli SET image100:ping ok
docker exec -it image100-redis redis-cli GET image100:ping
```

期望：`PONG`，以及 `ok`。

### 5.4 本机端口探测

```bash
ss -lntp | grep -E '7311|7312'
```

或：

```bash
bash -c 'echo >/dev/tcp/127.0.0.1/7311' && echo '7311 ok'
bash -c 'echo >/dev/tcp/127.0.0.1/7312' && echo '7312 ok'
```

---



## 6. 防火墙（让 Windows 也能连）



### 6.1 firewalld

```bash
systemctl is-active firewalld

# 若为 active，执行：
firewall-cmd --permanent --add-port=7311/tcp
firewall-cmd --permanent --add-port=7312/tcp
firewall-cmd --reload
firewall-cmd --list-ports
```



### 6.2 在 Windows PowerShell 测试

```powershell
Test-NetConnection 192.168.137.128 -Port 7311
Test-NetConnection 192.168.137.128 -Port 7312
```

`TcpTestSucceeded : True` 表示通。若 IP 变了，换成新 IP。

---



## 7. 应用如何连接（写代码时用）



### 7.1 程序跑在虚拟机本机

```env
DATABASE_URL=postgresql+asyncpg://retouch:retouch_dev@127.0.0.1:7311/retouch
REDIS_URL=redis://127.0.0.1:7312/0
```



### 7.2 程序跑在 Windows，库在虚拟机（当前最常见）

```env
DATABASE_URL=postgresql+asyncpg://retouch:retouch_dev@192.168.137.128:7311/retouch
REDIS_URL=redis://192.168.137.128:7312/0
```



### 7.3 以后应用也进 Docker，且与中间件同一 compose 网络

用**服务名 + 容器内端口**（不是 7311/7312）：

```env
DATABASE_URL=postgresql+asyncpg://retouch:retouch_dev@postgres:5432/retouch
REDIS_URL=redis://redis:6379/0
```



### 7.4 图形工具连库（可选，如 DBeaver）


| 项   | 值                 |
| --- | ----------------- |
| 主机  | `192.168.137.128` |
| 端口  | `7311`            |
| 数据库 | `retouch`         |
| 用户  | `retouch`         |
| 密码  | `retouch_dev`     |


---



## 8. 日常运维

在 `/opt/image100-middleware` 下：

```bash
# 启动 / 停止
docker compose up -d
docker compose stop

# 停掉容器但保留数据卷
docker compose down

# 状态与日志
docker compose ps
docker compose logs -f --tail=200

# 进库
docker exec -it image100-postgres psql -U retouch -d retouch
docker exec -it image100-redis redis-cli
```



### 8.1 备份 PostgreSQL

```bash
mkdir -p /opt/image100-middleware/backup
docker exec image100-postgres \
  pg_dump -U retouch -d retouch -F c -f /tmp/retouch.dump
docker cp image100-postgres:/tmp/retouch.dump \
  /opt/image100-middleware/backup/retouch-$(date +%F).dump
ls -lh /opt/image100-middleware/backup/
```



### 8.2 危险：清空全部中间件数据

```bash
cd /opt/image100-middleware
docker compose down -v
```

会删除 `image100_pg_data` / `image100_redis_data`，**库数据全丢**。不影响你原来的 MySQL 容器。

---



## 9. 常见问题



### 9.1 写成了 `docker-compose` 报 command not found

改用：

```bash
docker compose up -d
```



### 9.2 拉镜像很慢 / 失败

配置 Docker 镜像加速，编辑 `/etc/docker/daemon.json`：

```bash
cat > /etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": ["https://docker.m.daocloud.io"]
}
EOF
systemctl daemon-reload
systemctl restart docker
cd /opt/image100-middleware && docker compose pull
```



### 9.3 端口冲突

```bash
ss -lntp | grep -E '7311|7312'
```

修改 `.env` 中端口后执行：

```bash
docker compose up -d
```

同时改 Windows 侧连接串端口。

### 9.4 Windows 连不上，虚拟机本机却正常

1. 是否执行了第 6 章放行端口
2. IP 是否仍是 `192.168.137.128`（`hostname -I`）
3. VMware 网卡是否为 NAT/桥接且宿主机能 ping 通



### 9.5 改了 `.env` 密码但登录失败

数据卷已用旧密码初始化。处理方式二选一：

- 改回原密码；或  
- `docker compose down -v` 后重建（**清空数据**）



### 9.6 会不会影响已有 MySQL？

不会。本教程只创建 `image100-postgres` / `image100-redis`，不操作 `mysql8-server`。

---



## 10. 验收清单（按顺序打勾）

- [x] `docker compose version` 正常  
- [x] `/opt/image100-middleware` 下已有 `docker-compose.yml` 与 `.env`  
- [x] `docker compose ps` 中 postgres、redis 为 Up/healthy  
- [x] `psql` 能 `SELECT version();`  
- [x] `redis-cli ping` 返回 PONG  
- [x] `7311` / `7312` 本机可访问  
- [x] （可选）Windows `Test-NetConnection 192.168.137.128 -Port 7311/7312` 成功  
- [x] 原有 MySQL（3306）仍在运行（若你需要它）  

全部完成后，中间件部署即结束。业务表以后由应用 Alembic 迁移创建，**现在不必手工建业务表**。

---



## 11. 推荐操作顺序（照着做）

1. Xshell 登录虚拟机（IP：`192.168.137.128`）
2. 执行 **§2.1 / §2.2** 确认 Docker 与端口
3. 执行 **§4.1～§4.4** 创建文件并 `docker compose up -d`
4. 执行 **§5** 验证
5. 需要 Windows 连库时执行 **§6**
6. 记下连接串 **§7.2**，留给后续写 FastAPI

---



## 12. 一页速查

```bash
cd /opt/image100-middleware
docker compose up -d
docker compose ps
docker exec -it image100-postgres psql -U retouch -d retouch -c "SELECT 1;"
docker exec -it image100-redis redis-cli ping
```

Windows → 虚拟机连接串：

```text
postgresql+asyncpg://retouch:retouch_dev@192.168.137.128:7311/retouch
redis://192.168.137.128:7312/0
```

---

**文档结束。** 按第 11 章顺序做即可。某步报错时，把完整命令和终端输出发出来即可继续排查。