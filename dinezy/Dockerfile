FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential pkg-config libcairo2-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# tampilan (templates & static) disimpan di repo frontend
ARG FRONTEND_REPO
ARG FRONTEND_BRANCH=main
ARG GITHUB_TOKEN
RUN FRONTEND_REPO="$FRONTEND_REPO" FRONTEND_BRANCH="$FRONTEND_BRANCH" GITHUB_TOKEN="$GITHUB_TOKEN" \
    python docker/ambil_tampilan.py /app/frontend

RUN mkdir -p data media var/cache && chmod +x start.sh

EXPOSE 8000
CMD ["bash", "start.sh"]
