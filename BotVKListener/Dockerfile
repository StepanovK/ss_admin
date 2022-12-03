FROM python:3.9
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

COPY ./Models/requirements.txt ./BotVKListener/Models/requirements.txt
RUN pip install -r BotVKListener/Models/requirements.txt

COPY ./utils/ ./BotVKListener/utils/
COPY ./Models ./BotVKListener/Models
COPY ./BotVKListener/ ./BotVKListener/

CMD ["python", "./BotVKListener/bot_listener.py"]