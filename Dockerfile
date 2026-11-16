FROM python:3.12.16-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir pip==25.0.1 \
    && python -m pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 app

COPY src ./src

USER app

ENTRYPOINT ["python", "-m", "enron_analysis"]

FROM runtime AS test

USER root
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY pytest.ini .
COPY tests ./tests

USER app

ENTRYPOINT ["python", "-m", "pytest", "-q"]

FROM runtime AS production
