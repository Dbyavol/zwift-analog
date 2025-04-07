import asyncio
import logging
from PyQt5.QtCore import QThread, pyqtSignal
from bleak import BleakScanner, BleakClient


# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler("trainer_app.log", encoding="utf-8")
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# UUID сервиса и характеристики для пульсометра (Heart Rate Service)
HRS_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
HRS_CHARACTERISTIC_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

# UUID сервиса и характеристики для мощности и каденса
FTMS_SERVICE_UUID = "00001826-0000-1000-8000-00805f9b34fb"
POWER_CHARACTERISTIC_UUID = "00002a63-0000-1000-8000-00805f9b34fb"

class BluetoothScannerThread(QThread):
    """
    Поток для сканирования Bluetooth-устройств.

    Атрибуты:
        device_type (str): Тип искомого устройства (пульсометр или велостанок).
    
    Сигналы:
        scan_finished (list): Список найденных устройств [(имя, MAC), ...].
    """
    scan_finished = pyqtSignal(list)  # [(имя, MAC), ...]
    scanning = False  # Флаг выполнения сканирования

    def __init__(self, device_type):
        super().__init__()
        self.device_type = device_type
        self.running = True

    async def scan_devices(self):
        """Асинхронный поиск устройств."""
        while self.running:
            if not self.scanning:  # Проверяем флаг, чтобы не выполнять сканирование во время подключения
                await asyncio.sleep(1)
                continue

            logger.info(f"[🔍] Поиск {self.device_type}...")
            devices = await BleakScanner.discover()
            found_devices = [(d.name, d.address) for d in devices if d.name]

            # Фильтрация найденных устройств по типу
            filtered_devices = []
            for name, mac in found_devices:
                if self.device_type == "пульсометр" and "Polar" in name:
                    filtered_devices.append((name, mac))
                elif self.device_type == "велостанок" and "Think" in name:
                    filtered_devices.append((name, mac))

            if filtered_devices:
                self.scan_finished.emit(filtered_devices)  # Передача списка найденных устройств

            await asyncio.sleep(3)  # Задержка перед повторным сканированием

    def run(self):
        """Запуск сканирования устройств."""
        asyncio.run(self.scan_devices())

    def stop(self):
        """Остановка сканирования."""
        self.running = False
        logger.info(f"[⏹] Остановка поиска {self.device_type}")

    def pause(self):
        """Приостановка сканирования."""
        self.scanning = False
        logger.info(f"[⏸] Приостановка поиска {self.device_type}")

    def resume(self):
        """Возобновление сканирования."""
        self.scanning = True
        logger.info(f"[▶] Возобновление поиска {self.device_type}")


class BluetoothConnectThread(QThread):
    """
    Поток для подключения к устройству и запуска получения данных.

    Сигналы:
        connection_result (str, bool): MAC-адрес устройства, статус подключения.
        data_received (int): Значение пульса.
    """
    connection_result = pyqtSignal(str, str, bool)
    data_received = pyqtSignal(int)

    def __init__(self, name, mac, device_type):
        super().__init__()
        self.name = name
        self.mac = mac
        self.device_type = device_type
        self.connected = False
        self.running = True

    async def connect_and_listen(self):
        """Асинхронное подключение и запуск потока получения данных."""
        while self.running:
            try:
                logger.info(f"🔗 Подключение к {self.name}:{self.mac}...")
                async with BleakClient(self.mac) as client:
                    self.connected = await client.is_connected()

                    if self.connected:
                        logger.info("✅ Подключение успешно.")
                        self.connection_result.emit(self.name, self.mac, True)

                        # Запуск постоянного чтения данных
                        if self.device_type == 'пульсометр':
                            await client.start_notify(HRS_CHARACTERISTIC_UUID, self.handle_heart_rate)
                        else:
                            await client.start_notify(POWER_CHARACTERISTIC_UUID, self.handle_power_data)
                        while self.connected:
                            await asyncio.sleep(1)
                    else:
                        logger.warning("❌ Не удалось подключиться.")
                        self.connection_result.emit(self.name, self.mac, False)
            except Exception as e:
                logger.error(f"[⚠️] Ошибка подключения: {e}")
                self.connection_result.emit(self.name, self.mac, False)
        
    def handle_power_data(self, _, data):
        """Обрабатывает входящие данные от велостанка."""
        if len(data) < 6:
            logger.warning("⚠️ Недостаточно данных для чтения мощности и каденса.")
            return

        # Ватты (мощность) во втором и третьем байтах (Little Endian)
        power = int.from_bytes(data[2:4], byteorder="little", signed=True)

        # Каденс в четвертом и пятом байтах
        cadence = int.from_bytes(data[4:6], byteorder="little", signed=False)

        logger.info(f"⚡ Мощность: {power} Вт  |  🔄 Каденс: {cadence} об/мин")

        self.data_received.emit(power)

    def handle_heart_rate(self, _, data):
        """Обработка и передача данных пульсометра."""
        heart_rate = data[1]  # Второй байт — значение пульса
        logger.info(f"❤️ Текущий пульс: {heart_rate} уд/мин")
        self.data_received.emit(heart_rate)

    def run(self):
        """Запуск асинхронного подключения."""
        asyncio.run(self.connect_and_listen())
    
    def stop(self):
        self.connected = False
        self.running = False
