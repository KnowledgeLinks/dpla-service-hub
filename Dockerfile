# Dockerfile for DPLA Service Hub 
FROM python:3.5.1
MAINTAINER Jeremy Nelson <jermnelson@gmail.com>

ENV HOME /opt/dpla-service-hub

ADD . $HOME
RUN ./

