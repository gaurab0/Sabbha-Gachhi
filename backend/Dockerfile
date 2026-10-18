# syntax=docker/dockerfile:1.7
FROM python:3.13.7-slim-bookworm AS builder
ENV VIRTUAL_ENV=/opt/venv PATH=/opt/venv/bin:$PATH PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential libjpeg62-turbo-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/* \
    && python -m venv "$VIRTUAL_ENV"
WORKDIR /build
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && pip install -r requirements.txt

FROM python:3.13.7-slim-bookworm AS runtime-base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv PATH=/opt/venv/bin:$PATH \
    DJANGO_SETTINGS_MODULE=core.settings
RUN apt-get update && apt-get install -y --no-install-recommends \
      libjpeg62-turbo zlib1g tini \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app . /app
RUN mkdir -p /app/media /app/staticfiles && chown -R app:app /app/media /app/staticfiles
USER 10001:10001
ENTRYPOINT ["sh", "/app/entrypoint.sh"]
EXPOSE 8000

FROM runtime-base AS dev
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

FROM runtime-base AS prod
ENV DJANGO_DEBUG=false
RUN DJANGO_SECRET_KEY=build-only-placeholder python manage.py collectstatic --noinput
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz/', timeout=2)" || exit 1
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]
