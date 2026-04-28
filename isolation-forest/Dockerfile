FROM python:3.12-slim

WORKDIR /app/isolation-forest

COPY isolation-forest/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY db/ /app/db/
COPY isolation-forest/ .

CMD ["python", "main.py"]
