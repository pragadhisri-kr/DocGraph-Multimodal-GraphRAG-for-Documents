FROM python:3.11-slim
ARG INSTALL_DOCLING=false
WORKDIR /srv
COPY requirements.txt requirements-docling.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
 && if [ "$INSTALL_DOCLING" = "true" ]; then pip install --no-cache-dir -r requirements-docling.txt; fi
COPY app ./app
ENV UPLOAD_DIR=/tmp/uploads
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
