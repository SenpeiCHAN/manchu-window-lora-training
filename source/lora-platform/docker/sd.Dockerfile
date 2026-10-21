FROM lora-platform-worker:latest

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
ARG COMFYUI_REF=f1072eb0350638a3390ddb6afbcaa8c6b237c6fd
WORKDIR /opt/ComfyUI
COPY docker/fetch_repo.py /tmp/fetch_repo.py

RUN REPO=comfyanonymous/ComfyUI COMMIT=${COMFYUI_REF} TARGET=/opt/ComfyUI python /tmp/fetch_repo.py \
    && pip install -r requirements.txt

CMD ["python", "main.py", "--listen", "0.0.0.0", "--port", "8188"]
