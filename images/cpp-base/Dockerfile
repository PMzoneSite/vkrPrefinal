FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl \
    git \
    sudo \
    openssh-server \
    build-essential \
    gdb \
    cmake \
    ninja-build \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash student && \
    echo "student:student123" | chpasswd && \
    echo "student ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/student

RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs

RUN curl -fsSL https://code-server.dev/install.sh | sh && command -v code-server

RUN mkdir -p /home/student/workspace && chown -R student:student /home/student

COPY settings.json /home/student/.local/share/code-server/User/settings.json
RUN chown -R student:student /home/student/.local

COPY start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

EXPOSE 8080 2222

USER student
WORKDIR /home/student/workspace

CMD ["/usr/local/bin/start.sh"]
