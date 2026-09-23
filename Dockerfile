FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV DB_PATH=/app/data/roomrental.db \
    SEED_DEMO=1
RUN mkdir -p /app/data /app/uploads
VOLUME /app/data /app/uploads
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
