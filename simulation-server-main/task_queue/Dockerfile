FROM python:3.10-slim

COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt

COPY . /worker
WORKDIR /worker

CMD ["python", "example_worker.py"]