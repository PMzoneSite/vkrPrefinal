# web/assignments/api.py
from fastapi import APIRouter, HTTPException, Request, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from typing import List, Dict, Optional
import uuid
from datetime import datetime
from pathlib import Path
from fastapi.templating import Jinja2Templates

from .models import Assignment, Submission, AssignmentStatus
from .database import db

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

# === HTML страницы ===
@router.get("/", response_class=HTMLResponse)
async def assignments_list(request: Request):
    """Страница списка заданий"""
    # Получаем пользователя из сессии
    token = request.cookies.get("session_token")
    username = None
    role = None
    
    # Пробуем получить сессию из app.py
    try:
        # Импортируем sessions из app.py
        from app import sessions
        if token and token in sessions:
            username = sessions[token]["username"]
            role = sessions[token]["role"]
    except ImportError:
        # Если нет в app.py, пробуем другой способ
        pass
    
    # Альтернативно: получаем из request.state если передано
    if hasattr(request.state, 'user'):
        username = request.state.user.get('username')
        role = request.state.user.get('role')
    
    # Получаем все задания
    assignments = db.get_all_assignments()
    
    return templates.TemplateResponse(
        request,
        "assignments/list.html",
        {
            "assignments": assignments,
            "username": username or "Гость",
            "role": role or "guest",
            "total_count": len(assignments),
        },
    )
@router.get("/create", response_class=HTMLResponse)
async def create_assignment_page(request: Request):
    """Страница создания задания"""
    # ВРЕМЕННО: фиксированные данные
    username = "Преподаватель"
    role = "teacher"
    
    return templates.TemplateResponse(
        request,
        "assignments/create.html",
        {
            "username": username,
            "role": role,
        },
    )
@router.get("/{assignment_id}", response_class=HTMLResponse)
async def view_assignment(request: Request, assignment_id: str):
    """Страница просмотра задания"""
    # Получаем задание
    assignment = db.get_assignment(assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Задание не найдено")
    
    # Получаем пользователя
    token = request.cookies.get("session_token")
    username = None
    role = None
    
    try:
        from auth import sessions
        if token and token in sessions:
            username = sessions[token]["username"]
            role = sessions[token]["role"]
    except:
        pass
    
    # Проверяем, есть ли решение у студента
    submission = None
    if role == "student" and username:
        submission_id = f"{username}_{assignment_id}"
        submission = db.get_submission(submission_id)
    
    return templates.TemplateResponse(
        request,
        "assignments/view.html",  # Нужно создать этот файл
        {
            "assignment": assignment.to_dict(),
            "username": username,
            "role": role,
            "submission": submission.to_dict() if submission else None,
        },
    )
# === REST API ===
@router.get("/api/assignments")
async def get_assignments_api() -> Dict:
    """Получить все задания (API)"""
    assignments = db.get_all_assignments()
    return {
        "success": True,
        "data": [assig.to_dict() for assig in assignments]
    }

@router.get("/api/assignments/{assignment_id}")
async def get_assignment_api(assignment_id: str) -> Dict:
    """Получить конкретное задание (API)"""
    assignment = db.get_assignment(assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Задание не найдено")
    
    return {
        "success": True,
        "data": assignment.to_dict()
    }

@router.post("/api/assignments/create")
async def create_assignment_api(
    title: str = Form(...),
    description: str = Form(...),
    course: str = Form("python"),
    difficulty: str = Form("beginner"),
    max_score: int = Form(100),
    due_date: Optional[str] = Form(None)  # Добавим due_date
):
    """Создать новое задание (API)"""
    try:
        print(f"📝 Получены данные для создания задания:")
        print(f"   Title: {title}")
        print(f"   Description: {description}")
        print(f"   Course: {course}")
        print(f"   Difficulty: {difficulty}")
        print(f"   Max score: {max_score}")
        print(f"   Due date: {due_date}")
        
        # Генерируем ID
        import uuid
        assignment_id = f"{course}-{str(uuid.uuid4())[:8]}"
        print(f"   Generated ID: {assignment_id}")
        
        # Создаем задание
        from .models import Assignment
        assignment = Assignment(
            id=assignment_id,
            title=title,
            description=description,
            course=course,
            difficulty=difficulty,
            max_score=max_score,
            due_date=due_date  # Добавляем due_date
        )
        
        print(f"   Assignment object created")
        
        # Сохраняем
        from .database import db
        if db.save_assignment(assignment):
            print(f"✅ Задание сохранено в базу")
            return {
                "success": True,
                "message": "Задание создано",
                "data": assignment.to_dict()
            }
        else:
            print(f"❌ Ошибка сохранения в базу")
            return {
                "success": False,
                "message": "Ошибка сохранения задания в базу данных"
            }
            
    except Exception as e:
        import traceback
        print(f"🔥 Критическая ошибка в create_assignment_api:")
        print(traceback.format_exc())
        return {
            "success": False,
            "message": f"Внутренняя ошибка сервера: {str(e)}"
        }

@router.delete("/api/assignments/{assignment_id}")
async def delete_assignment_api(assignment_id: str):
    """Удалить задание"""
    if db.delete_assignment(assignment_id):
        return {
            "success": True,
            "message": "Задание удалено"
        }
    else:
        raise HTTPException(status_code=404, detail="Задание не найдено")

# === API для решений ===
@router.get("/api/submissions/{student_id}")
async def get_student_submissions_api(student_id: str):
    """Получить решения студента"""
    submissions = db.get_student_submissions(student_id)
    return {
        "success": True,
        "data": [sub.to_dict() for sub in submissions]
    }

@router.get("/api/submissions/assignment/{assignment_id}")
async def get_assignment_submissions_api(assignment_id: str):
    """Получить все решения для задания"""
    submissions = db.get_assignment_submissions(assignment_id)
    return {
        "success": True,
        "data": [sub.to_dict() for sub in submissions]
    }

@router.post("/api/submissions/submit")
async def submit_assignment_api(
    student_id: str = Form(...),
    assignment_id: str = Form(...),
    code: str = Form(...)
):
    """Сдать решение задания"""
    try:
        submission_id = f"{student_id}_{assignment_id}"
        
        submission = Submission(
            id=submission_id,
            student_id=student_id,
            assignment_id=assignment_id,
            status=AssignmentStatus.SUBMITTED.value,
            submitted_at=datetime.now().isoformat(),
            files=[{"name": "main.py", "content": code}]
        )
        
        if db.save_submission(submission):
            # TODO: Запустить автотесты
            return {
                "success": True,
                "message": "Решение отправлено",
                "data": submission.to_dict()
            }
        else:
            return {
                "success": False,
                "message": "Ошибка сохранения решения"
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Ошибка: {str(e)}"
        }