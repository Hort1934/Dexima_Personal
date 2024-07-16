FROM python:3.10-bullseye

WORKDIR /app


RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 85

CMD ["python", "manage.py", "runserver", "0.0.0.0:85"]