FROM ubuntu:latest

RUN apt-get update -y
RUN apt-get install -y python-pip python-dev build-essential libmagickwand-dev

RUN mkdir app
WORKDIR /app
COPY . /app/
RUN pip install -r requirements.txt



RUN python database.py
CMD python main.py

EXPOSE 8888