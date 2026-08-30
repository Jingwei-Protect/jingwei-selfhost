FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=dev \
    ENABLE_ADV_PROTECT=0 \
    OPENBLAS_NUM_THREADS=1 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libjpeg62-turbo \
        libpng16-16 \
        libtiff6 \
        fonts-dejavu-core \
        fonts-wqy-microhei \
    && apt-get install -y chromium chromium-driver \
    && rm -rf /var/lib/apt/lists/*
ENV CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER=/usr/bin/chromedriver
WORKDIR /app
COPY requirements.txt ./
RUN sed -i 's/^opencv-python/opencv-python-headless/' requirements.txt \
    && pip install --upgrade pip \
    && pip install -r requirements.txt
COPY api ./api
COPY core ./core
COPY evaluation ./evaluation
COPY ui ./ui
COPY scripts/capture_holo_css.py ./scripts/capture_holo_css.py
COPY frontend/src/holo-card ./frontend/src/holo-card
COPY --from=frontend-build /app/frontend/dist ./frontend/dist
RUN mkdir -p /app/data
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

FROM runtime AS runtime-adv
COPY requirements-adv.txt ./
RUN pip install -r requirements-adv.txt
ENV ENABLE_ADV_PROTECT=1
