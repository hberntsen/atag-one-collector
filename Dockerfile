FROM alpine:3.7

RUN apk update && \
    apk add python3 &&pip3 install influxdb

COPY collector.py /collector.py

USER nobody
ENTRYPOINT ["python3", "/collector.py"]
