# Веб‑платформа изолированных сред разработки (MVP → полноценная система)

Этот документ описывает:

- архитектуру системы (Git + Docker + code-server + веб‑панель),
- как поднять инфраструктуру на Windows с Docker Desktop,
- как подготовить центральный Git‑репозиторий заданий,
- как студентам работать через VS Code в браузере,
- как сдавать и проверять задания через Git,
- как администратору/преподавателю управлять средами.

Документ рассчитан на режим разработки (локально на одной машине). После стабилизации MVP можно перенести на сервер.

---

## 1) Компоненты системы

### 1.1 Центральный Git‑сервер

Роль: хранит шаблоны заданий и принимает `push` от студентов.

В MVP используется `Gitea` (контейнер). Позже можно заменить на GitLab/GitHub Enterprise.

### 1.2 Docker‑среды студентов

Каждому студенту выдаётся отдельный контейнер с:

- `code-server` (VS Code в браузере),
- языковыми инструментами (Python/C++/...),
- `git` внутри контейнера.

Рабочая директория контейнера монтируется в Docker Volume, поэтому код сохраняется между перезапусками.

### 1.3 Веб‑панель (FastAPI)

Роль:

- авторизация,
- просмотр заданий,
- создание/остановка/удаление контейнеров студентов через Docker API,
- отображение URL и пароля к среде.

Сейчас реализовано на шаблонах (Jinja). API сделан так, чтобы поверх него можно было поднять React фронтенд.

---

## 2) Быстрый старт (локально)

### 2.1 Поднять инфраструктуру (Gitea)

Из корня проекта:

```powershell
docker compose -f .\docker-compose.infra.yml up -d
```

Проверка:

- Gitea: `http://localhost:3000`

Примечание: если у вас нестабильный доступ к Docker Hub (`docker.io`), этот compose использует образ Gitea из `docker.gitea.com`.

### 2.2 Создать пользователя и репозиторий заданий в Gitea

1) Откройте `http://localhost:3000`, пройдите первичную настройку (можно оставить значения по умолчанию, БД уже указана в compose).
2) Создайте организацию `edu`.
3) Создайте репозиторий `edu/assignments` (публичный для MVP).

### 2.3 Подготовить репозиторий заданий (структура веток)

Рекомендуемая схема веток для MVP:

- `main` — базовый шаблон/заготовка
- `assignment-1`, `assignment-2`, ... — ветки с конкретными заданиями

Ветка задания должна содержать:

- `README.md` с текстом задания
- `tests/` или `check.sh` (скрипт проверки)
- стартовый код

Пример (Python):

- `README.md`
- `main.py`
- `tests/test_main.py`
- `pyproject.toml` или `requirements.txt`

Пример (C++):

- `README.md`
- `CMakeLists.txt`
- `src/`
- `tests/` или `check.sh`

### 2.4 Настроить переменные окружения проекта

Файл `.env` в корне проекта:

- `ASSIGNMENTS_TEMPLATE_REPO_URL` — URL репозитория‑шаблона (откуда клонировать)
- `ASSIGNMENTS_PUSH_URL_TEMPLATE` — URL куда студент будет пушить (для MVP совпадает)

Сейчас установлены значения для локального Gitea:

- `ASSIGNMENTS_TEMPLATE_REPO_URL=http://localhost:3000/edu/assignments.git`
- `ASSIGNMENTS_PUSH_URL_TEMPLATE=http://localhost:3000/edu/assignments.git`

Для `git push` из контейнера нужен доступ на запись. В MVP проще всего использовать HTTP Basic с токеном Gitea:

- создайте пользователя (например `teacher`) и Personal Access Token в Gitea
- заполните в `.env`:
  - `GITEA_HTTP_USER=teacher`
  - `GITEA_HTTP_TOKEN=<token>`

Эти значения используются веб‑панелью для формирования `GIT_PUSH_URL`, который уходит в контейнер.

### 2.5.1 Засеять базовое задание в Git (ветка `assignment-1`)

