FROM python:3.13-alpine
WORKDIR /app/src
RUN addgroup --gid 1000 --system appgroup && adduser -u 1000 -S appuser -G appgroup
COPY ./Pipfile* /app/
RUN pip install --upgrade pip
RUN pip install pipenv
ENV PYTHONPATH=/app:$PYTHONPATH
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev && \
    pipenv install --system --deploy && \
    apk del .build-deps
COPY . /app
USER 1000:1000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
