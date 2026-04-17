"""创建初始管理员账号"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "development")

from app import create_app
from app.extensions import db
from app.models.user import User

app = create_app("development")
with app.app_context():
    if User.query.filter_by(username="admin").first():
        print("admin 已存在")
    else:
        u = User(username="admin", role="admin", real_name="系统管理员")
        u.set_password("Admin@123456")
        db.session.add(u)
        db.session.commit()
        print(f"✓ 管理员已创建 id={u.id}  账号: admin / Admin@123456")
