# pull official base image
FROM python:3.10.4-buster
# set work directory
WORKDIR /usr/src/app
# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH $PYTHONPATH:/usr/src/app
# install dependencies
COPY ./requirements.txt /usr/src/app/requirements.txt
RUN python3 -m pip install -r requirements.txt --no-cache-dir
# copy project
COPY . /usr/src/app/
# start
CMD ["python3", "/usr/src/app/wallabot.py"]
