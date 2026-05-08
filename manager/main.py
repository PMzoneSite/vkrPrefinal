import argparse
import sys
from tabulate import tabulate

# Правильные импорты для структуры с __init__.py
try:
    from .docker_manager import DockerManager
    from .config import config
except ImportError:
    # Альтернатива если запускаем напрямую
    from docker_manager import DockerManager
    from config import config

def print_banner():
    """Вывод приветственного баннера"""
    banner = """
====================================================
  Менеджер сред разработки для студентов (Docker)
====================================================
"""
    print(banner)

def build_image(args):
    """Сборка Docker образа"""
    manager = DockerManager()
    try:
        tag = manager.build_image(tag=args.tag, force=args.force)
        print(f"\n[ok] Готово! Образ: {tag}")
        print(f"  Используйте: python main.py create student123")
    except Exception as e:
        print(f"\n[error] Ошибка: {e}")
        return 1
    return 0

def create_environment(args):
    """Создание новой среды"""
    manager = DockerManager()
    try:
        result = manager.create_environment(
            student_id=args.student_id,
            course=args.course,
            git_repo_url=args.git_repo_url,
            git_branch=args.git_branch,
            git_push_url=args.git_push_url,
        )
        
        print("\n" + "="*50)
        print("[ok] СРЕДА УСПЕШНО СОЗДАНА")
        print("="*50)
        print(f"Студент:       {result['student_id']}")
        print(f"Контейнер:     {result['container_name']}")
        print(f"Статус:        {result['status']}")
        print(f"Веб-доступ:    {result['web_url']}")
        print(f"Пароль:        {result['password']}")
        print(f"ID контейнера: {result['container_id']}")
        print("="*50)
        print("\nИнструкция для студента:")
        print(f"1. Откройте браузер: {result['web_url']}")
        print(f"2. Введите пароль: {result['password']}")
        print(f"3. Начните работу!")
        
    except Exception as e:
        print(f"\n[error] Ошибка создания среды: {e}")
        return 1
    return 0

def stop_environment(args):
    """Остановка среды"""
    manager = DockerManager()
    success = manager.stop_environment(args.student_id)
    return 0 if success else 1

def remove_environment(args):
    """Полное удаление среды"""
    manager = DockerManager()
    success = manager.remove_environment(args.student_id)
    return 0 if success else 1

def list_environments(args):
    """Список всех сред"""
    manager = DockerManager()
    environments = manager.list_environments()
    
    if not environments:
        print("Нет активных сред разработки")
        return 0
    
    # Преобразуем данные для таблицы
    table_data = []
    for env in environments:
        table_data.append([
            env['student_id'],
            env['container_id'],
            env['status'],
            env['host_port'],
            env['created'],
            env['image']
        ])
    
    headers = ["Студент", "Container ID", "Статус", "Порт", "Создан", "Образ"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Статистика
    running = sum(1 for e in environments if e['status'] == 'running')
    stopped = sum(1 for e in environments if e['status'] == 'exited')
    print(f"\nСтатистика: запущено {running}, остановлено {stopped}, всего {len(environments)}")
    
    return 0

def info_environment(args):
    """Информация о конкретной среде"""
    manager = DockerManager()
    info = manager.get_environment_info(args.student_id)
    
    if not info:
        print(f"Среда для студента {args.student_id} не найдена")
        return 1
    
    print(f"\nИнформация о среде студента {args.student_id}:")
    print("-" * 40)
    for key, value in info.items():
        if key == 'volumes':
            print(f"{key}:")
            for vol in value:
                print(f"  - {vol['Source']} -> {vol['Destination']}")
        else:
            print(f"{key}: {value}")
    
    return 0

def cleanup_environments(args):
    """Очистка старых сред"""
    manager = DockerManager()
    count = manager.cleanup_old_environments(args.hours)
    print(f"\nУдалено контейнеров: {count}")
    return 0

def main():
    """Основная функция"""
    print_banner()
    
    parser = argparse.ArgumentParser(
        description="Менеджер изолированных сред разработки для студентов",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python main.py build                    # Собрать Docker образ
  python main.py create student001        # Создать среду для студента
  python main.py list                     # Показать все среды
  python main.py info student001         # Информация о среде
  python main.py stop student001         # Остановить среду
  python main.py remove student001       # Удалить среду полностью
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Команды")
    
    # Команда build
    build_parser = subparsers.add_parser("build", help="Сборка Docker образа")
    build_parser.add_argument("--tag", help="Тег образа")
    build_parser.add_argument("--force", action="store_true", help="Пересобрать образ")
    build_parser.set_defaults(func=build_image)
    
    # Команда create
    create_parser = subparsers.add_parser("create", help="Создание новой среды")
    create_parser.add_argument("student_id", help="ID студента")
    create_parser.add_argument("--course", default="python", help="Курс (python, web, etc)")
    create_parser.add_argument("--git-repo-url", dest="git_repo_url", help="URL репозитория-шаблона")
    create_parser.add_argument("--git-branch", dest="git_branch", help="Ветка/branch задания")
    create_parser.add_argument("--git-push-url", dest="git_push_url", help="URL для push (ветка/неймспейс студента)")
    create_parser.set_defaults(func=create_environment)
    
    # Команда stop
    stop_parser = subparsers.add_parser("stop", help="Остановка среды")
    stop_parser.add_argument("student_id", help="ID студента")
    stop_parser.set_defaults(func=stop_environment)
    
    # Команда remove
    remove_parser = subparsers.add_parser("remove", help="Полное удаление среды")
    remove_parser.add_argument("student_id", help="ID студента")
    remove_parser.set_defaults(func=remove_environment)
    
    # Команда list
    list_parser = subparsers.add_parser("list", help="Список всех сред")
    list_parser.set_defaults(func=list_environments)
    
    # Команда info
    info_parser = subparsers.add_parser("info", help="Информация о среде")
    info_parser.add_argument("student_id", help="ID студента")
    info_parser.set_defaults(func=info_environment)
    
    # Команда cleanup
    cleanup_parser = subparsers.add_parser("cleanup", help="Очистка старых сред")
    cleanup_parser.add_argument("--hours", type=int, default=24, help="Возраст в часах")
    cleanup_parser.set_defaults(func=cleanup_environments)
    
    # Парсим аргументы
    if len(sys.argv) == 1:
        parser.print_help()
        return 0
    
    args = parser.parse_args()
    
    try:
        return args.func(args)
    except AttributeError:
        parser.print_help()
        return 0
    except Exception as e:
        print(f"Ошибка: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())