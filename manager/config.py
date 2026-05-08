import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

class Config:
    """Конфигурация системы управления средами"""
    
    # Docker образ по умолчанию
    DEFAULT_IMAGE = os.getenv("DEFAULT_IMAGE", "dev-env-python-base")
    
    # Префикс для имен контейнеров
    CONTAINER_PREFIX = os.getenv("CONTAINER_PREFIX", "student-env-")
    
    # Порт code-server внутри контейнера
    CONTAINER_PORT = int(os.getenv("CONTAINER_PORT", "8080"))
    
    # Диапазон портов на хосте для маппинга
    HOST_PORT_START = int(os.getenv("HOST_PORT_START", "10000"))
    HOST_PORT_END = int(os.getenv("HOST_PORT_END", "20000"))
    
    # Пароль по умолчанию (в реальной системе генерировать!)
    DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD", "student123")
    
    # Лимиты ресурсов
    CPU_LIMIT = os.getenv("CPU_LIMIT", "1.0")
    MEMORY_LIMIT = os.getenv("MEMORY_LIMIT", "1g")
    
    # Путь к Dockerfile для сборки образа
    DOCKERFILE_PATH = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "images",
        "python-base"
    )

config = Config()