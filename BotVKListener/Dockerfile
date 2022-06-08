FROM python:latest
RUN mkdir -p /app
WORKDIR /app
COPY ./BotVKListener/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt
COPY ./Models ./Models
RUN pip install -r Models/requirements.txt
ENV TZ Europe/Moscow
COPY ./BotVKListener/ ./BotVKListener/
COPY ./utils/ ./utils/
COPY ./config.py ./config.py
COPY ./.env ./.env
CMD ["python", "./BotVKListener/server.py"]