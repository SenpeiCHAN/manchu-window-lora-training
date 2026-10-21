FROM python:3.11-slim@sha256:0dd364ba7e10242f07755449e3a3d0e35f9efd987952737b90def6709ab0c5ce

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libicu76 libgssapi-krb5-2 && rm -rf /var/lib/apt/lists/*
COPY docker/fetch_powershell.py /tmp/fetch_powershell.py
RUN python /tmp/fetch_powershell.py && rm /tmp/fetch_powershell.py
COPY backend/api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY backend /app/backend
EXPOSE 8000
