# Подробная настройка связки Gitea + проект

Этот документ описывает рабочую схему:

- преподаватель хранит шаблоны заданий в репозитории `edu/assignments`,
- при создании среды студента система автоматически создаёт отдельный репозиторий `edu/student-<student_id>`,
- система копирует выбранную ветку задания в ветку `students/<student_id>/<assignment_branch>` внутри репозитория студента,
- студент работает в code-server и отправляет решение `git push origin HEAD` в свой репозиторий,
- преподаватель проверяет решения из студенческих репозиториев.

## Как правильно понимать хранение данных

Правильная модель для вашего сценария:

1. Шаблоны и эталонные тесты живут в репозитории преподавателя.
2. Работа каждого студента хранится в отдельном репозитории студента.
3. В контейнере студента код хранится в Docker volume.
4. Git нужен как журнал изменений и механизм сдачи.

Это лучше, чем хранить всё в одном репозитории, потому что проще:

- разграничивать доступ,
- смотреть прогресс по каждому студенту,
- не смешивать студенческие коммиты между собой.

## 1. Поднять Gitea

Из корня проекта:

```powershell
docker compose -f .\docker-compose.infra.yml up -d
```

Проверить:

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:3000 | Select-Object StatusCode
```

Ожидается `200`.

## 2. Первичная настройка Gitea

1. Откройте `http://localhost:3000`.
2. Пройдите initial setup.
3. Создайте пользователя-админа, например `admin`.
4. Создайте организацию `edu`.
5. Создайте репозиторий преподавателя: `edu/assignments`.

## 3. Подготовить репозиторий заданий преподавателя

Рекомендуемый формат веток:

- `assignment-1`
- `assignment-2`
- `assignment-3`

Каждая ветка должна содержать минимум:

- `README.md`
- код-заготовку
- `check.sh` или `tests/`

В проект уже добавлен seed-набор `seed-assignments/assignment-1`.

## 4. Создать токены в Gitea

Нужно два токена:

1. `GITEA_ADMIN_TOKEN`  
   для API-запросов создания репозиториев студентов.

2. `GITEA_HTTP_TOKEN`  
   для git clone/push через HTTP.

Как создать:

1. Войти под нужным пользователем.
2. Settings -> Applications -> Generate New Token.
3. Дать права repo и org.
4. Скопировать токен.

## 5. Заполнить `.env`

Откройте `.env` и заполните:

```env
ASSIGNMENTS_TEMPLATE_REPO_URL=http://localhost:3000/edu/assignments.git
ASSIGNMENTS_PUSH_URL_TEMPLATE=http://localhost:3000/edu/assignments.git
GITEA_HTTP_USER=admin
GITEA_HTTP_TOKEN=<token-for-http-git>
GITEA_URL=http://localhost:3000
GITEA_ORG=edu
GITEA_ADMIN_USER=admin
GITEA_ADMIN_TOKEN=<token-for-api>
GITEA_STUDENT_REPO_PREFIX=student-
USE_PER_STUDENT_REPO=1
GITEA_PREFER_ADMIN_TOKEN_FOR_GIT=1
```

Ключевые параметры:

- `USE_PER_STUDENT_REPO=1` включает режим автосоздания отдельного репозитория для каждого студента.
- `GITEA_ADMIN_USER` должен совпадать с владельцем `GITEA_ADMIN_TOKEN`.
- `GITEA_HTTP_USER` и `GITEA_HTTP_TOKEN` должны быть парой от одного и того же пользователя.
- `GITEA_PREFER_ADMIN_TOKEN_FOR_GIT=1` включает безопасный режим, при котором clone/push внутри платформы выполняются от владельца админ-токена (рекомендуется для MVP).
- Не оставляйте пробелы перед значениями в `.env`.

## 6. Загрузить базовое задание в `edu/assignments`

```powershell
.\.venv\Scripts\Activate.ps1
$env:ASSIGNMENTS_TEMPLATE_REPO_URL="http://localhost:3000/edu/assignments.git"
$env:GITEA_HTTP_USER="admin"
$env:GITEA_HTTP_TOKEN="<token-for-http-git>"
.\seed-assignments\seed.ps1
```

Проверка:

- в Gitea в `edu/assignments` должна появиться ветка `assignment-1`.

## 7. Запустить приложение

```powershell
.\.venv\Scripts\Activate.ps1
python .\web\app.py
```

Если сервер уже был запущен до изменений, обязательно остановите старый процесс и запустите заново.

## 8. Что происходит при создании среды

Когда преподаватель или студент вызывает создание среды:

1. Приложение проверяет наличие репозитория `edu/student-<student_id>`.
2. Если репозитория нет, создаёт его через Gitea API.
3. Клонирует ветку задания из `edu/assignments`.
4. Пушит её в ветку `students/<student_id>/<assignment_branch>` в репозиторий студента.
5. Создаёт или переиспользует Docker-контейнер студента.
6. Контейнер запускает code-server и клонирует студенческий репозиторий в `/home/student/workspace/project`.

Итог:

- студент видит задание сразу в VS Code,
- студент пушит только в свой репозиторий.

## 9. Как студент решает и отправляет

Через UI:

- выбрать задание,
- нажать создать среду,
- нажать проверить,
- нажать отправить.

Через терминал в VS Code:

```bash
cd /home/student/workspace/project
git status
git add -A
git commit -m "submit assignment-1"
git push origin HEAD
```

## 10. Как преподаватель проверяет

Вариант 1:

- открыть `edu/student-<student_id>`,
- смотреть ветку `students/<student_id>/<assignment_branch>`,
- смотреть историю коммитов и diff.

Вариант 2:

```powershell
git clone http://localhost:3000/edu/student-student005.git
cd .\student-student005
git checkout students/student005/assignment-1
```

## 11. Диагностика типовых ошибок

### `TemplateNotFound: assignments/create.html`

Причина: неверный путь к шаблонам в `web/assignments/api.py`.

Исправлено: шаблоны берутся через абсолютный путь `web/templates`.

### `409 Conflict container name already in use`

Причина: контейнер уже существует.

Исправлено: при создании среда переиспользуется/перезапускается.

### `git ls-remote` не показывает ветки

Проверьте:

- `ASSIGNMENTS_TEMPLATE_REPO_URL`,
- доступность Gitea,
- приватность репозитория и токены.

### Ошибка push из контейнера

Проверьте:

- `GITEA_HTTP_USER`,
- `GITEA_HTTP_TOKEN`,
- права токена на запись в репозитории.

## 12. Рекомендуемый рабочий процесс

1. Преподаватель создаёт/обновляет ветку задания в `edu/assignments`.
2. Студент выбирает задание в UI.
3. Система создаёт его репозиторий при первом запуске.
4. Студент кодит, запускает проверку, отправляет push.
5. Преподаватель проверяет конкретный студенческий репозиторий.

