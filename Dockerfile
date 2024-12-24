FROM python:3.12-slim
LABEL APP Lab3

WORKDIR /opt/Mountain 

COPY . .

RUN pip install -r requirements.txt

CMD ["python3", "-m", "gunicorn", "-b", "0.0.0.0:3000", "-w", "4", "app:app"]