
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QDialog, QCheckBox, QHBoxLayout, QPushButton
from PyQt5.QtCore import QTimer, Qt, QDateTime
from PyQt5.QtGui import QFont, QColor
import pyqtgraph as pg
import json

class TrainingWindow(QDialog):
    """Окно тренировки с графиком мощности, пульса и каденса."""
    def __init__(self, trainer_thread, heart_rate_thread):
        super().__init__()
        self.setWindowTitle("Тренировка")
        self.setGeometry(100, 200, 1500, 1000)
        self.setWindowFlags(Qt.FramelessWindowHint)  # Убираем стандартные кнопки управления
        self.setStyleSheet("background-color: #121212; color: white; border-radius: 10px;")

        layout = QVBoxLayout()

        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel("Training window")
        self.title_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.title_label.setStyleSheet("color: #1DB954;")
        self.title_label.setAlignment(Qt.AlignLeft)

        self.close_button = self.create_control_button("✖", "#FF4444")
        self.minimize_button = self.create_control_button("➖", "#1DB954")

        self.close_button.clicked.connect(self.close)
        self.minimize_button.clicked.connect(self.showMinimized)

        title_bar.addWidget(self.title_label)
        title_bar.addStretch(1)
        title_bar.addWidget(self.minimize_button)
        title_bar.addWidget(self.close_button)

        layout.addLayout(title_bar)

        # Данные
        self.power_label = QLabel("Мощность (Вт): -", self)
        self.power_label.setStyleSheet("font-size: 48px;")
        layout.addWidget(self.power_label)

        self.heart_rate_label = QLabel("Пульс (уд/мин): -", self)
        self.heart_rate_label.setStyleSheet("font-size: 48px;")
        layout.addWidget(self.heart_rate_label)

        self.cadence_label = QLabel("Каденс (об/мин): -", self)
        self.cadence_label.setStyleSheet("font-size: 48px;")
        layout.addWidget(self.cadence_label)

        # Чекбоксы для управления графиком
        self.show_power_checkbox = QCheckBox("Показать мощность")
        self.show_power_checkbox.setChecked(True)
        self.show_power_checkbox.toggled.connect(self.update_graph)

        self.show_heart_rate_checkbox = QCheckBox("Показать пульс")
        self.show_heart_rate_checkbox.setChecked(True)
        self.show_heart_rate_checkbox.toggled.connect(self.update_graph)

        self.show_cadence_checkbox = QCheckBox("Показать каденс")
        self.show_cadence_checkbox.setChecked(True)
        self.show_cadence_checkbox.toggled.connect(self.update_graph)

        checkbox_layout = QHBoxLayout()
        checkbox_layout.addWidget(self.show_power_checkbox)
        checkbox_layout.addWidget(self.show_heart_rate_checkbox)
        checkbox_layout.addWidget(self.show_cadence_checkbox)
        layout.addLayout(checkbox_layout)

        # График
        # self.graph_widget = pg.PlotWidget(self)
        # layout.addWidget(self.graph_widget)

        self.setLayout(layout)

        self.power_data = []
        self.heart_rate_data = []
        self.cadence_data = []  # даже если пока не используешь
        self.time_counter = 0
        self.heart_time_counter = 0
        self.power_time_counter = 0
        

        # ======= ДОБАВЛЯЕМ В НАЧАЛЕ __init__ =======
        self.real_time_label = QLabel("", self)
        self.real_time_label.setFont(QFont("Arial", 12))
        self.real_time_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.real_time_label)

        # Таймер для отображения времени
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_real_time)
        self.clock_timer.start(1000)

        # ======= ДВА ГРАФИКА ВМЕСТО ОДНОГО =======
        self.power_graph_widget = pg.PlotWidget(self)
        self.power_graph_widget.setBackground(None)
        self.power_graph_widget.showGrid(True, True)
        self.power_graph_widget.setTitle("Мощность (Вт)", color='w', size='12pt')
        self.power_graph_widget.getAxis('left').setPen('w')
        self.power_graph_widget.getAxis('bottom').setPen('w')
        layout.addWidget(self.power_graph_widget)

        self.heart_graph_widget = pg.PlotWidget(self)
        self.heart_graph_widget.setBackground(None)
        self.heart_graph_widget.showGrid(True, True)
        self.heart_graph_widget.setTitle("Пульс (уд/мин)", color='w', size='12pt')
        self.heart_graph_widget.getAxis('left').setPen('w')
        self.heart_graph_widget.getAxis('bottom').setPen('w')
        layout.addWidget(self.heart_graph_widget)

        self.power_plot = self.power_graph_widget.plot(pen=pg.mkPen('b', width=2))
        self.heart_rate_plot = self.heart_graph_widget.plot(pen=pg.mkPen('r', width=2))

        self.power_time = []
        self.heart_time = []

        # Минималистичная настройка графика
        self.power_graph_widget.setBackground(None)  # Прозрачный фон
        self.power_graph_widget.showGrid(False, False)

        # Минималистичная настройка графика
        self.heart_graph_widget.setBackground(None)  # Прозрачный фон
        self.heart_graph_widget.showGrid(False, False)

        # Флаги получения данных
        self.received_power = False
        self.received_heart_rate = False

        if trainer_thread:
            self.trainer_thread = trainer_thread
            self.trainer_thread.data_received.connect(self.update_power)
            self.trainer_thread.start()

        if heart_rate_thread:
            self.heart_rate_thread = heart_rate_thread
            self.heart_rate_thread.data_received.connect(self.update_heart_rate)
            self.heart_rate_thread.start()

        # Время начала тренировки
        self.start_time = QDateTime.currentDateTime().toString("yyyy-MM-dd_HH-mm-ss")
    
    def create_control_button(self, text, color):
        button = QPushButton(text)
        button.setFixedSize(30, 30)
        button.setFont(QFont("Arial", 12, QFont.Bold))
        button.setStyleSheet(f"""
            QPushButton {{ background-color: transparent; color: {color}; border-radius: 5px; }}
            QPushButton:hover {{ background-color: {self.darken_color(color, 50)}; }}
        """)
        return button

    def darken_color(self, color, factor):
        c = QColor(color)
        c = c.darker(100 + factor)
        return c.name()

    def update_power(self, power):
        self.power_label.setText(f"Мощность (Вт): {power}")

        self.power_data.append(power)

        self.received_power = True
        self.update_graph()

    def update_heart_rate(self, value):
        self.heart_rate_label.setText(f"Пульс (уд/мин): {value}")
        self.heart_rate_data.append(value)
        
        self.received_heart_rate = True
        self.update_graph()
        
    def update_graph(self):
        # Обновление счетчиков
        if self.received_power:
            self.power_time.append(self.power_time_counter)
            self.power_time_counter += 1
        if self.received_heart_rate:
            self.heart_time.append(self.heart_time_counter)
            self.heart_time_counter += 1

        self.time_counter += 1

        # Если данных не пришло — дополняем 0
        if not self.received_power:
            self.power_data.append(0)
            self.power_time.append(self.power_time_counter)
        if not self.received_heart_rate:
            self.heart_rate_data.append(0)
            self.heart_time.append(self.heart_time_counter)

        # Сбрасываем флаги
        self.received_power = False
        self.received_heart_rate = False

        # Обновляем каждый график отдельно
        if self.show_power_checkbox.isChecked():
            self.power_plot.setData(self.power_time, self.power_data)
        else:
            self.power_plot.clear()

        if self.show_heart_rate_checkbox.isChecked():
            self.heart_rate_plot.setData(self.heart_time, self.heart_rate_data)
        else:
            self.heart_rate_plot.clear()

    
    def closeEvent(self, event):
        """Сохранение данных при закрытии."""
        filename = f"training_{self.start_time}.json"
        data = {
            "power": self.power_data,
            "cadence": self.cadence_data,
            "heart_rate": self.heart_rate_data
        }
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        event.accept()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(event.globalPos() - self.offset)

    def mouseReleaseEvent(self, event):
        self.dragging = False
    
    def update_real_time(self):
        current_time = QDateTime.currentDateTime().toString("HH:mm:ss")
        self.real_time_label.setText(f"Текущее время: {current_time}")


