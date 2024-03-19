FROM python:3.10-slim
WORKDIR /app/src

COPY . /app
RUN pip install --upgrade pip
RUN pip install pipenv
RUN pipenv install --system --deploy
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]