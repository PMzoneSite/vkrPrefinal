// Общие функции для веб-интерфейса

function createEnvironment(studentId = null) {
    const studentIdInput = studentId || document.getElementById('studentId').value;
    const course = document.getElementById('course')?.value || 'python';
    const assignmentBranch = document.getElementById('assignmentBranch')?.value || 'main';
    
    if (!studentIdInput) {
        alert('Введите ID студента');
        return;
    }
    
    const formData = new FormData();
    formData.append('student_id', studentIdInput);
    formData.append('course', course);
    formData.append('assignment_branch', assignmentBranch);
    
    fetch('/api/environments/create', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(`Среда создана!\nURL: ${data.data.web_url}\nПароль: ${data.data.password}`);
            refreshList();
        } else {
            alert(`Ошибка: ${data.message}`);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Произошла ошибка при создании среды');
    });
}

function stopEnvironment(studentId) {
    if (!confirm(`Остановить среду студента ${studentId}?`)) return;
    
    fetch(`/api/environments/${studentId}/stop`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message);
        refreshList();
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Произошла ошибка');
    });
}

function removeEnvironment(studentId) {
    if (!confirm(`Удалить среду студента ${studentId}? Все данные будут потеряны!`)) return;
    
    fetch(`/api/environments/${studentId}/remove`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message);
        refreshList();
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Произошла ошибка');
    });
}

function refreshList() {
    fetch('/api/environments')
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Для простоты перезагружаем страницу
            location.reload();
        }
    });
}

function cleanupEnvironments() {
    if (!confirm('Удалить все остановленные среды старше 24 часов?')) return;
    
    // В реальном проекте добавьте отдельный endpoint для cleanup
    alert('Функция очистки будет реализована в следующей версии');
}

// Обработка формы создания
const createForm = document.getElementById('createForm');
if (createForm) {
    createForm.addEventListener('submit', function(e) {
        e.preventDefault();
        createEnvironment();
    });
}