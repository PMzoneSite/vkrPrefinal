# Как запустить проект (Windows + Docker Desktop)

Ниже два способа запуска:

- **A. Быстро поднять тестовую “студенческую” среду** (Web IDE в браузере) через `docker compose`.
- **B. Запустить веб‑панель управления** (`web/`, FastAPI) и **CLI‑менеджер** (`manager/`) через Python виртуальное окружение (они управляют контейнерами в Docker Desktop).

---

## Предварительные требования

- Docker Desktop установлен и запущен.
- Python 3.10+ (рекомендуется 3.11/3.12) установлен и доступен как `python` в PowerShell.

Проверка:

```powershell
docker --version
docker compose version
python --version
```

---

## A) Запуск тестовой среды (code-server в браузере)

Эта команда поднимет контейнер `student-test-env` и откроет Web IDE на порту `8080`.

Из корня репозитория:

```powershell
docker compose -f .\docker-compose.test.yml up --build -d
```

Дальше:

- **URL**: `http://localhost:8080`
- **Пароль**: `student123` (задан в `docker-compose.test.yml` как `CODE_PASSWORD`)

Остановить:

```powershell
docker compose -f .\docker-compose.test.yml down
```

Если хотите, чтобы файлы были на диске Windows (а не в docker volume), в `docker-compose.test.yml` есть пример bind-mount (закомментирован).

---

## B) Запуск веб‑панели управления (FastAPI) + CLI менеджера

### 1) Создать виртуальное окружение и поставить зависимости

Из корня репозитория:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r .\web\requirements.txt
pip install -r .\manager\requirements.txt
```

Важно:

- Модуль `manager` использует Python-библиотеку `docker` и подключается к Docker Desktop через `docker.from_env()`.
- Docker Desktop **должен быть запущен**, иначе `manager` и веб‑панель не смогут управлять контейнерами.

### 2) Запустить веб‑панель

```powershell
python .\web\app.py
```

Откройте:

- **URL**: `http://localhost:8000`
- **Тестовые учётки**:
  - `admin` / `admin123`
  - `teacher` / `teacher123`
  - `student001` / `student123` (и далее до `student100`)

Если порт `8000` занят (ошибка `winerror 10048`), можно:

- остановить старый процесс, который слушает `8000`, или
- запустить веб‑панель на другом порту:

```powershell
$env:PORT=8001
python .\web\app.py
```

### 3) Собрать базовый образ для студенческих сред (один раз)

В отдельном PowerShell (с активированной `.venv`):

```powershell
python -m manager build
```

Образ по умолчанию: `dev-env-python-base` (см. переменную `DEFAULT_IMAGE`).

### 4) Создать среду для конкретного студента

```powershell
python -m manager create student001
```

Команда выведет:

- URL вида `http://localhost:10xxx`
- сгенерированный пароль (это пароль для входа в code-server)

### 5) Полезные команды менеджера

```powershell
python -m manager list
python -m manager info student001
python -m manager stop student001
python -m manager remove student001
```

---

## Частые проблемы

### Ошибка подключения к Docker

Если видите ошибку вида “Ошибка подключения к Docker”, проверьте:

- Docker Desktop запущен
- `docker ps` в PowerShell работает без ошибок:

```powershell
docker ps
```

### PowerShell не даёт активировать venv

Разрешите выполнение скриптов для текущего пользователя:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

