"""
М19: Управление пользователями и ролями
Локальные профили, роли (Admin/Operator/Viewer), права доступа.
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import os

class UserRole:
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"

class UsersModule:
    """Управление локальными пользователями и ролями."""
    
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.users_file = os.path.join(data_dir, "users.json")
        self.users: Dict[str, Dict] = self._load_users()
    
    def _load_users(self) -> Dict[str, Dict]:
        if os.path.exists(self.users_file):
            with open(self.users_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_users(self):
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, indent=2, ensure_ascii=False)
    
    def create_user(self, username: str, password_hash: str, role: str = UserRole.VIEWER) -> bool:
        if username in self.users:
            return False
        self.users[username] = {
            'password_hash': password_hash,
            'role': role,
            'created_at': datetime.now().isoformat(),
            'last_login': None,
            'active': True
        }
        self._save_users()
        return True
    
    def authenticate(self, username: str, password_hash: str) -> Optional[str]:
        user = self.users.get(username)
        if user and user['password_hash'] == password_hash and user['active']:
            user['last_login'] = datetime.now().isoformat()
            self._save_users()
            return user['role']
        return None
    
    def get_user(self, username: str) -> Optional[Dict]:
        return self.users.get(username)
    
    def list_users(self) -> List[str]:
        return list(self.users.keys())
    
    def delete_user(self, username: str) -> bool:
        if username in self.users:
            del self.users[username]
            self._save_users()
            return True
        return False
    
    def set_role(self, username: str, role: str) -> bool:
        if username in self.users:
            self.users[username]['role'] = role
            self._save_users()
            return True
        return False
    
    def has_permission(self, username: str, permission: str) -> bool:
        user = self.users.get(username)
        if not user:
            return False
        perms = {
            UserRole.ADMIN: ['read', 'write', 'delete', 'admin', 'export', 'import'],
            UserRole.OPERATOR: ['read', 'write', 'export'],
            UserRole.VIEWER: ['read']
        }
        return permission in perms.get(user['role'], [])
