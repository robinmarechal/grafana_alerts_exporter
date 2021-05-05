FROM python:3.6-alpine3.7

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app
RUN pip3 install --no-cache-dir -r requirements.txt

COPY grafana_alerts_exporter.py /usr/src/app

EXPOSE 5555
ENV LISTEN_ADDRESS=:5555 DEBUG=0 CONFIG_FILE="/etc/grafana_alerts_exporter/grafana_alerts_exporter.yml"

ENTRYPOINT [ "python", "-u", "./grafana_alerts_exporter.py" ]