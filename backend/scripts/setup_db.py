"""
数据库初始化脚本：建库、建表、写入初始 admin 账号

运行方式（在 backend/ 目录下执行）：
  python scripts/setup_db.py

环境要求：
  - MySQL 已启动，且 .env 中 DEV_DATABASE_URL 可访问
  - Python 虚拟环境已激活（. .venv/bin/activate）
"""
import os
import sys

# 确保 backend/ 在 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get(
    "DEV_DATABASE_URL",
    "mysql+pymysql://root:password@localhost:3306/attendance_dev?charset=utf8mb4",
)

# ── 1. 解析连接参数 ──────────────────────────────────────────────────
# mysql+pymysql://user:pass@host:port/dbname?...
import re
m = re.match(
    r"mysql\+pymysql://(?P<user>[^:]+):(?P<password>[^@]*)@(?P<host>[^:/]+)(?::(?P<port>\d+))?/(?P<dbname>[^?]+)",
    DB_URL,
)
if not m:
    print("ERROR: 无法解析 DEV_DATABASE_URL，请检查 .env 配置")
    sys.exit(1)

USER = m.group("user")
PASSWORD = m.group("password")
HOST = m.group("host")
PORT = int(m.group("port") or 3306)
DBNAME = m.group("dbname")

print(f"连接 MySQL: {USER}@{HOST}:{PORT}")

# ── 2. 建库 ─────────────────────────────────────────────────────────
try:
    conn = pymysql.connect(host=HOST, port=PORT, user=USER, password=PASSWORD,
                           charset="utf8mb4")
    with conn.cursor() as cur:
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DBNAME}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DBNAME.replace('dev', 'test')}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    conn.commit()
    conn.close()
    print(f"✓ 数据库 {DBNAME} 已就绪")
except Exception as e:
    print(f"✗ 建库失败: {e}")
    print("  请确认 MySQL 已启动，且用户名密码正确。")
    print("  默认密码 'password' 可通过 .env 中 DEV_DATABASE_URL 修改。")
    sys.exit(1)

# ── 3. Flask-Migrate 建表 ───────────────────────────────────────────
from app import create_app
from app.extensions import db

app = create_app("development")

with app.app_context():
    migrations_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "migrations")
    if not os.path.exists(migrations_dir):
        print("初始化 Flask-Migrate 迁移目录...")
        from flask_migrate import init, migrate as migrate_cmd, upgrade
        init()
        migrate_cmd(message="initial schema")
        upgrade()
    else:
        print("运行 Flask-Migrate upgrade...")
        from flask_migrate import upgrade
        upgrade()
    print("✓ 数据库表结构已就绪")

    # ── 4. 写入初始 admin 账号 ──────────────────────────────────────
    from app.models.user import User
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(username="admin", role="admin", real_name="系统管理员")
        admin.set_password("Admin@123456")
        db.session.add(admin)
        db.session.commit()
        print("✓ 初始管理员账号已创建: admin / Admin@123456")
    else:
        print("✓ 管理员账号已存在，跳过创建")

print("\n数据库初始化完成！")
print("启动后端：cd backend && python run.py")
print("启动前端：cd frontend && npm run dev")
