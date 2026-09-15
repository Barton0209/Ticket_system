"""
М34: Мониторинг файлов
Watchdog за изменениями в папках, авто-обработка.
"""
from typing import Callable, List, Optional
class FileWatcherModule:
    def __init__(self):
        self.watchers = []
    def watch_folder(self, folder: str, callback: Callable[[str], None], patterns: List[str] = None):
        self.watchers.append({"folder": folder, "callback": callback, "patterns": patterns or ["*"]})
    def start(self):
        pass
    def stop(self):
        self.watchers.clear()
    def is_watching(self, folder: str) -> bool:
        return any(w["folder"] == folder for w in self.watchers)
