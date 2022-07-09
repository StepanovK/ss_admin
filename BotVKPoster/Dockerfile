FROM python:latest
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
ENV PYTHONPATH="/app/BotVKPoster/"
COPY ./Docker/config.py ./BotVKPoster/config.py
COPY ./BotVKPoster/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt
COPY ./Models ./BotVKPoster/Models
RUN pip install -r BotVKPoster/Models/requirements.txt
COPY ./BotVKPoster/ ./BotVKPoster/
COPY ./utils/ ./BotVKPoster/utils/
CMD ["python", "./BotVKPoster/server.py"]