FROM python:latest
ENV TZ Europe/Moscow
RUN mkdir -p /app
WORKDIR /app
COPY ./config.py ./BotVKPoster/config.py
COPY ./config.py ./BotVKPoster/Models/config.py
ENV PYTHONPATH="/app/BotVKPoster/:/app/BotVKPoster/Models"
RUN pip install --upgrade pip
COPY ./BotVKPoster/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt
COPY ./Models ./BotVKPoster/Models
RUN pip install -r BotVKPoster/Models/requirements.txt
COPY ./BotVKPoster/ ./BotVKPoster/
COPY ./utils/ ./BotVKPoster/utils/
CMD ["python", "./BotVKPoster/server.py"]