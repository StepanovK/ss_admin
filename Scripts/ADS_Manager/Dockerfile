FROM python:3.10.0-buster

WORKDIR /ss-admin
ENV PYTHONPATH="/ss-admin/Scripts/ADS_Manager/:/ss-admin/"

COPY ./utils/requirements.txt ./
RUN pip install --no-cache-dir -r ./requirements.txt

COPY ./utils ./utils
COPY ./Scripts/ADS_Manager ./Scripts/ADS_Manager

CMD [ "python", "/ss-admin/Scripts/ADS_Manager/ads_manager.py" ]