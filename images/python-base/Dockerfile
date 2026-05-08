# Используем официальный образ Ubuntu LTS
FROM ubuntu:22.04

# Устанавливаем переменные окружения для избежания интерактивных диалогов
ENV DEBIAN_FRONTEND=noninteractive

# Обновляем систему и устанавливаем базовые утилиты
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    sudo \
    nano \
    htop \
    procps \
    net-tools \
    openssh-server \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Создаем пользователя 'student' (не-root)
RUN useradd -m -s /bin/bash student && \
    echo "student:student123" | chpasswd && \
    echo "student ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/student

# Устанавливаем Node.js (необходим для некоторых расширений VS Code)
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs

# Устанавливаем code-server (VS Code для web)
RUN curl -fsSL https://code-server.dev/install.sh | sh && command -v code-server

# Создаем рабочую директорию
RUN mkdir -p /home/student/workspace && \
    chown -R student:student /home/student

# Копируем настройки VS Code
COPY settings.json /home/student/.local/share/code-server/User/settings.json
RUN chown -R student:student /home/student/.local

# Копируем скрипт запуска
COPY start.sh /usr/local/bin/start.sh

# ВАЖНО: Устанавливаем права на исполнение для скрипта
# chmod уже внутри контейнера, а не на хосте
RUN chmod +x /usr/local/bin/start.sh

# Устанавливаем порты для работы
EXPOSE 8080 2222

# Переключаемся на пользователя student
USER student
WORKDIR /home/student/workspace

# Создаем тестовый файл приветствия
RUN echo "# Welcome to Dev Environment" > /home/student/workspace/README.md && \
    echo "Python version: \`python3 --version\`" >> /home/student/workspace/README.md

# Запускаем code-server при старте контейнера
CMD ["/usr/local/bin/start.sh"]