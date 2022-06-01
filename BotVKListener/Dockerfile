FROM python:3.10.0-buster

WORKDIR /ss-admin
ENV PYTHONPATH="/ss-admin/BotVKListener/:/ss-admin/"

COPY ./utils/requirements.txt ./
RUN pip install --no-cache-dir -r ./requirements.txt

COPY ./utils ./utils
COPY ./BotVKListener ./BotVKListener
COPY ./Models ./Models


CMD [ "python", "/ss-admin/Models/create_db.py", "python", "/ss-admin/BotVKListener/Parser/_initial_downloading.py" ]