from assignments.api import router as assignments_router
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sys
import os
import subprocess
import json
import tempfile
import shutil
from urllib import request as urlrequest
from urllib.error import HTTPError
from pathlib import Path
from dotenv import load_dotenv


# Получаем абсолютный путь к текущей папке web
BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR.parent / ".env")

# Добавляем путь к manager для импорта
manager_path = BASE_DIR.parent / "manager"
sys.path.insert(0, str(manager_path))

# Импортируем модуль аутентификации
try:
    from auth import get_user, create_student, load_users
except ImportError:
    print("[warn] Модуль auth.py не найден. Создайте файл auth.py")
    # Заглушка для тестирования
    def get_user(username):
        users = {
            "admin": {"password": "admin123", "role": "admin"},
            "teacher": {"password": "teacher123", "role": "teacher"},
            "student001": {"password": "student123", "role": "student"},
            "student002": {"password": "student123", "role": "student"},
            "student003": {"password": "student123", "role": "student"},
        }
        return users.get(username)
    
    def create_student(username, password="student123"):
        return {"password": password, "role": "student"}
    
    def load_users():
        return {}

try:
    from docker_manager import DockerManager
    from config import config
except ImportError as e:
    print(f"Import error: {e}")
    print(f"Manager path: {manager_path}")
    print(f"Current dir: {os.getcwd()}")
    # Создаем заглушки для тестирования
    class DockerManager:
        def list_environments(self): return []
        def create_environment(self, student_id, course): 
            return {"web_url": "http://localhost:10000", "password": "test123", "student_id": student_id}
        def stop_environment(self, student_id): return True
        def remove_environment(self, student_id): return True
        def get_environment_info(self, student_id): 
            return {"status": "running", "host_port": "10000", "password": "test123"}

app = FastAPI(
    title="Dev Environment Manager",
    description="Веб-интерфейс управления средами разработки",
    version="1.0.0"
)
# Подключаем роутер заданий
app.include_router(assignments_router, prefix="/assignments", tags=["assignments"])
print("[ok] Роутер системы заданий подключен")
# Настройка путей к шаблонам и статическим файлам
templates_dir = BASE_DIR / "templates"
static_dir = BASE_DIR / "static"

print("[init] Конфигурация путей:")
print(f"   Base directory: {BASE_DIR}")
print(f"   Templates: {templates_dir}")
print(f"   Static files: {static_dir}")
print(f"   Templates exists: {templates_dir.exists()}")
print(f"   Static exists: {static_dir.exists()}")

# Создаем папки если их нет
templates_dir.mkdir(exist_ok=True)
static_dir.mkdir(exist_ok=True)

# Настраиваем шаблоны и статические файлы
templates = Jinja2Templates(directory=str(templates_dir))

# Монтируем статические файлы
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
else:
    print("[warn] Папка static не найдена!")

# Инициализация менеджера Docker
try:
    docker_manager = DockerManager()
    print("[ok] Docker менеджер инициализирован")
except Exception as e:
    print(f"[warn] Ошибка инициализации Docker менеджера: {e}")
    docker_manager = None

# Загружаем пользователей
users = load_users()
print(f"[ok] Загружено {len(users)} пользователей")

