
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
        self.graph_widget = pg.PlotWidget(self)
        layout.addWidget(self.graph_widget)

        self.setLayout(layout)

        # Минималистичная настройка графика
        self.graph_widget.setBackground(None)  # Прозрачный фон
        self.graph_widget.showGrid(False, False)
        self.graph_widget.getAxis('left').setVisible(False)
        self.graph_widget.getAxis('bottom').setVisible(False)

        # Линии графика
        self.power_plot = self.graph_widget.plot(pen=pg.mkPen('b', width=2))
        self.heart_rate_plot = self.graph_widget.plot(pen=pg.mkPen('r', width=2))
        self.cadence_plot = self.graph_widget.plot(pen=pg.mkPen('g', width=2))

        self.x_data = []
        self.power_data = []
        self.cadence_data = []
        self.heart_rate_data = []

        self.time_counter = 0

        # Флаги получения данных
        self.received_power = False
        self.received_heart_rate = False

        # Таймер обновления графика
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_graph)
        self.timer.start(1000)  # Обновление каждую секунду

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

    def update_heart_rate(self, value):
        self.heart_rate_label.setText(f"Пульс (уд/мин): {value}")
        self.heart_rate_data.append(value)
        
        self.received_heart_rate = True
        
    def update_graph(self):
        """Обновление графика."""
        self.x_data.append(self.time_counter)
        self.time_counter += 1

        # Если данных не было - добавляем пустые значения
        if not self.received_power:
            self.power_data.append(0)
            self.cadence_data.append(0)
        if not self.received_heart_rate:
            self.heart_rate_data.append(0)

        # Сбрасываем флаги
        self.received_power = False
        self.received_heart_rate = False

        if self.show_power_checkbox.isChecked():
            self.power_plot.setData(self.x_data, self.power_data)
        else:
            self.power_plot.clear()
        '''
        if self.show_cadence_checkbox.isChecked():
            self.cadence_plot.setData(self.x_data, self.cadence_data)
        else:
            self.cadence_plot.clear()
        '''
        if self.show_heart_rate_checkbox.isChecked():
            self.heart_rate_plot.setData(self.x_data, self.heart_rate_data)
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

