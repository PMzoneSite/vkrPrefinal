# web/assignments/database.py
import json
from pathlib import Path
from typing import List, Dict, Optional
from .models import Assignment, Submission

class AssignmentDatabase:
    """Управление базой данных заданий"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(exist_ok=True)
        
        self.assignments_file = data_dir / "assignments.json"
        self.submissions_file = data_dir / "submissions.json"
        self.results_file = data_dir / "results.json"
        
        # Инициализация файлов
        self._init_files()
    
    def _init_files(self):
        """Инициализировать JSON файлы если их нет"""
        for file in [self.assignments_file, self.submissions_file, self.results_file]:
            if not file.exists():
                print(f"[init] Создаю файл: {file.name}")
                with open(file, 'w', encoding='utf-8', newline='') as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
            else:
                # Проверяем кодировку и валидность
                self._ensure_file_valid_utf8(file)
    # === Методы для заданий ===
    def save_assignment(self, assignment: Assignment) -> bool:
        """Сохранить задание"""
        try:
            print(f"💾 Сохранение задания {assignment.id} в базу...")
            
            # Проверяем кодировку файла
            self._ensure_file_valid_utf8(self.assignments_file)
            
            # Читаем с указанием кодировки
            with open(self.assignments_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"   Текущие задания: {list(data.keys())}")
            
            data[assignment.id] = assignment.to_dict()
            
            # Записываем с правильной кодировкой
            with open(self.assignments_file, 'w', encoding='utf-8', newline='') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"[ok] Задание сохранено. Всего: {len(data)}")
            return True
        except Exception as e:
            import traceback
            print(f"❌ Ошибка сохранения задания:")
            print(traceback.format_exc())
            
            # Пробуем создать файл заново
            try:
                with open(self.assignments_file, 'w', encoding='utf-8', newline='') as f:
                    json.dump({assignment.id: assignment.to_dict()}, f, ensure_ascii=False, indent=2)
                print(f"[fix] Файл создан заново с одним заданием")
                return True
            except:
                return False

    def _ensure_file_valid_utf8(self, file_path):
        """Убедиться что файл в кодировке UTF-8"""
        if not file_path.exists():
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
            return
        
        # Пробуем прочитать в разных кодировках
        encodings = ['utf-8', 'utf-8-sig', 'utf-16', 'utf-16-le', 'utf-16-be', 'cp1251']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read().strip()
                    if not content:
                        raise json.JSONDecodeError("Empty file", "", 0)
                    json.loads(content)
                print(f"[ok] Файл {file_path.name} в кодировке {encoding}")
                
                # Если не UTF-8, конвертируем
                if encoding != 'utf-8':
                    print("[fix] Конвертирую в UTF-8...")
                    with open(file_path, 'r', encoding=encoding) as f:
                        data = json.load(f)
                    with open(file_path, 'w', encoding='utf-8', newline='') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                return
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
        
        # Если ни одна кодировка не подошла, создаем заново
        print(f"[warn] Не удалось определить кодировку {file_path.name}, создаю заново...")
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
    
    def get_assignment(self, assignment_id: str) -> Optional[Assignment]:
        """Получить задание по ID"""
        try:
            with open(self.assignments_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if assignment_id in data:
                return Assignment.from_dict(data[assignment_id])
            return None
        except:
            return None
    
    def get_all_assignments(self) -> List[Assignment]:
        """Получить все задания"""
        try:
            with open(self.assignments_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return [Assignment.from_dict(assig) for assig in data.values()]
        except:
            return []
    
    def delete_assignment(self, assignment_id: str) -> bool:
        """Удалить задание"""
        try:
            with open(self.assignments_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if assignment_id in data:
                del data[assignment_id]
                
                with open(self.assignments_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                return True
            return False
        except:
            return False
    
    # === Методы для решений ===
    def save_submission(self, submission: Submission) -> bool:
        """Сохранить решение студента"""
        try:
            with open(self.submissions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            data[submission.id] = submission.to_dict()
            
            with open(self.submissions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving submission: {e}")
            return False
    
    def get_submission(self, submission_id: str) -> Optional[Submission]:
        """Получить решение по ID"""
        try:
            with open(self.submissions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if submission_id in data:
                return Submission.from_dict(data[submission_id])
            return None
        except:
            return None
    
    def get_student_submissions(self, student_id: str) -> List[Submission]:
        """Получить все решения студента"""
        try:
            with open(self.submissions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            submissions = []
            for sub_data in data.values():
                if sub_data['student_id'] == student_id:
                    submissions.append(Submission.from_dict(sub_data))
            
            return submissions
        except:
            return []
    
    def get_assignment_submissions(self, assignment_id: str) -> List[Submission]:
        """Получить все решения для задания"""
        try:
            with open(self.submissions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            submissions = []
            for sub_data in data.values():
                if sub_data['assignment_id'] == assignment_id:
                    submissions.append(Submission.from_dict(sub_data))
            
            return submissions
        except:
            return []

# Глобальный экземпляр базы данных
from pathlib import Path
db = AssignmentDatabase(Path(__file__).parent / "data")