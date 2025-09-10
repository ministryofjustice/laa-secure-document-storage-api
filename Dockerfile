FROM python:3.13-alpine
WORKDIR /app/src
RUN addgroup --gid 1000 --system appgroup && adduser -u 1000 -S appuser -G appgroup
COPY ./Pipfile* /app/
RUN pip install --upgrade pip
RUN pip install pipenv
ENV PYTHONPATH=/app:$PYTHONPATH
RUN pipenv install --system --deploy
COPY . /app
USER 1000:1000
# The two lines below is dependency for installing Locust
USER root
RUN apk add python3-dev musl-dev build-base linux-headers
# Stop being root now, was only needed for above
USER appuser
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
