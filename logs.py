import logging
import queue
import threading
import datetime
from PyQt5.QtWidgets import QTextEdit

# Глобальная очередь для логов
log_queue = queue.Queue()

class QueueHandler(logging.Handler):
    """Кастомный хендлер для отправки логов в очередь"""
    def emit(self, record):
        log_queue.put(self.format(record))

def setup_logging():
    """Настройка логирования с файлами и очередью"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Очистка старых хендлеров (если уже есть)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Формат логов
    formatter = logging.Formatter("%(asctime)s - %(filename)s - %(levelname)s - %(message)s")

    # Логирование в файл
    file_handler = logging.FileHandler("trainer_app.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Логирование в очередь (для GUI)
    queue_handler = QueueHandler()
    queue_handler.setFormatter(formatter)
    logger.addHandler(queue_handler)

    return logger

# Время начала текущей сессии для фильтрации логов
session_start_time = datetime.datetime.now()

class LogUpdater(threading.Thread):
    """Поток для обновления логов в QTextEdit"""
    def __init__(self, log_widget: QTextEdit):
        super().__init__(daemon=True)
        self.log_widget = log_widget

    def run(self):
        while True:
            log_record = log_queue.get()  # Получаем запись из очереди
            timestamp_str, log_msg = log_record.split(" - ", 1)
            timestamp = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f")

            # Фильтруем только свежие логи
            if timestamp >= session_start_time:
                self.log_widget.append(log_record)
