FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

COPY . .

ENV PORT=3000
EXPOSE 3000

CMD ["python3", "scripts/run_atlas.py", "--host", "0.0.0.0", "--no-browser"]