# Текущие сессии (в памяти)
sessions = {}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Главная страница"""
    return templates.TemplateResponse(request, "index.html", {})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа"""
    return templates.TemplateResponse(request, "login.html", {})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Аутентификация пользователя"""
    # Получаем пользователя из базы
    user = get_user(username)
    
    # Если пользователь не найден и имя начинается с "student", создаем нового
    if not user and username.startswith("student"):
        user = create_student(username)
    
    # Проверяем пароль
    if user and user["password"] == password:
        # Генерируем токен сессии
        import secrets
        token = secrets.token_hex(16)
        sessions[token] = {
            "username": username,
            "role": user["role"]
        }
        
        # Создаем ответ с куки
        response = RedirectResponse(url="/", status_code=302)
        
        # Редирект в зависимости от роли
        if user["role"] == "admin":
            response = RedirectResponse(url="/admin", status_code=302)
        elif user["role"] == "teacher":
            response = RedirectResponse(url="/teacher", status_code=302)
        else:
            response = RedirectResponse(url=f"/student/{username}", status_code=302)
        
        response.set_cookie(key="session_token", value=token, httponly=True)
        return response
    
    # Неверные учетные данные
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": "Неверные имя пользователя или пароль"},
    )

def check_auth(request: Request, allowed_roles=None):
    """Проверка авторизации пользователя"""
    if allowed_roles is None:
        allowed_roles = ["admin", "teacher", "student"]
    
    token = request.cookies.get("session_token")
    if not token or token not in sessions:
        return None
    
    user_role = sessions[token]["role"]
    if user_role not in allowed_roles:
        return None
    
    return sessions[token]

def list_assignment_branches(repo_url: str) -> list[str]:
    if not repo_url:
        return []
    try:
        r = subprocess.run(
            ["git", "ls-remote", "--heads", repo_url],
            capture_output=True,
            text=True,
            check=True,
        )
        branches = []
        for line in r.stdout.splitlines():
            parts = line.strip().split()
            if len(parts) != 2:
                continue
            ref = parts[1]
            if ref.startswith("refs/heads/"):
                branches.append(ref.removeprefix("refs/heads/"))
        branches = sorted(set(branches))
        return branches
    except Exception:
        return []

def _gitea_api_request(method: str, path: str, data: dict | None = None) -> tuple[int, dict | str]:
    base = os.getenv("GITEA_URL", "http://localhost:3000").rstrip("/")
    token = os.getenv("GITEA_ADMIN_TOKEN", "").strip()
    if not token:
        raise RuntimeError("GITEA_ADMIN_TOKEN не задан")
    url = f"{base}{path}"
    body = None
    headers = {"Authorization": f"token {token}"}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urlrequest.Request(url, data=body, headers=headers, method=method)
    try:
        with urlrequest.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8") if resp.length != 0 else ""
            return resp.status, json.loads(raw) if raw else {}
    except HTTPError as e:
        raw = e.read().decode("utf-8") if e.fp else ""
        payload = {}
        if raw:
            try:
                payload = json.loads(raw)
            except Exception:
                payload = {"raw": raw}
        return e.code, payload

def _inject_basic_auth(url: str, user: str | None, token: str | None) -> str:
    if not user or not token:
        return url
    if url.startswith("http://"):
        return url.replace("http://", f"http://{user}:{token}@", 1)
    if url.startswith("https://"):
        return url.replace("https://", f"https://{user}:{token}@", 1)
    return url

def _token_user(base_url: str, token: str) -> str | None:
    if not token:
        return None
    req = urlrequest.Request(
        f"{base_url.rstrip('/')}/api/v1/user",
        headers={"Authorization": f"token {token}"},
        method="GET",
    )
    try:
        with urlrequest.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            payload = json.loads(raw) if raw else {}
            login = (payload.get("login") or "").strip()
            return login or None
    except Exception:
        return None

def resolve_git_http_credentials() -> tuple[str, str]:
    gitea_url = os.getenv("GITEA_URL", "http://localhost:3000")
    prefer_admin = (os.getenv("GITEA_PREFER_ADMIN_TOKEN_FOR_GIT", "1") or "1").strip() == "1"
    http_token = (os.getenv("GITEA_HTTP_TOKEN", "") or "").strip()
    admin_token = (os.getenv("GITEA_ADMIN_TOKEN", "") or "").strip()

    if prefer_admin and admin_token:
        user = _token_user(gitea_url, admin_token) or (os.getenv("GITEA_ADMIN_USER", "") or "").strip()
        if user:
            return user, admin_token

    if http_token:
        user = _token_user(gitea_url, http_token) or (os.getenv("GITEA_HTTP_USER", "") or "").strip()
        if user:
            return user, http_token

    if admin_token:
        user = _token_user(gitea_url, admin_token) or (os.getenv("GITEA_ADMIN_USER", "") or "").strip()
        if user:
            return user, admin_token

    raise RuntimeError("Не удалось определить git-учетные данные из токенов Gitea")

def ensure_student_repo_and_seed(student_id: str, assignment_branch: str, template_repo_url: str) -> tuple[str, str]:
    gitea_url = os.getenv("GITEA_URL", "http://localhost:3000").rstrip("/")
    org = os.getenv("GITEA_ORG", "edu")
    repo_prefix = os.getenv("GITEA_STUDENT_REPO_PREFIX", "student-")
    repo_name = f"{repo_prefix}{student_id}"
    git_user, git_token = resolve_git_http_credentials()
    repo_http = f"{gitea_url}/{org}/{repo_name}.git"
    repo_push = _inject_basic_auth(repo_http, git_user, git_token)

    code, _ = _gitea_api_request("GET", f"/api/v1/repos/{org}/{repo_name}")
    if code == 404:
        create_code, create_payload = _gitea_api_request(
            "POST",
            f"/api/v1/orgs/{org}/repos",
            {"name": repo_name, "private": True, "auto_init": False},
        )
        if create_code not in (201, 409):
            raise RuntimeError(f"Ошибка создания репозитория студента: {create_payload}")
    elif code != 200:
        raise RuntimeError(f"Ошибка доступа к репозиторию студента: {code}")

    if not template_repo_url:
        return repo_http, repo_push

    seed_dir = tempfile.mkdtemp(prefix="seed-assignment-")
    try:
        subprocess.run(
            ["git", "clone", "--single-branch", "--branch", assignment_branch, template_repo_url, seed_dir],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(["git", "-C", seed_dir, "remote", "remove", "origin"], check=False, capture_output=True, text=True)
        subprocess.run(["git", "-C", seed_dir, "remote", "add", "origin", repo_push], check=True, capture_output=True, text=True)
        branch = f"students/{student_id}/{assignment_branch}"
        subprocess.run(["git", "-C", seed_dir, "checkout", "-B", branch], check=True, capture_output=True, text=True)
        push_res = subprocess.run(
            ["git", "-C", seed_dir, "push", "-u", "origin", branch],
            check=False,
            capture_output=True,
            text=True,
        )
        if push_res.returncode != 0:
            stderr = (push_res.stderr or "").lower()
            if "set up to track remote branch" not in stderr and "everything up-to-date" not in stderr and "already exists" not in stderr:
                raise RuntimeError(push_res.stderr or push_res.stdout or "Ошибка push в репозиторий студента")
    finally:
        shutil.rmtree(seed_dir, ignore_errors=True)

    return repo_http, repo_push

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Панель администратора"""
    user = check_auth(request, ["admin"])
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    # Получаем список всех сред
    environments = []
    if docker_manager:
        try:
            environments = docker_manager.list_environments()
        except Exception as e:
            print(f"Ошибка получения списка сред: {e}")
    
    # Получаем всех пользователей-студентов
    all_users = load_users()
    student_users = [u for u in all_users if all_users[u]["role"] == "student"]
    
    return templates.TemplateResponse(
        request,
        "admin.html",
        {
            "environments": environments,
            "username": user["username"],
            "role": user["role"],
            "student_users": student_users,
        },
    )

