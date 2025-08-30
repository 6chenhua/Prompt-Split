"""
用户认证子系统 - 自动生成的代码
原始需求: 用户认证：验证{用户身份}和{权限}...
"""

from flask_login import UserMixin
from werkzeug.security import check_password_hash
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    permissions = db.Column(db.JSON, default=[])
    users = db.relationship('User', backref='role', lazy=True)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    
    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def has_permission(self, permission):
        if not self.role or not self.role.permissions:
            return False
        return permission in self.role.permissions

class AuthService:
    @staticmethod
    def authenticate(username, password):
        user = User.query.filter_by(username=username).first()
        if user and user.verify_password(password):
            return user
        return None
    
    @staticmethod
    def check_permission(user, permission):
        if not user:
            return False
        return user.has_permission(permission)
