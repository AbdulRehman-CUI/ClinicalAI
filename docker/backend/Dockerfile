# Backend service image for the FastAPI application.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend ./backend
#COPY alembic.ini ./alembic.ini
COPY backend/alembic.ini ./backend/alembic.ini

EXPOSE 8000

#CMD ["sh", "-c", "python -m alembic -c /app/alembic.ini upgrade head && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"]
CMD ["sh", "-c", "python -m alembic -c /app/backend/alembic.ini upgrade head && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"]
