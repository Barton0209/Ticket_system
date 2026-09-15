"""
MainWindow - главное окно приложения

Основной интерфейс Excel Studio HR v3.2.1.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QMenuBar, QMenu, QAction, QStatusBar,
    QSplitter, QTreeWidget, QTreeWidgetItem,
    QTabWidget, QTextEdit, QPushButton, QLabel,
    QMessageBox, QFileDialog, QApplication
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QIcon

from ...core.app import Application


class MainWindow(QMainWindow):
    """Главное окно приложения."""
    
    def __init__(self, app: Application):
        """Инициализация главного окна.
        
        Args:
            app: Главный объект приложения.
        """
        super().__init__()
        
        self.app = app
        
        # Настройка окна
        self.setWindowTitle('Excel Studio HR v3.2.1')
        self.setMinimumSize(1200, 800)
        
        # Создаём интерфейс
        self._setup_ui()
        
        # Создаём меню
        self._setup_menu()
        
        # Создаём статус бар
        self._setup_statusbar()
    
    def _setup_ui(self):
        """Создание пользовательского интерфейса."""
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной layout
        main_layout = QVBoxLayout(central_widget)
        
        # Разделитель: дерево файлов / просмотр
        splitter = QSplitter(Qt.Horizontal)
        
        # Левая панель: дерево файлов и листов
        self.files_tree = QTreeWidget()
        self.files_tree.setHeaderLabels(['📁 Файлы и листы'])
        self.files_tree.setMinimumWidth(250)
        splitter.addWidget(self.files_tree)
        
        # Правая панель: вкладки просмотра/редактирования
        self.tabs = QTabWidget()
        splitter.addWidget(self.tabs)
        
        # Начальная вкладка - приветствие
        welcome_widget = self._create_welcome_tab()
        self.tabs.addTab(welcome_widget, '🏠 Главная')
        
        main_layout.addWidget(splitter)
    
    def _create_welcome_tab(self) -> QWidget:
        """Создание вкладки приветствия."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        
        # Заголовок
        title = QLabel('Excel Studio HR v3.2.1')
        title.setStyleSheet('font-size: 24px; font-weight: bold;')
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Подзаголовок
        subtitle = QLabel('Автоматизированная станция обработки кадровой отчётности')
        subtitle.setStyleSheet('font-size: 14px; color: gray;')
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        
        # Профиль развёртывания
        profile = QLabel('Профиль: без прав администратора')
        profile.setStyleSheet('font-size: 12px; color: blue;')
        profile.setAlignment(Qt.AlignCenter)
        layout.addWidget(profile)
        
        # Кнопки действий
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignCenter)
        
        # Кнопка загрузки файлов
        self.btn_add_files = QPushButton('📂 Добавить файлы')
        self.btn_add_files.clicked.connect(self._on_add_files)
        self.btn_add_files.setMinimumSize(200, 50)
        btn_layout.addWidget(self.btn_add_files)
        
        # Кнопка создания job
        self.btn_new_job = QPushButton('📋 Новый шаблон дня')
        self.btn_new_job.clicked.connect(self._on_new_job)
        self.btn_new_job.setMinimumSize(200, 50)
        btn_layout.addWidget(self.btn_new_job)
        
        layout.addLayout(btn_layout)
        
        # Информация о системе
        info = QLabel(
            'Модули: 41 | Операций: 65+ | Критерии приёмки: 40\n'
            'ООО «ВелесстройМонтаж»'
        )
        info.setStyleSheet('font-size: 11px; color: gray;')
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)
        
        return widget
    
    def _setup_menu(self):
        """Создание меню приложения."""
        menubar = self.menuBar()
        
        # Файл
        file_menu = menubar.addMenu('📁 Файл')
        
        add_files_action = QAction('📂 Добавить файлы...', self)
        add_files_action.setShortcut('Ctrl+O')
        add_files_action.triggered.connect(self._on_add_files)
        file_menu.addAction(add_files_action)
        
        save_action = QAction('💾 Сохранить', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self._on_save)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('❌ Выход', self)
        exit_action.setShortcut('Alt+F4')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Правка
        edit_menu = menubar.addMenu('✏️ Правка')
        
        undo_action = QAction('↩️ Отменить', self)
        undo_action.setShortcut('Ctrl+Z')
        undo_action.triggered.connect(self._on_undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction('↪️ Повторить', self)
        redo_action.setShortcut('Ctrl+Y')
        redo_action.triggered.connect(self._on_redo)
        edit_menu.addAction(redo_action)
        
        # Конструктор
        designer_menu = menubar.addMenu('⚙️ Конструктор')
        
        scenarios_action = QAction('📜 Сценарии обработки', self)
        scenarios_action.triggered.connect(self._on_scenarios)
        designer_menu.addAction(scenarios_action)
        
        mappings_action = QAction('🗺️ Шаблоны маппинга', self)
        mappings_action.triggered.connect(self._on_mappings)
        designer_menu.addAction(mappings_action)
        
        # Job
        job_menu = menubar.addMenu('📅 Шаблоны дня')
        
        jobs_action = QAction('📋 Управление job', self)
        jobs_action.triggered.connect(self._on_jobs)
        job_menu.addAction(jobs_action)
        
        run_all_action = QAction('▶️ Запустить все job', self)
        run_all_action.triggered.connect(self._on_run_jobs)
        job_menu.addAction(run_all_action)
        
        # Сервис
        service_menu = menubar.addMenu('🔧 Сервис')
        
        settings_action = QAction('⚙️ Настройки', self)
        settings_action.triggered.connect(self._on_settings)
        service_menu.addAction(settings_action)
        
        health_action = QAction('❤️ Здоровье системы', self)
        health_action.triggered.connect(self._on_health)
        service_menu.addAction(health_action)
        
        # Справка
        help_menu = menubar.addMenu('❓ Справка')
        
        about_action = QAction('ℹ️ О программе', self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)
    
    def _setup_statusbar(self):
        """Создание статус бара."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        # Статус
        self.status_label = QLabel('Готов')
        self.statusbar.addWidget(self.status_label)
        
        # Прогресс
        self.progress_bar = None  # Будет создан при необходимости
    
    @Slot()
    def _on_add_files(self):
        """Обработчик добавления файлов."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            'Добавить файлы',
            '',
            'Excel файлы (*.xlsx *.xlsm *.xls);;CSV файлы (*.csv);;Все файлы (*)'
        )
        
        if files:
            self.statusbar.showMessage(f'Добавлено файлов: {len(files)}')
            # TODO: Вызвать М1 - загрузка файлов
    
    @Slot()
    def _on_save(self):
        """Обработчик сохранения."""
        self.statusbar.showMessage('Сохранение...')
        # TODO: Вызвать М14 - надёжность
    
    @Slot()
    def _on_undo(self):
        """Обработчик отмены (М14, FR-1402)."""
        self.statusbar.showMessage('Отмена...')
    
    @Slot()
    def _on_redo(self):
        """Обработчик повтора."""
        self.statusbar.showMessage('Повтор...')
    
    @Slot()
    def _on_scenarios(self):
        """Обработчик сценариев (М4)."""
        QMessageBox.information(self, 'Конструктор', 'Модуль М4: Конструктор цепочек')
    
    @Slot()
    def _on_mappings(self):
        """Обработчик маппингов (М5)."""
        QMessageBox.information(self, 'Маппинг', 'Модуль М5: Шаблоны маппинга')
    
    @Slot()
    def _on_jobs(self):
        """Обработчик job (М7, М29)."""
        QMessageBox.information(self, 'Шаблоны дня', 'Модуль М7: Ежедневные шаблоны')
    
    @Slot()
    def _on_run_jobs(self):
        """Обработчик запуска job."""
        QMessageBox.information(self, 'Запуск', 'Запуск всех job...')
    
    @Slot()
    def _on_settings(self):
        """Обработчик настроек (М30)."""
        QMessageBox.information(self, 'Настройки', 'Модуль М30: Конфигурация')
    
    @Slot()
    def _on_health(self):
        """Обработчик здоровья системы (М30, М40)."""
        QMessageBox.information(self, 'Здоровье', 'Модуль М30: Диагностика')
    
    @Slot()
    def _on_about(self):
        """Обработчик о программе."""
        QMessageBox.about(
            self,
            'О программе',
            'Excel Studio HR v3.2.1\n\n'
            'Автоматизированная станция обработки кадровой отчётности\n'
            'ООО «ВелесстройМонтаж»\n\n'
            'Профиль развёртывания: без прав администратора\n'
            '41 модуль | 65+ операций | 40 критериев приёмки'
        )
    
    @Slot()
    def _on_new_job(self):
        """Обработчик создания нового job."""
        self.statusbar.showMessage('Создание нового шаблона дня...')
    
    def closeEvent(self, event):
        """Обработчик закрытия окна."""
        reply = QMessageBox.question(
            self,
            'Выход',
            'Вы уверены, что хотите выйти?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
