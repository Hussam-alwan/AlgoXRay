# Dedicated runtime. No application, fixture, model or key is copied inside.
FROM python:3.12-slim
ENV PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /tmp
USER 10001:10001
HEALTHCHECK NONE
ENTRYPOINT ["python"]
