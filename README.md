# Grafana Alerts Exporter

Prometheus exporter to expose alerts configures in Grafana to Prometheus.

That allows to take advantage of Grafana forms simplicity to create alerts, and to use them in Prometheus rules for more advanced alerts. 

# Roadmap
- [ ] Dashboard example ?

# Docker

Build image

```
docker build --tag grafana_alerts_exporter .
```

Run

```
docker run -d \
    --name grafana_alerts_exporter \
    -p 9823:9823 \
    -v "$PWD/grafana_alerts_exporter.yml:/usr/share/exporter/grafana_alerts_exporter.yml \
    grafana_alerts_exporter
```

# Command line

```
python3 grafana_alerts_exporter.py -h

  -h, --help            show this help message and exit
  --config.file CONFIG_FILE
                        Path to config file
  --web.listen-address LISTEN_ADDRESS
                        Listen to this address and port
  --debug               Enable debug
```

# Metrics

```
# HELP grafana_alerts_collector_collect_seconds Time spent to collect metrics from Grafana Alerts
# TYPE grafana_alerts_collector_collect_seconds summary
grafana_alerts_collector_collect_seconds_count
grafana_alerts_collector_collect_seconds_sum
# HELP grafana_alerts_collector_collect_seconds_created Time spent to collect metrics from Grafana Alerts
# TYPE grafana_alerts_collector_collect_seconds_created gauge
grafana_alerts_collector_collect_seconds_created
# HELP grafana_alerts_alert_state Alert state value. 0 = ok, 1 = pending, 2 = alerting
# TYPE grafana_alerts_alert_state gauge
grafana_alerts_alert_state
# HELP grafana_alerts_state_changes_total Total times this alert state has changed
# TYPE grafana_alerts_state_changes_total gauge
grafana_alerts_state_changes_total
# HELP grafana_alerts_new_state_date Date of last status update
# TYPE grafana_alerts_new_state_date gauge
grafana_alerts_new_state_date
# HELP grafana_alerts_execution_error 1 if the execution of the alert rule resulted in an error
# TYPE grafana_alerts_execution_error gauge
grafana_alerts_execution_error
# HELP grafana_alerts_alert_value Alert state value. 0 = ok, 1 = alerting, 2 = pending
# TYPE grafana_alerts_alert_value gauge
grafana_alerts_alert_value
# HELP grafana_alerts_silence Whether the alert is being silent (1) or no (0)
# TYPE grafana_alerts_silence gauge
grafana_alerts_silence
```