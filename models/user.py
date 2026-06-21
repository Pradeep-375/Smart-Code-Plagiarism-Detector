from datetime import datetime
import bcrypt


class User:
    def __init__(self, id, name, email, password, role, created_at=None, last_login=None, is_active=True):
        self.id = id
        self.name = name
        self.email = email
        self.password = password
        self.role = role
        self.created_at = created_at or datetime.now()
        self.last_login = last_login
        self.is_active = is_active

    @staticmethod
    def hash_password(password):
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    @staticmethod
    def check_password(password, hashed):
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    def is_admin(self):
        return self.role == 'admin'

    def is_faculty(self):
        return self.role in ('faculty', 'admin')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'created_at': str(self.created_at),
            'last_login': str(self.last_login) if self.last_login else None,
            'is_active': self.is_active
        }
