FROM python:3.14-slim
WORKDIR /app
COPY requirements/phase_7_1.txt /app/requirements/phase_7_1.txt
RUN pip install --no-cache-dir -r /app/requirements/phase_7_1.txt
COPY . /app
ENV PYTHONUNBUFFERED=1 UIIP_DATABASE_BACKEND=postgresql UIIP_HTTP_HOST=0.0.0.0
EXPOSE 8000
CMD ["python", "scripts/run_production_api.py"]
