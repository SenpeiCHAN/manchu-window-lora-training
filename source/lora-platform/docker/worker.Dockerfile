FROM pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
ARG SD_SCRIPTS_REF=690ea7f96c23182352ec63def76d431c6120bd2f
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git libglib2.0-0 libsm6 libxext6 libxrender1 && rm -rf /var/lib/apt/lists/*
COPY backend/worker/requirements.txt /tmp/requirements.txt
RUN git clone --depth 1 https://github.com/kohya-ss/sd-scripts.git /opt/sd-scripts \
    && git -C /opt/sd-scripts fetch --depth 1 origin ${SD_SCRIPTS_REF} \
    && git -C /opt/sd-scripts checkout ${SD_SCRIPTS_REF} \
    && cd /opt/sd-scripts \
    && pip install -r requirements.txt \
    && cd /app \
    && pip install -r /tmp/requirements.txt
COPY backend /app/backend
COPY scripts /app/scripts
CMD ["python", "-m", "backend.worker.main"]
