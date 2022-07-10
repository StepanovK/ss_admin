FROM python:latest
RUN apt-get update && apt-get install -y locales
RUN sed -i -e \
  's/# ru_RU.UTF-8 UTF-8/ru_RU.UTF-8 UTF-8/' /etc/locale.gen \
   && locale-gen
ENV LANG ru_RU.UTF-8
ENV LANGUAGE ru_RU:ru
ENV LC_LANG ru_RU.UTF-8
ENV LC_ALL ru_RU.UTF-8
ENV TZ Europe/Moscow
RUN pip install --upgrade pip

RUN mkdir -p /app
WORKDIR /app
COPY ./Docker/config.py ./BotVKListener/config.py
ENV PYTHONPATH="/app/BotVKListener/"

COPY ./BotVKListener/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt
COPY ./Models ./BotVKListener/Models
RUN pip install -r BotVKListener/Models/requirements.txt
COPY ./BotVKListener/ ./BotVKListener/
COPY ./utils/ ./BotVKListener/utils/
CMD ["python", "./BotVKListener/server.py"]