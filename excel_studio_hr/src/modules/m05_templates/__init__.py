"""
М5: Шаблоны и пресеты
FR-0501: Библиотека шаблонов обработки
FR-0502: Сохранение цепочек как шаблонов
FR-0503: Параметризация шаблонов
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import os


@dataclass
class TemplateParameter:
    """Параметр шаблона"""
    name: str
    type: str  # str, int, float, bool, column, file
    default: Any = None
    description: str = ""
    required: bool = False
    choices: List[Any] = field(default_factory=list)


@dataclass
class Template:
    """Шаблон обработки"""
    id: str
    name: str
    description: str
    category: str
    version: str
    author: str
    created_at: str
    updated_at: str
    parameters: List[TemplateParameter]
    steps: List[Dict[str, Any]]  # Цепочка операций
    tags: List[str] = field(default_factory=list)
    icon: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в dict"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'version': self.version,
            'author': self.author,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'parameters': [
                {
                    'name': p.name,
                    'type': p.type,
                    'default': p.default,
                    'description': p.description,
                    'required': p.required,
                    'choices': p.choices
                }
                for p in self.parameters
            ],
            'steps': self.steps,
            'tags': self.tags,
            'icon': self.icon
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Template':
        """Десериализация из dict"""
        params = [
            TemplateParameter(
                name=p['name'],
                type=p['type'],
                default=p.get('default'),
                description=p.get('description', ''),
                required=p.get('required', False),
                choices=p.get('choices', [])
            )
            for p in data.get('parameters', [])
        ]
        
        return cls(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            category=data['category'],
            version=data['version'],
            author=data['author'],
            created_at=data['created_at'],
            updated_at=data['updated_at'],
            parameters=params,
            steps=data['steps'],
            tags=data.get('tags', []),
            icon=data.get('icon', '')
        )


class TemplateModule:
    """Модуль управления шаблонами"""
    
    def __init__(self, templates_dir: str):
        self.templates_dir = templates_dir
        os.makedirs(templates_dir, exist_ok=True)
        self._templates: Dict[str, Template] = {}
        self._load_templates()
    
    def _load_templates(self):
        """Загрузка шаблонов из файлов"""
        if not os.path.exists(self.templates_dir):
            return
        
        for filename in os.listdir(self.templates_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.templates_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        template = Template.from_dict(data)
                        self._templates[template.id] = template
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"Ошибка загрузки шаблона {filename}: {e}")
    
    def save_template(self, template: Template) -> str:
        """Сохранение шаблона"""
        template.updated_at = datetime.now().isoformat()
        filepath = os.path.join(self.templates_dir, f"{template.id}.json")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(template.to_dict(), f, indent=2, ensure_ascii=False)
        
        self._templates[template.id] = template
        return template.id
    
    def get_template(self, template_id: str) -> Optional[Template]:
        """Получение шаблона по ID"""
        return self._templates.get(template_id)
    
    def list_templates(self, category: Optional[str] = None, 
                       tags: Optional[List[str]] = None) -> List[Template]:
        """Список шаблонов с фильтрацией"""
        result = list(self._templates.values())
        
        if category:
            result = [t for t in result if t.category == category]
        
        if tags:
            result = [t for t in result if any(tag in t.tags for tag in tags)]
        
        return sorted(result, key=lambda t: t.name)
    
    def delete_template(self, template_id: str) -> bool:
        """Удаление шаблона"""
        if template_id not in self._templates:
            return False
        
        filepath = os.path.join(self.templates_dir, f"{template_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
        
        del self._templates[template_id]
        return True
    
    def apply_template(self, template_id: str, 
                       params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Применение шаблона с параметрами
        
        Args:
            template_id: ID шаблона
            params: значения параметров
            
        Returns:
            Список шагов с подставленными параметрами
        """
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Шаблон {template_id} не найден")
        
        # Валидация параметров
        for param in template.parameters:
            if param.required and param.name not in params:
                raise ValueError(f"Обязательный параметр {param.name} не указан")
        
        # Подстановка параметров в шаги
        steps = []
        for step in template.steps:
            step_copy = json.loads(json.dumps(step))  # Глубокая копия
            
            # Рекурсивная замена параметров
            step_copy = self._substitute_params(step_copy, params)
            steps.append(step_copy)
        
        return steps
    
    def _substitute_params(self, obj: Any, params: Dict[str, Any]) -> Any:
        """Рекурсивная подстановка параметров"""
        if isinstance(obj, str):
            for key, value in params.items():
                placeholder = f"${{{key}}}"
                if placeholder in obj:
                    obj = obj.replace(placeholder, str(value))
            return obj
        elif isinstance(obj, dict):
            return {k: self._substitute_params(v, params) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_params(item, params) for item in obj]
        return obj
    
    def create_template_from_steps(self, name: str, description: str,
                                   category: str, steps: List[Dict[str, Any]],
                                   parameters: Optional[List[TemplateParameter]] = None,
                                   tags: Optional[List[str]] = None,
                                   author: str = "User") -> Template:
        """Создание шаблона из цепочки операций"""
        import uuid
        
        template = Template(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            category=category,
            version="1.0.0",
            author=author,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            parameters=parameters or [],
            steps=steps,
            tags=tags or []
        )
        
        self.save_template(template)
        return template
    
    def get_categories(self) -> List[str]:
        """Список категорий шаблонов"""
        categories = set(t.category for t in self._templates.values())
        return sorted(categories)
    
    def export_template(self, template_id: str, filepath: str) -> bool:
        """Экспорт шаблона в файл"""
        template = self.get_template(template_id)
        if not template:
            return False
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(template.to_dict(), f, indent=2, ensure_ascii=False)
        return True
    
    def import_template(self, filepath: str) -> Optional[Template]:
        """Импорт шаблона из файла"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            template = Template.from_dict(data)
            self.save_template(template)
            return template
        except Exception as e:
            print(f"Ошибка импорта шаблона: {e}")
            return None

__all__ = ['TemplateParameter', 'Template', 'TemplateModule']
