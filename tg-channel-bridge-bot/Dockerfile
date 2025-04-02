FROM python:3.8.20-slim-bookworm

COPY . .
RUN apt-get update
RUN apt-get install libmagic1 -y
RUN pip3 install --no-cache-dir -r requirements.txt
RUN pip3 install python-telegram-bot --upgrade

#COPY . .

CMD [ "python3", "./tgbot.py" ]

