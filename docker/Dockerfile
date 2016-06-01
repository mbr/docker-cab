FROM python:3-alpine
LABEL Description="docker-cab image"
MAINTAINER Marc Brinkmann <git@marcbrinkmann.de>

RUN pip install https://github.com/mbr/docker-cab/zipball/master

ENTRYPOINT ["/usr/local/bin/docker-cab"]
