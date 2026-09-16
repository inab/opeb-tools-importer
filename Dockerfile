# 3.11: the pinned pymongo 4.3.3 ships no prebuilt wheels for 3.12+
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt

# Run as an unprivileged user; it only needs write access to the inspection dir
RUN useradd --uid 1000 --create-home importer \
    && mkdir -p /app/inspection_openebench_import \
    && chown importer:importer /app/inspection_openebench_import

COPY main.py utils.py ./

USER importer

ENTRYPOINT ["python3", "main.py"]
CMD ["--loglevel", "DEBUG"]
