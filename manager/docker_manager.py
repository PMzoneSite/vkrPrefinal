import docker
import random
import string
import time
import os
from typing import Dict, Optional, List
from dotenv import load_dotenv

# Загружаем переменные окружения
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


class DockerManager:
    """Менеджер для работы с Docker контейнерами"""
    
    def __init__(self):
        """Инициализация Docker клиента"""
        try:
            # Для Windows с Docker Desktop используем default
            self.client = docker.from_env()
            # Проверяем подключение
            self.client.ping()
            print("[ok] Docker daemon подключен")
        except Exception as e:
            print(f"[error] Ошибка подключения к Docker: {e}")
            raise
    
    def build_image(self, tag: str = None, force: bool = False) -> str:
        """Сборка Docker образа из Dockerfile"""
        if tag is None:
            tag = config.DEFAULT_IMAGE
        
        # Проверяем, существует ли образ уже
        try:
            existing_images = self.client.images.list(name=tag)
            if existing_images and not force:
                print(f"Образ {tag} уже существует. Используем существующий.")
                return tag
        except:
            pass
        
        print(f"Сборка образа {tag}...")
        try:
            image, build_logs = self.client.images.build(
                path=config.DOCKERFILE_PATH,
                tag=tag,
                rm=True,
                pull=True
            )
            
            # Выводим логи сборки
            for log in build_logs:
                if 'stream' in log:
                    line = log['stream'].strip()
                    if line:
                        print(f"  {line}")
            
            print(f"[ok] Образ {tag} успешно собран")
            return tag
        except docker.errors.BuildError as e:
            print(f"[error] Ошибка сборки образа: {e}")
            for log in e.build_log:
                if 'stream' in log:
                    print(log['stream'].strip())
            raise
    
    def find_available_port(self) -> int:
        """Поиск свободного порта в заданном диапазоне"""
        used_ports = set()
        
        # Получаем все контейнеры и их порты
        containers = self.client.containers.list(all=True)
        for container in containers:
            ports = container.attrs['NetworkSettings']['Ports']
            if ports:
                for port_map in ports.values():
                    if port_map:
                        for mapping in port_map:
                            if 'HostPort' in mapping:
                                used_ports.add(int(mapping['HostPort']))
        
        # Ищем свободный порт
        for port in range(config.HOST_PORT_START, config.HOST_PORT_END):
            if port not in used_ports:
                return port
        
        raise RuntimeError("Нет свободных портов в заданном диапазоне")
    
    def generate_password(self, length: int = 12) -> str:
        """Генерация случайного пароля"""
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(random.choice(chars) for _ in range(length))
    
    def create_environment(
        self,
        student_id: str,
        course: str = "python",
        git_repo_url: str | None = None,
        git_branch: str | None = None,
        git_push_url: str | None = None,
    ) -> Dict:
        """Создание новой среды для студента"""
        
        container_name = f"{config.CONTAINER_PREFIX}{student_id}"
        try:
            existing = self.client.containers.get(container_name)
            existing.reload()
            if existing.status == "restarting":
                try:
                    existing.remove(force=True)
                except Exception:
                    pass
                existing = None
            if existing is not None:
                info = self.get_environment_info(student_id)
                if existing.status != "running":
                    existing.start()
                    existing.reload()
                    info = self.get_environment_info(student_id)
                host_port = None
                if info:
                    hp = info.get("host_port")
                    if hp and hp != "N/A":
                        host_port = str(hp)
                if not host_port:
                    ports = existing.attrs.get("NetworkSettings", {}).get("Ports", {}) or {}
                    port_key = f"{config.CONTAINER_PORT}/tcp"
                    if port_key in ports and ports[port_key]:
                        host_port = str(ports[port_key][0].get("HostPort"))
                return {
                    "student_id": student_id,
                    "container_id": (info or {}).get("container_id", existing.id[:12]),
                    "container_name": container_name,
                    "host_port": int(host_port) if host_port and host_port.isdigit() else (host_port or "N/A"),
                    "password": (info or {}).get("password"),
                    "status": existing.status,
                    "created_at": existing.attrs.get("Created"),
                    "web_url": f"http://localhost:{host_port}" if host_port and host_port != "N/A" else None,
                    "reused": True,
                }
        except docker.errors.NotFound:
            pass

        password = self.generate_password()
        host_port = self.find_available_port()
        
        print(f"Создание среды для студента {student_id}...")
        print(f"  Имя контейнера: {container_name}")
        print(f"  Пароль: {password}")
        print(f"  Веб-доступ: http://localhost:{host_port}")
        
        # Параметры запуска контейнера
        environment_vars = {
            "CODE_PASSWORD": password,
            "STUDENT_ID": student_id,
            "COURSE": course
        }
        if git_repo_url:
            environment_vars["GIT_REPO_URL"] = git_repo_url
        if git_branch:
            environment_vars["GIT_BRANCH"] = git_branch
        if git_push_url:
            environment_vars["GIT_PUSH_URL"] = git_push_url
        if git_branch and not str(git_branch).startswith("students/"):
            environment_vars["GIT_STUDENT_BRANCH"] = f"students/{student_id}/{git_branch}"
        environment_vars["GIT_USER_NAME"] = student_id
        environment_vars["GIT_USER_EMAIL"] = f"{student_id}@local"
        
        try:
            # Запускаем контейнер
            container = self.client.containers.run(
                image=config.DEFAULT_IMAGE,
                name=container_name,
                detach=True,
                ports={f"{config.CONTAINER_PORT}/tcp": host_port},
                environment=environment_vars,
                volumes={
                    f"{container_name}-data": {
                        'bind': '/home/student/workspace',
                        'mode': 'rw'
                    }
                },
                mem_limit=config.MEMORY_LIMIT,
                cpu_quota=int(float(config.CPU_LIMIT) * 100000),  # Convert to microseconds
                restart_policy={"Name": "unless-stopped"}
                # Убрали remove=True, так как он несовместим с restart_policy
            )
            
            # Ждем запуска code-server
            print("  Ожидание запуска code-server...", end="", flush=True)
            for _ in range(30):  # Ждем до 30 секунд
                time.sleep(1)
                container.reload()
                if container.status == "running":
                    logs = container.logs(tail=10).decode('utf-8')
                    if "code-server" in logs.lower():
                        print(" [ok]")
                        break
                print(".", end="", flush=True)
            else:
                print(" [warn] (таймаут)")
            
            return {
                "student_id": student_id,
                "container_id": container.id[:12],
                "container_name": container_name,
                "host_port": host_port,
                "password": password,
                "status": container.status,
                "created_at": container.attrs['Created'],
                "web_url": f"http://localhost:{host_port}"
            }
            
        except docker.errors.APIError as e:
            print(f"[error] Ошибка создания контейнера: {e}")
            raise
    
    def stop_environment(self, student_id: str) -> bool:
        """Остановка среды студента"""
        container_name = f"{config.CONTAINER_PREFIX}{student_id}"
        
        try:
            container = self.client.containers.get(container_name)
            print(f"Остановка среды {student_id}...")
            container.stop()
            print(f"[ok] Среда {student_id} остановлена")
            return True
        except docker.errors.NotFound:
            print(f"[error] Контейнер для студента {student_id} не найден")
            return False
        except Exception as e:
            print(f"[error] Ошибка остановки: {e}")
            return False
    
    def remove_environment(self, student_id: str) -> bool:
        """Полное удаление среды (контейнер + volume)"""
        container_name = f"{config.CONTAINER_PREFIX}{student_id}"
        volume_name = f"{container_name}-data"
        
        try:
            # Останавливаем и удаляем контейнер
            try:
                container = self.client.containers.get(container_name)
                if container.status == "running":
                    container.stop()
                container.remove(force=True)
                print(f"[ok] Контейнер {student_id} удален")
            except docker.errors.NotFound:
                print(f"  Контейнер для {student_id} не найден")
            
            # Удаляем volume
            try:
                volume = self.client.volumes.get(volume_name)
                volume.remove(force=True)
                print(f"[ok] Volume {student_id} удален")
            except:
                print(f"  Volume для {student_id} не найден или уже удален")
            
            return True
            
        except Exception as e:
            print(f"[error] Ошибка удаления: {e}")
            return False
    
    def list_environments(self) -> List[Dict]:
        """Получение списка всех студенческих сред"""
        containers = []
        
        try:
            all_containers = self.client.containers.list(
                all=True,
                filters={"name": config.CONTAINER_PREFIX}
            )
            
            for container in all_containers:
                # Получаем информацию о портах
                ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
                host_port = "N/A"
                
                port_key = f"{config.CONTAINER_PORT}/tcp"
                if ports and port_key in ports:
                    port_mapping = ports[port_key]
                    if port_mapping and isinstance(port_mapping, list):
                        host_port = port_mapping[0].get('HostPort', 'N/A')
                
                # Получаем student_id из имени контейнера
                student_id = container.name.replace(config.CONTAINER_PREFIX, "")
                
                containers.append({
                    "student_id": student_id,
                    "container_id": container.id[:12],
                    "status": container.status,
                    "host_port": host_port,
                    "created": container.attrs.get('Created', 'N/A')[:19] if container.attrs.get('Created') else "N/A",
                    "image": container.image.tags[0] if container.image.tags else "N/A"
                })
            
            return containers
            
        except Exception as e:
            print(f"[error] Ошибка получения списка контейнеров: {e}")
            return []
    
    def get_environment_info(self, student_id: str) -> Optional[Dict]:
        """Получение информации о конкретной среде"""
        container_name = f"{config.CONTAINER_PREFIX}{student_id}"
        
        try:
            container = self.client.containers.get(container_name)
            
            # Получаем информацию о портах
            ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
            host_port = "N/A"
            
            port_key = f"{config.CONTAINER_PORT}/tcp"
            if ports and port_key in ports:
                port_mapping = ports[port_key]
                if port_mapping and isinstance(port_mapping, list):
                    host_port = port_mapping[0].get('HostPort', 'N/A')
            
            # Безопасное получение IP адреса
            network_settings = container.attrs.get('NetworkSettings', {})
            ip_address = network_settings.get('IPAddress', '')
            if not ip_address:
                ip_address = 'N/A'
            
            # ПОЛУЧАЕМ ПАРОЛЬ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ КОНТЕЙНЕРА
            env_vars = container.attrs.get('Config', {}).get('Env', [])
            password = "неизвестен"
            
            for env in env_vars:
                if env and '=' in env:
                    key, value = env.split('=', 1)
                    if key == 'CODE_PASSWORD':
                        password = value
                        break
            
            # Если не нашли в env, пробуем получить из logs
            if password == "неизвестен":
                try:
                    logs = container.logs(tail=50).decode('utf-8', errors='ignore')
                    if 'PASSWORD=' in logs:
                        for line in logs.split('\n'):
                            if 'PASSWORD=' in line:
                                password = line.split('PASSWORD=')[1].strip()
                                break
                except:
                    pass
            
            return {
                "student_id": student_id,
                "container_id": container.id[:12],
                "status": container.status,
                "host_port": host_port,
                "created": container.attrs.get('Created', 'N/A'),
                "image": container.image.tags[0] if container.image.tags else "N/A",
                "ip_address": ip_address,
                "password": password  # ВОЗВРАЩАЕМ ПАРОЛЬ
            }
        except docker.errors.NotFound:
            return None
        except Exception as e:
            print(f"Ошибка в get_environment_info для {student_id}: {e}")
            return None

    def exec_in_environment(
        self,
        student_id: str,
        command: str,
        workdir: str = "/home/student/workspace/project",
    ) -> Dict:
        container_name = f"{config.CONTAINER_PREFIX}{student_id}"
        container = self.client.containers.get(container_name)
        cmd = ["bash", "-lc", f"cd {workdir} 2>/dev/null || true; {command}"]
        r = container.exec_run(cmd, stdout=True, stderr=True)
        out = r.output.decode("utf-8", errors="replace") if isinstance(r.output, (bytes, bytearray)) else str(r.output)
        exit_code = int(r.exit_code) if hasattr(r, "exit_code") and r.exit_code is not None else 0
        return {"exit_code": exit_code, "output": out}
    
    def cleanup_old_environments(self, older_than_hours: int = 24) -> int:
        """Очистка старых остановленных контейнеров"""
        count = 0
        try:
            containers = self.client.containers.list(
                all=True,
                filters={
                    "name": config.CONTAINER_PREFIX,
                    "status": "exited"
                }
            )
            
            for container in containers:
                # Проверяем время создания
                created = container.attrs['Created']
                created_timestamp = time.mktime(
                    time.strptime(created[:19], "%Y-%m-%dT%H:%M:%S")
                )
                age_hours = (time.time() - created_timestamp) / 3600
                
                if age_hours > older_than_hours:
                    container.remove()
                    print(f"  Удален старый контейнер: {container.name}")
                    count += 1
            
            if count > 0:
                print(f"[ok] Удалено {count} старых контейнеров")
            else:
                print("  Нет старых контейнеров для удаления")
            
            return count
            
        except Exception as e:
            print(f"[error] Ошибка очистки: {e}")
            return 0