FROM python:3.12-slim

WORKDIR /app/scoring-pipeline

COPY scoring-pipeline/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY db/ /app/db/
COPY scoring-pipeline/ .

CMD ["python", "main.py"]
