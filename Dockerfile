FROM python:3-alpine
LABEL Description="docker-cab image"
MAINTAINER Marc Brinkmann <git@marcbrinkmann.de>

COPY . /code
WORKDIR /code
RUN pip install .

ENTRYPOINT ["/usr/local/bin/docker-cab"]
