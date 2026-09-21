FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/home/mnemosyne

RUN groupadd --system mnemosyne && \
    useradd --system --gid mnemosyne --create-home --home-dir /home/mnemosyne mnemosyne

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app /app/app
COPY src /app/src
COPY ui /app/ui
COPY scripts /app/scripts
COPY README.md /app/README.md
COPY IMPLEMENTATION_SPECIFICATION.md /app/IMPLEMENTATION_SPECIFICATION.md
COPY PROJECT_DATA_SCIENCE_DATA_ENGINEERING_POSITIONING.md /app/PROJECT_DATA_SCIENCE_DATA_ENGINEERING_POSITIONING.md
COPY PROJECT_ROADMAP.md /app/PROJECT_ROADMAP.md

RUN mkdir -p /app/data /app/app/db /app/audit /app/models /home/mnemosyne/.hermes/profiles && \
    chown -R mnemosyne:mnemosyne /app/data /app/app/db /app/audit /app/models /home/mnemosyne

USER mnemosyne

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).read()"

CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
