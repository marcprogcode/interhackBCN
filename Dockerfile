FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn pandas numpy tqdm openpyxl

# Copy source code and data
COPY src/ ./src/
COPY data/ ./data/

# The API expects to be run from src/ so data_loader uses relative path "data"
WORKDIR /app/src

EXPOSE 8000

CMD ["python", "api.py"]
