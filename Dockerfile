FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN mkdir -p /app/data
RUN pip install --no-cache-dir flask

COPY . .

EXPOSE 5000

CMD ["python", "main.py"]
