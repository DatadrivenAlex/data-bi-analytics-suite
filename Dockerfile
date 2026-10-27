FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY pyproject.toml README.md requirements.txt ./
COPY src ./src
COPY sql ./sql
COPY data ./data

RUN pip install --no-cache-dir ".[postgres]"

ENTRYPOINT ["bi-analytics"]
CMD ["run"]
