FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir streamlit plotly httpx pandas

COPY frontend/ ./frontend/

EXPOSE 8501

ENTRYPOINT ["streamlit", "run", "frontend/dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
