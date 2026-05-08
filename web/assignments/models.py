# web/assignments/models.py
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
import json
from pathlib import Path

# Перечисления
class AssignmentStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    GRADED = "graded"
    LATE = "late"

class TestResult(Enum):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"

class Difficulty(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

# Модели данных
@dataclass
class Assignment:
    """Модель задания"""
    id: str  # например: "python-001"
    title: str
    description: str
    course: str = "python"  # python, web, data, etc
    difficulty: str = "beginner"
    max_score: int = 100
    due_date: Optional[str] = None  # ISO формат
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Файлы задания
    template_files: List[Dict] = field(default_factory=list)  # [{"name": "main.py", "content": "..."}]
    test_files: List[Dict] = field(default_factory=list)      # Тесты
    instructions: str = ""
    tags: List[str] = field(default_factory=list)  # ["functions", "loops", "strings"]
    
    def to_dict(self) -> Dict:
        """Конвертировать в словарь для JSON"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Assignment':
        """Создать из словаря"""
        return cls(**data)

@dataclass
class Submission:
    """Модель решения студента"""
    id: str  # student_id + assignment_id
    student_id: str
    assignment_id: str
    status: str = AssignmentStatus.NOT_STARTED.value
    submitted_at: Optional[str] = None
    score: int = 0
    max_score: int = 100
    files: List[Dict] = field(default_factory=list)  # Файлы решения
    test_results: Dict = field(default_factory=dict)  # Результаты тестов
    feedback: str = ""
    teacher_comment: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Submission':
        return cls(**data)

@dataclass
class TestResult:
    """Результат теста"""
    test_name: str
    status: str  # passed, failed, error
    message: str = ""
    execution_time: float = 0.0
    details: Dict = field(default_factory=dict)