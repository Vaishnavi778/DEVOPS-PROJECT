FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY requirements.txt pyproject.toml ./
COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic

RUN apk upgrade --no-cache \
    && python -m pip install --no-cache-dir --upgrade pip \
    && find /usr -type d -name 'setuptools-*.dist-info' -prune -exec rm -rf '{}' + \
    && python -m pip install --no-cache-dir --upgrade "setuptools>=78.1.1" \
    && python -m pip install --no-cache-dir .

RUN adduser -D -u 10001 appuser
USER 10001:10001

EXPOSE 8000
CMD ["uvicorn", "inventory_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
