"""
М12: Печать и экспорт в PDF
FR-1201: Настройка параметров печати
FR-1202: Экспорт в PDF
"""

from typing import Dict, Any, Optional
import pandas as pd


class PrintModule:
    """Модуль печати"""
    
    def __init__(self):
        self.page_settings = {
            'orientation': 'portrait',
            'paper_size': 'A4',
            'margins': {'top': 20, 'bottom': 20, 'left': 20, 'right': 20},
            'scale': 100,
            'fit_to_page': False
        }
    
    def set_page_setup(self, orientation: str = 'portrait',
                      paper_size: str = 'A4',
                      margins: Optional[Dict[str, int]] = None,
                      scale: int = 100) -> None:
        """Настройка параметров страницы"""
        self.page_settings['orientation'] = orientation
        self.page_settings['paper_size'] = paper_size
        if margins:
            self.page_settings['margins'].update(margins)
        self.page_settings['scale'] = scale
    
    def to_html(self, df: pd.DataFrame, title: str = "Data") -> str:
        """Экспорт в HTML для печати"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>{title}</title></head>
        <body>
        {df.to_html(index=False)}
        </body>
        </html>
        """
        return html


__all__ = ['PrintModule']
