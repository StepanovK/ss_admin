FROM python:latest
ENV TZ Europe/Moscow
RUN mkdir -p /app
WORKDIR /app
COPY ./Docker/config.py ./BotVKListener/config.py
ENV PYTHONPATH="/app/BotVKListener/"
RUN pip install --upgrade pip
COPY ./BotVKListener/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt
COPY ./Models ./BotVKListener/Models
RUN pip install -r BotVKListener/Models/requirements.txt
COPY ./BotVKListener/ ./BotVKListener/
COPY ./utils/ ./BotVKListener/utils/
CMD ["python", "./BotVKListener/server.py"]