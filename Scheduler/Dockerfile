FROM python:3.9
RUN apt-get update && apt-get install -y locales
RUN sed -i -e \
  's/# ru_RU.UTF-8 UTF-8/ru_RU.UTF-8 UTF-8/' /etc/locale.gen \
   && locale-gen \
ENV LANG ru_RU.UTF-8
ENV LANGUAGE ru_RU:ru
ENV LC_LANG ru_RU.UTF-8
ENV LC_ALL ru_RU.UTF-8
ENV TZ Europe/Moscow

RUN pip install --upgrade pip

RUN mkdir -p /app
WORKDIR /app
COPY ./base_config.py ./Scheduler/base_config.py
COPY ./Docker/config.py ./Scheduler/config.py
ENV PYTHONPATH="/app/Scheduler/"

COPY ./Scheduler/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY ./Models/requirements.txt ./Scheduler/Models/requirements.txt
RUN pip install -r Scheduler/Models/requirements.txt

COPY ./utils/ ./Scheduler/utils/
RUN pip install -r Scheduler/utils/requirements.txt

COPY ./Models ./Scheduler/Models
COPY ./Scheduler/ ./Scheduler/

CMD ["python", "./Scheduler/main.py"]