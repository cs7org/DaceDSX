FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8

ENV RABBITMQ_HOST rabbitmq
ENV REDIS_HOST redis
ENV RESULTS_DIR /data/results
ENV RESOURCES_DIR /data/resources

COPY requirements.txt /tmp/

# install requirements
RUN python -m pip install --upgrade pip
RUN pip install -r /tmp/requirements.txt

COPY . /fastapi_app

# avoid running as root user
RUN useradd --create-home appuser
RUN chown -R appuser /fastapi_app
USER appuser
WORKDIR /fastapi_app

# expose the app port
EXPOSE 5001

# run the app server
CMD ["uvicorn", "webapp:app", "--host", "0.0.0.0", "--port", "5001", "--proxy-headers"]
