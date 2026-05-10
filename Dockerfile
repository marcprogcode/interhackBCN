FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if needed (pandas needs some)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and data
COPY src/ ./src/
COPY data/ ./data/

# Create outputs directory (the engine will generate the CSV at runtime)
RUN mkdir -p /app/outputs

# The API expects to be run from src/ so data_loader uses relative path "data"
WORKDIR /app/src

EXPOSE 8000

CMD ["python", "api.py"]