@app.get("/teacher", response_class=HTMLResponse)
async def teacher_dashboard(request: Request):
    """Панель преподавателя"""
    user = check_auth(request, ["admin", "teacher"])
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    # Получаем список всех сред
    environments = []
    if docker_manager:
        try:
            environments = docker_manager.list_environments()
        except Exception as e:
            print(f"Ошибка получения списка сред: {e}")
    
    # Получаем всех пользователей-студентов
    all_users = load_users()
    student_users = [u for u in all_users if all_users[u]["role"] == "student"]
    
    return templates.TemplateResponse(
        request,
        "teacher.html",
        {
            "environments": environments,
            "username": user["username"],
            "role": user["role"],
            "student_users": student_users,  # Важно передать список студентов!
        },
    )
@app.get("/student/{student_id}", response_class=HTMLResponse)
async def student_dashboard(request: Request, student_id: str):
    """Панель студента"""
    user = check_auth(request, ["admin", "teacher", "student"])
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    # Студент может видеть только свою среду
    if user["role"] == "student" and user["username"] != student_id:
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    
    # Получаем информацию о среде
    env_info = None
    if docker_manager:
        try:
            env_info = docker_manager.get_environment_info(student_id)
            print(f"DEBUG env_info для {student_id}: {env_info}")  # ДОБАВЬТЕ ЭТУ СТРОКУ
        except Exception as e:
            print(f"Ошибка получения информации о среде: {e}")
    
    # Инициализируем переменные
    env_status = "not_created"
    web_url = None
    password = None
    password_hint = "неизвестен"
    container_id = None
    
    if env_info:
        env_status = env_info.get("status", "unknown")
        host_port = env_info.get("host_port", "N/A")
        web_url = f"http://localhost:{host_port}" if host_port != "N/A" else None
        password = env_info.get("password", "")  # ВОТ ЗДЕСЬ БЕРЕМ ПАРОЛЬ
        
        print(f"DEBUG password для {student_id}: '{password}'")  # ДОБАВЬТЕ ЭТУ СТРОКУ
        
        if password and password != "неизвестен":
            password_hint = password
        else:
            password_hint = "неизвестен"
        
        container_id = env_info.get("container_id", "N/A")
    
    return templates.TemplateResponse(
        request,
        "student.html",
        {
            "student_id": student_id,
            "env_status": env_status,
            "web_url": web_url,
            "password": password,  # ПЕРЕДАЕМ ПАРОЛЬ В ШАБЛОН
            "password_hint": password_hint,
            "container_id": container_id,
            "username": user["username"],
            "role": user["role"],
            "assignments": list_assignment_branches(os.getenv("ASSIGNMENTS_TEMPLATE_REPO_URL", "")),
        },
    )

