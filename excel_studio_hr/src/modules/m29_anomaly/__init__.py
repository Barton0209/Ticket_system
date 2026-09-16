"""
М29: Поиск аномалий
Статистические методы обнаружения выбросов.
"""
from typing import List, Dict, Any
class AnomalyModule:
    def __init__(self):
        pass
    def zscore_anomalies(self, data: List[float], threshold: float = 3.0) -> List[int]:
        return []
    def iqr_anomalies(self, data: List[float]) -> List[int]:
        return []
    def isolation_forest(self, data: List[List[float]], contamination: float = 0.1) -> List[int]:
        return []

__all__ = ['AnomalyModule']
