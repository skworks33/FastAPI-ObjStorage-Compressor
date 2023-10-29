FROM python:3.9-slim

WORKDIR /app

ARG ENV

COPY requirements.txt .
COPY requirements-dev.txt .

RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Install dev requirements only if ENV is development
RUN if [ "$ENV" = "development" ]; then pip install --no-cache-dir --upgrade -r requirements-dev.txt; fi

COPY ./app/ .

CMD ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8080"]
