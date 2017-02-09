# Dockerfile for DPLA Service Hub 
FROM python:3.5.1
MAINTAINER Jeremy Nelson <jermnelson@gmail.com>

ENV HOME /opt/dpla-service-hub

COPY * $HOME/
RUN cd $HOME && \
    pip install -r requirements.txt
WORKDIR $HOME
CMD ["nohup", "gunicorn", "-b", "0.0.0.0:5000", "api:app"]
