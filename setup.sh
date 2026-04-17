#!/bin/bash
# 一键环境初始化脚本
# 使用方式：bash setup.sh
set -e

echo "====== 智能考勤系统环境初始化 ======"
ROOT=$(cd "$(dirname "$0")" && pwd)

# ── 1. Python 后端环境 ─────────────────────────────────────────────
echo ""
echo ">> [1/5] 创建 Python 虚拟环境..."
cd "$ROOT/backend"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "   ✓ .venv 已创建"
else
    echo "   ✓ .venv 已存在"
fi

echo ""
echo ">> [2/5] 安装 Python 依赖..."
.venv/bin/pip install -U pip -q
# 基础 web 依赖
.venv/bin/pip install \
    Flask Flask-SQLAlchemy Flask-JWT-Extended Flask-CORS Flask-Migrate \
    Flask-SocketIO eventlet gunicorn PyMySQL cryptography \
    python-dotenv bcrypt openpyxl \
    -i https://pypi.org/simple/ -q
# AI 依赖（torch CPU 版本，约 500MB）
echo "   安装 torch CPU 版本（约 500MB，请耐心等待）..."
.venv/bin/pip install torch torchvision \
    --index-url https://download.pytorch.org/whl/cpu -q
.venv/bin/pip install facenet-pytorch opencv-python-headless Pillow numpy \
    -i https://pypi.org/simple/ -q
# 测试工具
.venv/bin/pip install pytest pytest-cov pytest-mock -i https://pypi.org/simple/ -q
echo "   ✓ Python 依赖安装完成"

# ── 2. Node 前端环境 ────────────────────────────────────────────────
echo ""
echo ">> [3/5] 安装前端 Node 依赖..."
cd "$ROOT/frontend"
npm install
echo "   ✓ 前端依赖安装完成"

# ── 3. 配置文件 ─────────────────────────────────────────────────────
echo ""
echo ">> [4/5] 检查环境配置文件..."
if [ ! -f "$ROOT/backend/.env" ]; then
    cp "$ROOT/backend/.env.example" "$ROOT/backend/.env"
    echo "   ✓ .env 已从模板创建，请修改 DEV_DATABASE_URL 中的数据库密码"
else
    echo "   ✓ .env 已存在"
fi
if [ ! -f "$ROOT/frontend/.env" ]; then
    cp "$ROOT/frontend/.env.example" "$ROOT/frontend/.env"
    echo "   ✓ frontend/.env 已创建"
else
    echo "   ✓ frontend/.env 已存在"
fi

# ── 4. 数据库初始化 ─────────────────────────────────────────────────
echo ""
echo ">> [5/5] 初始化 MySQL 数据库..."
cd "$ROOT/backend"
.venv/bin/python scripts/setup_db.py

# ── 完成 ────────────────────────────────────────────────────────────
echo ""
echo "====== 初始化完成！======"
echo ""
echo "启动后端："
echo "  cd backend && .venv/bin/python run.py"
echo ""
echo "启动前端（另开终端）："
echo "  cd frontend && npm run dev"
echo ""
echo "运行测试："
echo "  cd backend && .venv/bin/pytest tests/"
echo ""
echo "默认管理员账号：admin / Admin@123456"
