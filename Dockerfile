FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY requirements.txt pyproject.toml ./
COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic

RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir --upgrade pip setuptools \
    && python -m pip install --no-cache-dir .

RUN useradd --system --uid 10001 --create-home appuser
USER 10001:10001

EXPOSE 8000
CMD ["uvicorn", "inventory_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
