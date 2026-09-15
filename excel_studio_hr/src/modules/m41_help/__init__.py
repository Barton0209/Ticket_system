"""
М41: Справка и обучение
Встроенная справка, туториалы, подсказки.
"""
from typing import List, Dict, Any
class HelpModule:
    def __init__(self):
        self.topics = {}
    def add_topic(self, topic_id: str, title: str, content: str):
        self.topics[topic_id] = {"title": title, "content": content}
    def get_topic(self, topic_id: str) -> Dict[str, str]:
        return self.topics.get(topic_id, {"title": "", "content": ""})
    def search(self, query: str) -> List[Dict[str, Any]]:
        return [t for t in self.topics.values() if query.lower() in t["content"].lower()]
    def get_tutorials(self) -> List[str]:
        return list(self.topics.keys())
