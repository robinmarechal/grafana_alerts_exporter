FROM python:3.6-alpine3.7

RUN mkdir -p /usr/share/exporter
WORKDIR /usr/share/exporter

COPY requirements.txt /usr/share/exporter
RUN pip3 install --no-cache-dir -r requirements.txt

COPY grafana_alerts_exporter.py /usr/share/exporter

EXPOSE 5555
ENV LISTEN_ADDRESS=:5555 DEBUG=0 CONFIG_FILE="/usr/share/exporter/grafana_alerts_exporter.yml"

ENTRYPOINT [ "python", "-u", "./grafana_alerts_exporter.py" ]