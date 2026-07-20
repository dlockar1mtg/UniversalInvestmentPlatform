FROM python:3.14-slim
WORKDIR /app
COPY requirements /app/requirements
RUN pip install --no-cache-dir -r /app/requirements/phase_7_3.txt
COPY . /app
ENV PYTHONUNBUFFERED=1 UIIP_DATABASE_BACKEND=postgresql UIIP_JOB_DATABASE_BACKEND=postgresql UIIP_HTTP_HOST=0.0.0.0
EXPOSE 8000
CMD ["python", "scripts/run_production_api.py"]
