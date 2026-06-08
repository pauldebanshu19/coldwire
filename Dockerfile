# Root Dockerfile — lets Railway / any platform that builds from the REPO ROOT
# deploy the backend without needing a "Root Directory" setting.
# (backend/Dockerfile still works for `docker build backend/` and docker-compose.)

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

COPY backend/ ./

EXPOSE 8000

# default = API; the worker service overrides this with the celery command.
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
