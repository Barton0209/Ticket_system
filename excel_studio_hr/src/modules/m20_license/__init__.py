"""
М20: Лицензирование
Локальная лицензия (trial/full), активация по ключу, проверка срока.
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json
import os
import hashlib

class LicenseType:
    TRIAL = "trial"
    FULL = "full"
    EXPIRED = "expired"

class LicenseModule:
    """Управление локальной лицензией."""
    
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.license_file = os.path.join(data_dir, "license.json")
        self.license_data: Optional[Dict] = self._load_license()
    
    def _load_license(self) -> Optional[Dict]:
        if os.path.exists(self.license_file):
            with open(self.license_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def _save_license(self):
        with open(self.license_file, 'w', encoding='utf-8') as f:
            json.dump(self.license_data, f, indent=2, ensure_ascii=False)
    
    def activate_trial(self, days: int = 30) -> bool:
        if self.license_data and self.license_data.get('type') == LicenseType.FULL:
            return False
        self.license_data = {
            'type': LicenseType.TRIAL,
            'activated_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(days=days)).isoformat(),
            'key': None
        }
        self._save_license()
        return True
    
    def activate_full(self, license_key: str) -> bool:
        # Простая валидация ключа (в полной версии - криптографическая проверка)
        if len(license_key) < 16:
            return False
        key_hash = hashlib.sha256(license_key.encode()).hexdigest()[:16]
        self.license_data = {
            'type': LicenseType.FULL,
            'activated_at': datetime.now().isoformat(),
            'expires_at': None,
            'key_hash': key_hash
        }
        self._save_license()
        return True
    
    def check_status(self) -> Dict[str, Any]:
        if not self.license_data:
            return {'type': LicenseType.EXPIRED, 'valid': False, 'days_left': 0}
        
        if self.license_data['type'] == LicenseType.FULL:
            return {'type': LicenseType.FULL, 'valid': True, 'days_left': None}
        
        expires = datetime.fromisoformat(self.license_data['expires_at'])
        now = datetime.now()
        if now > expires:
            return {'type': LicenseType.EXPIRED, 'valid': False, 'days_left': 0}
        
        days_left = (expires - now).days
        return {'type': LicenseType.TRIAL, 'valid': True, 'days_left': days_left}
    
    def is_valid(self) -> bool:
        status = self.check_status()
        return status['valid']
    
    def deactivate(self) -> bool:
        self.license_data = None
        if os.path.exists(self.license_file):
            os.remove(self.license_file)
        return True
