# Dockerfile for DPLA Service Hub 
FROM python:3.5.1
MAINTAINER Jeremy Nelson <jermnelson@gmail.com>

ENV HOME /opt/dpla-service-hub
ENV REPO https://github.com/KnowledgeLinks/dpla-service-hub.git

RUN apt-get update && apt-get install -y git && \
    git clone $REPO $HOME && \
    cd $HOME && \
    git checkout plains2peaks && \
    git pull origin plains2peaks && \
    pip install -r requirements.txt && \
    mkdir instance
COPY instance/config.py $HOME/instance/config.py
WORKDIR $HOME
CMD ["nohup", "gunicorn", "-b", "0.0.0.0:5000", "api:app"]
