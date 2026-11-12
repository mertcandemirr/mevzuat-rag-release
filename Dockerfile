FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.8.0 && pip install --no-cache-dir -r requirements.txt
RUN useradd -u 10001 --create-home rag && mkdir /cache /indexes && chown rag:rag /cache /indexes
COPY backend backend
COPY scripts scripts
USER rag
ENV HF_HOME=/cache PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false
CMD ["uvicorn","backend.api:app","--host","0.0.0.0","--port","8011"]
