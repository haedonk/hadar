FROM python:3.12-slim

WORKDIR /app/ingestion-pipeline

COPY ingestion-pipeline/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY db/ /app/db/
COPY ingestion-pipeline/ .

CMD ["python", "processor.py"]
