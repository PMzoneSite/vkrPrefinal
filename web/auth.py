import json
import os
from pathlib import Path

USERS_FILE = Path(__file__).parent / "users.json"

def load_users():
    """Загрузка пользователей из файла"""
    if USERS_FILE.exists():
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"[warn] Ошибка чтения файла {USERS_FILE}, создаю новый")
    
    # Базовые пользователи
    users = {
        "admin": {"password": "admin123", "role": "admin"},
        "teacher": {"password": "teacher123", "role": "teacher"},
    }
    
    # Автоматически создаем студентов
    for i in range(1, 101):
        username = f"student{i:03d}"
        users[username] = {"password": "student123", "role": "student"}
    
    save_users(users)
    return users

def save_users(users):
    """Сохранение пользователей в файл"""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

def get_user(username):
    """Получить пользователя"""
    users = load_users()
    return users.get(username)

def create_student(username, password="student123"):
    """Создать нового студента"""
    users = load_users()
    if username not in users:
        users[username] = {"password": password, "role": "student"}
        save_users(users)
        print(f"[ok] Создан новый студент: {username}")
    return users[username]

def create_user(username, password, role="student"):
    """Создать нового пользователя"""
    users = load_users()
    if username not in users:
        users[username] = {"password": password, "role": role}
        save_users(users)
        return True
    return False

def delete_user(username):
    """Удалить пользователя"""
    users = load_users()
    if username in users:
        del users[username]
        save_users(users)
        return True
    return False

def get_all_students():
    """Получить всех студентов"""
    users = load_users()
    return {name: data for name, data in users.items() if data["role"] == "student"}

# Инициализируем файл при импорте
if __name__ != "__main__":
    users = load_users()
    print(f"[ok] Модуль auth инициализирован. Пользователей: {len(users)}")