@app.get("/api/assignments")
async def assignments_api(request: Request):
    user = check_auth(request, ["admin", "teacher", "student"])
    if not user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    repo_url = os.getenv("ASSIGNMENTS_TEMPLATE_REPO_URL", "")
    return {"success": True, "data": {"repo_url": repo_url, "branches": list_assignment_branches(repo_url)}}

@app.post("/api/my/environment/create")
async def create_my_environment(
    request: Request,
    course: str = Form("python"),
    assignment_branch: str = Form("main"),
):
    user = check_auth(request, ["student"])
    if not user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    if not docker_manager:
        return {"success": False, "message": "Docker менеджер не инициализирован"}

    student_id = user["username"]
    git_repo_url = os.getenv("ASSIGNMENTS_TEMPLATE_REPO_URL", "")
    use_per_student_repo = os.getenv("USE_PER_STUDENT_REPO", "1").strip() == "1"
    git_push_url_template = os.getenv("ASSIGNMENTS_PUSH_URL_TEMPLATE")
    git_user = None
    git_token = None

    try:
        git_user, git_token = resolve_git_http_credentials()
        git_push_url = None
        effective_branch = assignment_branch
        if use_per_student_repo:
            student_repo_http, git_push_url = ensure_student_repo_and_seed(student_id, assignment_branch, git_repo_url)
            git_repo_url = _inject_basic_auth(student_repo_http, git_user, git_token)
            effective_branch = f"students/{student_id}/{assignment_branch}"
        elif git_push_url_template:
            git_push_url = git_push_url_template.format(student_id=student_id, branch=assignment_branch)
            git_push_url = _inject_basic_auth(git_push_url, git_user, git_token)
            git_repo_url = _inject_basic_auth(git_repo_url, git_user, git_token)
        result = docker_manager.create_environment(
            student_id,
            course,
            git_repo_url=git_repo_url,
            git_branch=effective_branch,
            git_push_url=git_push_url,
        )
        return {"success": True, "message": "Среда готова", "data": result}
    except Exception as e:
        return {"success": False, "message": f"Ошибка: {e}"}

@app.post("/api/my/check")
async def my_check(request: Request):
    user = check_auth(request, ["student"])
    if not user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    if not docker_manager:
        return {"success": False, "message": "Docker менеджер не инициализирован"}
    student_id = user["username"]
    try:
        r = docker_manager.exec_in_environment(
            student_id,
            'if [ -f "./check.sh" ]; then chmod +x ./check.sh; ./check.sh; elif command -v pytest >/dev/null 2>&1; then pytest -q; else python3 -m pip -q install pytest >/dev/null && pytest -q; fi',
        )
        return {"success": True, "data": r}
    except Exception as e:
        return {"success": False, "message": f"Ошибка: {e}"}

@app.post("/api/my/submit")
async def my_submit(request: Request):
    user = check_auth(request, ["student"])
    if not user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    if not docker_manager:
        return {"success": False, "message": "Docker менеджер не инициализирован"}
    student_id = user["username"]
    try:
        r = docker_manager.exec_in_environment(
            student_id,
            'git add -A && (git commit -m "submit" || true) && git push origin HEAD',
        )
        return {"success": True, "data": r}
    except Exception as e:
        return {"success": False, "message": f"Ошибка: {e}"}
