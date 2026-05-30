# 部署指南

## 目录

- [快速开始](#快速开始)
- [环境变量配置](#环境变量配置)
- [Docker Compose 部署](#docker-compose-部署)
- [手动部署](#手动部署)
- [备份与恢复](#备份与恢复)
- [监控与健康检查](#监控与健康检查)
- [安全建议](#安全建议)
- [常见问题](#常见问题)

## 快速开始

### 前置条件

- Docker 20.10+
- Docker Compose v2.0+
- 至少 2GB 可用内存

### 一键部署

```bash
# 1. 克隆项目
git clone <repository-url>
cd daily-headlines

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，修改 JWT_SECRET 和管理员密码

# 3. 启动服务
docker compose up -d

# 4. 访问应用
# 前端: http://localhost
# API:  http://localhost/api/health
# 管理员: admin / admin123 (请立即修改密码)
```

## 环境变量配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `MYSQL_ROOT_PASSWORD` | MySQL root 密码 | `rootpassword` |
| `MYSQL_DATABASE` | 数据库名 | `daily_headlines` |
| `MYSQL_USER` | 数据库用户 | `dailyhead` |
| `MYSQL_PASSWORD` | 数据库密码 | `dailyhead123` |
| `JWT_SECRET` | JWT 签名密钥 | `change-this-in-production` |
| `DEV_ADMIN_USERNAME` | 初始管理员用户名 | `admin` |
| `DEV_ADMIN_PASSWORD` | 初始管理员密码 | `admin123` |
| `CORS_ORIGINS` | 允许的跨域来源 | `http://localhost` |
| `WEB_PORT` | 前端端口 | `80` |

**生产环境必须修改：**
- `JWT_SECRET` - 使用 `openssl rand -hex 32` 生成
- `DEV_ADMIN_PASSWORD` - 使用强密码
- `MYSQL_PASSWORD` - 使用强密码

## Docker Compose 部署

### 服务架构

```
┌─────────────┐     ┌─────────────┐
│   Nginx     │────▶│   API       │
│   (Web)     │     │   (FastAPI) │
└─────────────┘     └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │  MySQL   │ │Meilisearch│ │  Volumes │
        │  8.0     │ │  v1.11   │ │          │
        └──────────┘ └──────────┘ └──────────┘
```

### 常用命令

```bash
# 启动所有服务
docker compose up -d

# 查看日志
docker compose logs -f api
docker compose logs -f web

# 重启服务
docker compose restart api

# 停止所有服务
docker compose down

# 停止并删除数据（危险！）
docker compose down -v
```

### 自定义端口

编辑 `.env` 文件：

```bash
WEB_PORT=8080  # 前端使用 8080 端口
```

## 手动部署

### 后端

```bash
cd apps/api

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
export DATABASE_URL="mysql+pymysql://user:pass@localhost/daily_headlines"
export JWT_SECRET="your-secret-key"

# 运行迁移
alembic upgrade head

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8015
```

### 前端

```bash
cd apps/web

# 安装依赖
npm install

# 开发模式
npm run dev

# 生产构建
npm run build
# 部署 dist/ 目录到 Nginx 或其他 Web 服务器
```

### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    root /path/to/apps/web/dist;
    index index.html;

    # API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:8015;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # SPA 路由
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

## 备份与恢复

### 自动备份

```bash
# 创建备份
./scripts/backup.sh

# 备份保存在 ./backups/ 目录
```

### 恢复备份

```bash
# 恢复指定备份
./scripts/restore.sh ./backups/db_20260529_120000.sql.gz
```

### 定时备份（Cron）

```bash
# 每天凌晨 3 点备份
0 3 * * * cd /path/to/daily-headlines && ./scripts/backup.sh >> /var/log/daily-headlines-backup.log 2>&1
```

## 监控与健康检查

### 健康检查端点

```bash
# API 健康检查（包含数据库连通性）
curl http://localhost/api/health

# 响应示例
{
  "data": {
    "status": "ok",
    "version": "1.0.0",
    "checks": {
      "api": "ok",
      "database": "ok"
    },
    "uptime_seconds": 3600
  }
}
```

### 监控指标端点

```bash
# 应用指标
curl http://localhost/api/metrics

# 响应示例
{
  "data": {
    "uptime_seconds": 3600.0,
    "requests": {
      "total": 1234,
      "errors": 5,
      "avg_response_ms": 45.2
    },
    "timestamp": "2026-05-29T12:00:00+00:00",
    "version": "1.0.0",
    "database": "mysql"
  }
}
```

### Docker 健康检查

所有服务都配置了 Docker 健康检查：

```bash
# 查看服务状态
docker compose ps

# 输出示例
NAME                      STATUS
daily-headlines-api       Up (healthy)
daily-headlines-web       Up (healthy)
daily-headlines-mysql     Up (healthy)
daily-headlines-meilisearch Up (healthy)
```

## 安全建议

### 生产环境清单

- [ ] 修改所有默认密码
- [ ] 使用强随机 JWT_SECRET
- [ ] 配置 HTTPS（使用 Let's Encrypt）
- [ ] 限制 CORS_ORIGINS 为实际域名
- [ ] 定期备份数据库
- [ ] 启用防火墙，只开放 80/443 端口
- [ ] 使用非 root 用户运行容器
- [ ] 定期更新依赖包

### HTTPS 配置

使用 Nginx + Let's Encrypt：

```bash
# 安装 certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

## 常见问题

### Q: 忘记管理员密码怎么办？

```bash
# 重置管理员密码
docker compose exec api python -c "
from app.core.database import SessionLocal
from app.modules.users.models import User
from app.modules.auth.service import hash_password
db = SessionLocal()
admin = db.query(User).filter(User.username == 'admin').first()
if admin:
    admin.password_hash = hash_password('new-password')
    db.commit()
    print('Password updated!')
"
```

### Q: 如何查看 API 日志？

```bash
# 实时日志
docker compose logs -f api

# 最近 100 行
docker compose logs --tail 100 api
```

### Q: 数据库迁移失败怎么办？

```bash
# 查看当前迁移版本
docker compose exec api alembic current

# 手动运行迁移
docker compose exec api alembic upgrade head

# 回滚一个版本
docker compose exec api alembic downgrade -1
```

### Q: 如何添加新的 RSS 源？

1. 登录管理后台
2. 点击"信息源"
3. 选择"RSS"类型
4. 输入 RSS 地址
5. 点击"测试预览"
6. 确认后保存

### Q: OPML 导入导出在哪里？

**导出：**
- 信息源页面 → 右上角"导出 OPML"按钮

**导入：**
- 信息源页面 → 右上角"导入 OPML"按钮
- 支持 `.opml` 和 `.xml` 文件

## 更新升级

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker compose down
docker compose build
docker compose up -d

# 数据库迁移会自动运行
```

## 技术支持

- 问题反馈：GitHub Issues
- 文档：README.md
- 开发计划：docs/DEVELOPMENT_PLAN.md
