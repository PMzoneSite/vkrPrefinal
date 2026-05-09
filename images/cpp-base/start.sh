#!/bin/bash

export PASSWORD="${CODE_PASSWORD:-student123}"

# Ensure user-installed Python CLIs (pip --user) are available (pytest, pip, etc.)
export PATH="$HOME/.local/bin:$PATH"

if command -v sshd &> /dev/null; then
    sudo service ssh start
fi

if [ ! -f "/home/student/workspace/.project-setup" ]; then
    echo "This file indicates workspace is set up" > /home/student/workspace/.project-setup
fi

PROJECT_DIR="${PROJECT_DIR:-/home/student/workspace/project}"
normalize_git_url() {
    local u="$1"
    u="${u//localhost/host.docker.internal}"
    u="${u//127.0.0.1/host.docker.internal}"
    echo "$u"
}

if [ -n "${GIT_REPO_URL:-}" ]; then
    GIT_REPO_URL="$(normalize_git_url "$GIT_REPO_URL")"
    if [ -n "${GIT_PUSH_URL:-}" ]; then
        GIT_PUSH_URL="$(normalize_git_url "$GIT_PUSH_URL")"
    fi
    if [ ! -d "$PROJECT_DIR/.git" ]; then
        rm -rf "$PROJECT_DIR"
        mkdir -p "$PROJECT_DIR"
        if [ -n "${GIT_BRANCH:-}" ]; then
            git clone --single-branch --branch "$GIT_BRANCH" "$GIT_REPO_URL" "$PROJECT_DIR" || true
        else
            git clone "$GIT_REPO_URL" "$PROJECT_DIR" || true
        fi
    fi

    if [ -n "${GIT_PUSH_URL:-}" ] && [ -d "$PROJECT_DIR/.git" ]; then
        git -C "$PROJECT_DIR" remote remove origin 2>/dev/null || true
        git -C "$PROJECT_DIR" remote add origin "$GIT_PUSH_URL" || true
    fi

    if [ -n "${GIT_STUDENT_BRANCH:-}" ] && [ -d "$PROJECT_DIR/.git" ]; then
        base="${GIT_BRANCH:-main}"
        git -C "$PROJECT_DIR" fetch origin "$base" 2>/dev/null || true
        git -C "$PROJECT_DIR" checkout -B "$GIT_STUDENT_BRANCH" "origin/$base" 2>/dev/null || git -C "$PROJECT_DIR" checkout -B "$GIT_STUDENT_BRANCH" || true
    fi

    if [ -n "${GIT_USER_NAME:-}" ]; then
        git -C "$PROJECT_DIR" config user.name "$GIT_USER_NAME" || true
    fi
    if [ -n "${GIT_USER_EMAIL:-}" ]; then
        git -C "$PROJECT_DIR" config user.email "$GIT_USER_EMAIL" || true
    fi
fi

code-server \
    --auth password \
    --bind-addr 0.0.0.0:8080 \
    --disable-telemetry \
    /home/student/workspace
