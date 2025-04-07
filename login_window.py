import sys
import logging
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QLabel,
    QHBoxLayout, QTextEdit
)
from PyQt5.QtCore import Qt, QPoint, QPropertyAnimation, QRect, QEasingCurve
from PyQt5.QtGui import QFont, QColor

from connections import BluetoothConnectThread, BluetoothScannerThread
from main_window import TrainingWindow
from logs import setup_logging, LogUpdater


# Настройка логирования
logging.basicConfig(
    filename="trainer_app.log",
    level=logging.INFO,
    format="%(asctime)s - %(filename)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    encoding="utf-8"
)
logger = logging.getLogger(__name__)

class TrainerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Trainer App")
        self.setGeometry(300, 200, 900, 600)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setStyleSheet("background-color: #121212; color: white; border-radius: 10px;")

        self.dragging = False
        self.offset = QPoint()

        # Настройка логирования
        self.logger = setup_logging()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)

        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel("Trainer App")
        self.title_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.title_label.setStyleSheet("color: #1DB954;")
        self.title_label.setAlignment(Qt.AlignLeft)

        self.close_button = self.create_control_button("✖", "#FF4444")
        self.minimize_button = self.create_control_button("➖", "#1DB954")

        title_bar.addWidget(self.title_label)
        title_bar.addStretch(1)
        title_bar.addWidget(self.minimize_button)
        title_bar.addWidget(self.close_button)

        main_layout.addLayout(title_bar)

        self.trainer_button = self.create_device_button("🚴 Power Source", "#FF6F00")
        self.heart_rate_button = self.create_device_button("❤️ Heart rate Sensor", "#FF6F00")
        self.start_button = self.create_device_button("▶ Старт тренировки", "#00BFFF")
        
        # self.trainer_button.clicked.connect(lambda: self.open_device_selection("велостанок"))
        # self.heart_rate_button.clicked.connect(lambda: self.open_device_selection("пульсометр"))
        self.start_button.clicked.connect(self.start_training)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.trainer_button)
        buttons_layout.addWidget(self.heart_rate_button)
        buttons_layout.addWidget(self.start_button)

        main_layout.addLayout(buttons_layout)

        self.status_label = QLabel("Searching for devices...")
        self.status_label.setFont(QFont("Arial", 12))
        self.status_label.setStyleSheet("color: #BBBBBB; text-align: center;")
        main_layout.addWidget(self.status_label)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background-color: #222222; color: #00FF00; border-radius: 5px;")
        main_layout.addWidget(self.log_output)

        # Поток для обновления логов
        self.log_thread = LogUpdater(self.log_output)
        self.log_thread.start()

        self.setLayout(main_layout)

        self.animate_widget(self.trainer_button, 0)
        self.animate_widget(self.heart_rate_button, 200)

        self.close_button.clicked.connect(self.close)
        self.minimize_button.clicked.connect(self.showMinimized)

        self.scanner_threads = {}
        self.start_scan("велостанок")
        self.start_scan("пульсометр")

    def create_device_button(self, text, color):
        button = QPushButton(text)
        button.setFont(QFont("Arial", 18, QFont.Bold))
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border-radius: 20px;
                padding: 40px;
            }}
            QPushButton:hover {{ background-color: {self.darken_color(color, 20)}; }}
        """)
        return button

    def create_control_button(self, text, color):
        button = QPushButton(text)
        button.setFixedSize(30, 30)
        button.setFont(QFont("Arial", 12, QFont.Bold))
        button.setStyleSheet(f"""
            QPushButton {{ background-color: transparent; color: {color}; border-radius: 5px; }}
            QPushButton:hover {{ background-color: {self.darken_color(color, 50)}; }}
        """)
        return button

    def animate_widget(self, widget, delay):
        anim = QPropertyAnimation(widget, b"geometry")
        anim.setDuration(600)
        anim.setStartValue(QRect(widget.x(), widget.y() + 50, widget.width(), widget.height()))
        anim.setEndValue(QRect(widget.x(), widget.y(), widget.width(), widget.height()))
        anim.setEasingCurve(QEasingCurve.OutBounce)
        anim.start()

    def darken_color(self, color, factor):
        c = QColor(color)
        c = c.darker(100 + factor)
        return c.name()

    def log(self, message, type='info'):
        self.log_output.append(message)  # Обновление окна логов
        self.logger.info(message)  # Запись в файл
    
    def start_training(self):
        """Открываем окно тренировки."""
        trainer_thread = self.connect_thread if self.connect_thread.device_type == "велостанок" else ""
        heart_rate_thread = self.connect_thread if self.connect_thread.device_type == "пульсометр" else ""

        self.training_window = TrainingWindow(trainer_thread, heart_rate_thread)
        self.training_window.show()
        self.close()

    def start_scan(self, device_type):
        logger.info(f"[▶] Начало автосканирования {device_type}...")
        scanner_thread = BluetoothScannerThread(device_type)
        scanner_thread.scan_finished.connect(lambda devices: self.auto_connect(device_type, devices))
        self.scanner_threads[device_type] = scanner_thread
        scanner_thread.start()
        scanner_thread.resume()

    def auto_connect(self, device_type, devices):
        for name, mac in devices:
            logger.info(f"[🔗] Автоподключение к {name} ({mac})...")
            self.scanner_threads[device_type].pause()
            self.start_connection(device_type, name, mac)
            return

    def start_connection(self, device_type, name, mac):
        logger.info(f"[🔄] Подключение к {name} ({mac})...")
        self.connect_thread = BluetoothConnectThread(name, mac, device_type)
        self.connect_thread.connection_result.connect(lambda n, m, s: self.handle_connection_result(device_type, n, m, s))
        self.connect_thread.start()

    def handle_connection_result(self, device_type, name, mac, success):
        if success:
            logger.info(f"[🎉] {name} успешно подключен!")
            if device_type == "велостанок":
                self.trainer_button.setText(f"🚴 {name}\nConnected")
                self.trainer_button.setStyleSheet("background-color: #00BFFF; color: white; border-radius: 20px; padding: 40px;")
            else:
                self.heart_rate_button.setText(f"❤️ {name}\nConnected")
                self.heart_rate_button.setStyleSheet("background-color: #00BFFF; color: white; border-radius: 20px; padding: 40px;")
        else:
            logger.warning(f"[❌] Failed to connect to {name}. Retrying...")
            self.scanner_threads[device_type].resume()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(event.globalPos() - self.offset)

    def mouseReleaseEvent(self, event):
        self.dragging = False

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TrainerApp()
    window.show()
    sys.exit(app.exec_())
