FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 ALGOXRAY_CUSTOM_CODE=0 ALGOXRAY_ALLOWED_HOSTS=localhost,127.0.0.1
WORKDIR /app
COPY requirements.lock.txt ./
COPY backend/ backend/
RUN pip install -c requirements.lock.txt -e ./backend && groupadd --gid 10001 app && useradd --uid 10001 --gid 10001 --no-create-home app
COPY fixtures/ fixtures/
COPY contracts/ contracts/
COPY web/ web/
COPY docs/poster.html docs/poster.html
COPY results/core-release/summary.json results/core-release/summary.json
RUN mkdir -p results/runs && chown -R app:app results && chmod -R a+rX /app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s CMD ["python","-c","import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=3)"]
CMD ["python","-m","uvicorn","algoxray.api:app","--host","0.0.0.0","--port","8000","--no-proxy-headers"]