В репозитории есть заготовка задания в `seed-assignments/assignment-1`.

Чтобы запушить ветку `assignment-1` в `edu/assignments`:

```powershell
.\.venv\Scripts\Activate.ps1
$env:ASSIGNMENTS_TEMPLATE_REPO_URL="http://localhost:3000/edu/assignments.git"
$env:GITEA_HTTP_USER="teacher"
$env:GITEA_HTTP_TOKEN="<token>"
.\seed-assignments\seed.ps1
```

### 2.5 Собрать базовый образ (Python)

```powershell
.\.venv\Scripts\Activate.ps1
python -m manager build
```

### 2.6 Запустить веб‑панель

```powershell
.\.venv\Scripts\Activate.ps1
python .\web\app.py
```

Откройте `http://localhost:8000`.

Учётки:

- `admin` / `admin123`
- `teacher` / `teacher123`
- `student001` / `student123`

Если порт занят:

```powershell
$env:PORT=8001
python .\web\app.py
```

---

## 3) Жизненный цикл задания (как это работает)

### 3.1 Создание среды

Преподаватель/админ нажимает “Создать среду” для студента.

Система:

1) выбирает свободный порт на хосте,
2) поднимает контейнер из базового образа,
3) прокидывает `CODE_PASSWORD` (пароль к code-server),
4) прокидывает `GIT_REPO_URL` и `GIT_BRANCH`,
5) контейнер при старте делает `git clone` в `/home/student/workspace/project`.

### 3.2 Работа студента

Студент открывает URL `http://localhost:10xxx`, вводит пароль и получает VS Code в браузере.

Внутри VS Code:

- исходники в `/home/student/workspace/project`
- можно делать коммиты:

```bash
cd /home/student/workspace/project
git status
git add -A
git commit -m "solve assignment"
```

### 3.3 Сдача через Git

MVP: `push` идёт в тот же репозиторий, но в отдельную ветку неймспейса студента: `students/<id>/<assignment>`.

Пример:

```bash
cd /home/student/workspace/project
git push origin HEAD
```

### 3.4 Проверка

В MVP проверка выполняется внутри контейнера командой, которую задаёт задание (например, `pytest -q` или `./check.sh`).

Полноценная версия:

- тесты запускаются в отдельном “runner” контейнере,
- результаты сохраняются в БД,
- преподаватель видит историю прогонов и коммиты.

---

## 4) Управление образами (языки)

### 4.1 Python образ

Исходники образа: `images/python-base`.

При запуске контейнера `start.sh` поддерживает:

- `GIT_REPO_URL`
- `GIT_BRANCH`
- `GIT_PUSH_URL`
- `GIT_USER_NAME`
- `GIT_USER_EMAIL`

### 4.2 C++ образ (пример)

Добавлен пример: `images/cpp-base/Dockerfile`.

Сборка вручную:

```powershell
docker build -t dev-env-cpp-base .\images\cpp-base
```

Дальше можно расширить `manager` так, чтобы `course=cpp` выбирал `dev-env-cpp-base`.

---

## 5) Что уже реализовано и что дальше

### 5.1 Уже сделано в коде (после последних правок)

- контейнер при старте может автоматически делать `git clone` выбранной ветки,
- API создания среды принимает `assignment_branch`,
- CLI `manager create` принимает `--git-repo-url`, `--git-branch`, `--git-push-url`,
- добавлен compose с инфраструктурой (Gitea/Postgres/Registry),
- добавлен пример образа C++.

### 5.2 Следующий шаг (в реализации)

- каталог заданий в веб‑панели из Git (а не из локального JSON),
- студентский экран: вкладки “Задания / Среда / Проверка / Отправка”,
- кнопка “Проверить” (exec тестов в контейнере и вывод лога),
- нормальная модель сдачи: `students/<id>/<assignment>` ветки или отдельные репозитории,
- PostgreSQL для пользователей/сессий/метаданных и результатов тестов,
- React фронтенд поверх API.

