FROM mcr.microsoft.com/azure-functions/python:2.0

ENV ASPNETCORE_URLS=http://+:8080

COPY . /home/site/wwwroot

RUN cd /home/site/wwwroot && \
    pip install -r requirements.txt
