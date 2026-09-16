"""
М17: Планировщик задач
FR-1701: Автоматизация по расписанию
FR-1702: Фоновые задачи
"""

from typing import Dict, Any, Optional, Callable
from datetime import datetime
import json
import os


class SchedulerModule:
    """Модуль планировщика задач"""
    
    def __init__(self, tasks_file: str):
        self.tasks_file = tasks_file
        self.tasks: Dict[str, Dict] = {}
        self._load_tasks()
    
    def _load_tasks(self):
        if os.path.exists(self.tasks_file):
            with open(self.tasks_file, 'r') as f:
                self.tasks = json.load(f)
    
    def _save_tasks(self):
        with open(self.tasks_file, 'w') as f:
            json.dump(self.tasks, f, indent=2)
    
    def add_task(self, task_id: str, name: str, action: str,
                schedule: str, params: Dict[str, Any],
                enabled: bool = True) -> str:
        task = {
            'id': task_id,
            'name': name,
            'action': action,
            'schedule': schedule,  # cron-like формат
            'params': params,
            'enabled': enabled,
            'created_at': datetime.now().isoformat(),
            'last_run': None,
            'next_run': None,
            'status': 'pending'
        }
        self.tasks[task_id] = task
        self._save_tasks()
        return task_id
    
    def remove_task(self, task_id: str) -> bool:
        if task_id in self.tasks:
            del self.tasks[task_id]
            self._save_tasks()
            return True
        return False
    
    def enable_task(self, task_id: str, enabled: bool) -> bool:
        if task_id in self.tasks:
            self.tasks[task_id]['enabled'] = enabled
            self._save_tasks()
            return True
        return False
    
    def get_tasks(self) -> list:
        return list(self.tasks.values())
    
    def run_task(self, task_id: str, callback: Callable) -> bool:
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        try:
            callback(task['action'], task['params'])
            task['last_run'] = datetime.now().isoformat()
            task['status'] = 'completed'
        except Exception as e:
            task['status'] = f'failed: {str(e)}'
        
        self._save_tasks()
        return True


__all__ = ['SchedulerModule']
