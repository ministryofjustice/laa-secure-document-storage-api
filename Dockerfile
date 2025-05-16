FROM python:3.13-alpine
WORKDIR /app/src
RUN addgroup --gid 1000 --system appgroup
RUN adduser -u 1000 -S appuser -G 1000
COPY ./Pipfile* /app/
RUN pip install --upgrade pip
RUN pip install pipenv
ENV PYTHONPATH=/app:$PYTHONPATH
RUN pipenv install --system --deploy
COPY . /app
USER 1000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