@app.post("/api/environments/create")
async def create_environment_api(
    request: Request,
    student_id: str = Form(...),
    course: str = Form("python"),
    assignment_branch: str = Form("main"),
):
    """API для создания среды"""
    user = check_auth(request, ["admin", "teacher"])
    if not user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    
    if not docker_manager:
        return {
            "success": False,
            "message": "Docker менеджер не инициализирован"
        }
    
    try:
        git_repo_url = os.getenv("ASSIGNMENTS_TEMPLATE_REPO_URL", "")
        use_per_student_repo = os.getenv("USE_PER_STUDENT_REPO", "1").strip() == "1"
        git_push_url_template = os.getenv("ASSIGNMENTS_PUSH_URL_TEMPLATE")
        git_user, git_token = resolve_git_http_credentials()
        git_push_url = None
        effective_branch = assignment_branch
        if use_per_student_repo:
            student_repo_http, git_push_url = ensure_student_repo_and_seed(student_id, assignment_branch, git_repo_url)
            git_repo_url = _inject_basic_auth(student_repo_http, git_user, git_token)
            effective_branch = f"students/{student_id}/{assignment_branch}"
        elif git_push_url_template:
            git_push_url = git_push_url_template.format(student_id=student_id, branch=assignment_branch)
            git_push_url = _inject_basic_auth(git_push_url, git_user, git_token)
            git_repo_url = _inject_basic_auth(git_repo_url, git_user, git_token)

        result = docker_manager.create_environment(
            student_id,
            course,
            git_repo_url=git_repo_url,
            git_branch=effective_branch,
            git_push_url=git_push_url,
        )
        
        # Автоматически создаем пользователя если его нет
        if not get_user(student_id):
            create_student(student_id)
        
        return {
            "success": True,
            "message": "Среда успешно создана",
            "data": {
                "web_url": result.get("web_url", "N/A"),
                "student_id": result.get("student_id", student_id),
                "password": result.get("password", "неизвестен")
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Ошибка создания среды: {str(e)}"
        }

@app.post("/api/environments/{student_id}/stop")
async def stop_environment_api(request: Request, student_id: str):
    """API для остановки среды"""
    user = check_auth(request)
    if not user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    
    # Проверка прав
    if user["role"] not in ["admin", "teacher"]:
        # Студент может останавливать только свою среду
        if user["role"] == "student" and user["username"] != student_id:
            raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    if not docker_manager:
        return {
            "success": False,
            "message": "Docker менеджер не инициализирован"
        }
    
    success = docker_manager.stop_environment(student_id)
    return {
        "success": success,
        "message": "Среда остановлена" if success else "Не удалось остановить среду"
    }

@app.post("/api/environments/{student_id}/remove")
async def remove_environment_api(request: Request, student_id: str):
    """API для удаления среды"""
    user = check_auth(request, ["admin", "teacher"])
    if not user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    
    if not docker_manager:
        return {
            "success": False,
            "message": "Docker менеджер не инициализирован"
        }
    
    success = docker_manager.remove_environment(student_id)
    return {
        "success": success,
        "message": "Среда удалена" if success else "Не удалось удалить среду"
    }

@app.get("/api/environments")
async def list_environments_api(request: Request):
    """API для получения списка сред"""
    user = check_auth(request, ["admin", "teacher"])
    if not user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    
    environments = []
    if docker_manager:
        try:
            environments = docker_manager.list_environments()
        except Exception as e:
            print(f"Ошибка получения списка сред: {e}")
    
    return {
        "success": True,
        "data": environments
    }

@app.get("/api/environment/{student_id}")
async def get_environment_api(request: Request, student_id: str):
    """API для получения информации о среде"""
    user = check_auth(request)
    if not user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    
    # Студент может получать информацию только о своей среде
    if user["role"] == "student" and user["username"] != student_id:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    env_info = None
    if docker_manager:
        try:
            env_info = docker_manager.get_environment_info(student_id)
        except Exception as e:
            print(f"Ошибка получения информации о среде: {e}")
    
    if not env_info:
        return {
            "success": False,
            "message": "Среда не найдена"
        }
    
    return {
        "success": True,
        "data": env_info
    }

@app.get("/api/users/students")
async def get_students_api(request: Request):
    """API для получения списка студентов"""
    user = check_auth(request, ["admin", "teacher"])
    if not user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    
    all_users = load_users()
    student_users = [u for u in all_users if all_users[u]["role"] == "student"]
    
    return {
        "success": True,
        "data": student_users
    }

@app.get("/logout")
async def logout():
    """Выход из системы"""
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("session_token")
    return response

@app.get("/health")
async def health_check():
    """Проверка здоровья приложения"""
    return {
        "status": "healthy",
        "service": "dev-env-manager-web",
        "docker_available": docker_manager is not None
    }

if __name__ == "__main__":
    import uvicorn
    import os
    
    port = int(os.getenv("PORT", "8000"))

    print("\n" + "="*50)
    print("[start] Запуск Dev Environment Manager Web")
    print("="*50)
    print(f"Рабочая директория: {BASE_DIR}")
    print(f"Доступно по адресу: http://localhost:{port}")
    print("Тестовые пользователи:")
    print(f"   - admin / admin123 (администратор)")
    print(f"   - teacher / teacher123 (преподаватель)")
    print(f"   - studentXXX / student123 (любой студент)")
    print("="*50 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=port)