#!/usr/bin/env python3

import argparse
import os
import re
import sys
import time
from pprint import pprint
from wsgiref.simple_server import make_server
import datetime


import requests
import yaml
from prometheus_client import REGISTRY, Gauge, Summary, Enum, make_wsgi_app
from prometheus_client.core import GaugeMetricFamily

DEBUG = int(os.environ.get("DEBUG", "0"))

COMMON_LABELS = ["alert_id", "alert_name", "dashboard_url"]

STATE_OK = "ok"
STATE_PENDING = "pending"
STATE_ALERTING = "alerting"

STATES = {STATE_ALERTING: 2, STATE_PENDING: 1, STATE_OK: 0}

COLLECTION_TIME = Summary(
    "grafana_alerts_collector_collect_seconds",
    "Time spent to collect metrics from Grafana Alerts",
)

METRICS = {
    "alert_state": {
        "name": "grafana_alerts_alert_state",
        "documentation": "Alert state value. 0 = ok, 1 = pending, 2 = alerting",
        "labelnames": COMMON_LABELS,
    },
    "new_state_date": {
        "name": "grafana_alerts_new_state_date",
        "documentation": "Date of last status update",
        "labelnames": COMMON_LABELS,
    },
    "execution_error": {
        "name": "grafana_alerts_execution_error",
        "documentation": "1 if the execution of the alert rule resulted in an error",
        "labelnames": COMMON_LABELS + ["error"],
    },
    "alert_value": {
        "name": "grafana_alerts_alert_value",
        "documentation": "Alert state value. 0 = ok, 1 = alerting, 2 = pending",
        "labelnames": COMMON_LABELS + ["metric"],
    },
    "state_changes_total": {
        "name": "grafana_alerts_state_changes_total",
        "documentation": "Total times this alert state has changed",
        "labelnames": COMMON_LABELS,
    },
    "silenced": {
        "name": "grafana_alerts_silence",
        "documentation": "Whether the alert is being silent (1) or no (0)",
        "labelnames": COMMON_LABELS,
    },
}


class AlertDetail(object):
    def __init__(self, basics, json):
        self.id = json["Id"]
        self.name = json["Name"]
        self.state = json["State"]
        self.silenced = json["Silenced"]
        self.new_state_date = json["NewStateDate"]
        self.state_changes = json["StateChanges"]
        self.error = json["ExecutionError"].strip()
        self.data = json["EvalData"]

        self.url = basics["url"]

        self.is_error = self.error != ""
        self.numeric_state = STATES[self.state]


class AlertMatch(object):
    def __init__(self, json):
        self.metric = json["metric"]
        self.tags = json["tags"]
        self.value = json["value"]


class GrafanaCollector(object):
    def __init__(self, cfg, debug):
        self._cfg = cfg
        self._debug = debug

        apiCfg = config(cfg, "global.grafana.api")
        self._url = apiCfg["url"].rstrip("/")
        self._params = apiCfg["params"]
        self._headers = apiCfg["headers"]
        self._insecure = apiCfg["insecure"]

        self._headers["content-type"] = "application/json"

    @COLLECTION_TIME.time()
    def collect(self):
        # Request data from Grafana
        alerts = self._fetch_all_alerts()
        return self._handle_alerts(alerts)

    def _get_data(self, response):
        if DEBUG:
            pprint(response.text)

        if response.status_code != 200:
            raise Exception(
                "Call to url %s failed with status: %s"
                % (response.url, response.status_code)
            )

        result = response.json()

        if DEBUG:
            pprint(result)

        return result

    def _fetch(self, url):
        response = requests.get(
            url, headers=self._headers, params=self._params, verify=(not self._insecure)
        )

        return self._get_data(response)

    def _fetch_all_alerts(self):
        url = "{0}/alerts".format(self._url)
        return self._fetch(url)

    def _fetch_alert_details(self, alert_id):
        url = "{0}/alerts/{1}".format(self._url, alert_id)
        return self._fetch(url)

    def _parse_date(self, datestr):
        return datetime.datetime.strptime(datestr, "%Y-%m-%dT%H:%M:%SZ")

    def _init_gauge(self, metric, add_labels=[]):
        template = METRICS[metric]
        return GaugeMetricFamily(
            name=template["name"],
            documentation=template["documentation"],
            labels=template["labelnames"] + add_labels,
        )

    def _handle_alerts(self, all_alerts):
        m_state = self._init_gauge("alert_state")
        m_state = self._init_gauge("alert_state")
        m_changes = self._init_gauge("state_changes_total")
        m_date = self._init_gauge("new_state_date")
        m_error = self._init_gauge("execution_error")
        m_value = self._init_gauge("alert_value")
        m_silenced = self._init_gauge("silenced")

        for basics in all_alerts:
            details_json = self._fetch_alert_details(basics["id"])
            alert = AlertDetail(basics, details_json)

            labels = [str(alert.id), alert.name, alert.url]

            m_state.add_metric(labels, alert.numeric_state)
            m_changes.add_metric(labels, alert.state_changes)
            m_silenced.add_metric(labels, int(alert.silenced))

            date = self._parse_date(alert.new_state_date)
            m_date.add_metric(labels, date.timestamp())

            if alert.is_error:
                m_error.add_metric(labels + [alert.error], 1)
            else:
                m_error.add_metric(labels + [""], 0)

            # alert value
            if alert.data != None and "evalMatches" in alert.data:
                for json in alert.data["evalMatches"]:
                    m = AlertMatch(json)
                    sample_labels = labels + [m.metric]

                    m_value.add_metric(sample_labels, m.value)

        yield m_state
        yield m_changes
        yield m_date
        yield m_error
        yield m_value
        yield m_silenced


def parse_args():
    parser = argparse.ArgumentParser(description="Grafana Alerts Exporter")

    parser.add_argument(
        "--config.file",
        dest="config_file",
        required=False,
        help="Path to config file",
        default=os.environ.get("CONFIG_FILE", "grafana_alerts_exporter.yml"),
    )
    parser.add_argument(
        "--web.listen-address",
        dest="listen_address",
        required=False,
        help="Listen to this address and port",
        default=os.environ.get("LISTEN_ADDRESS", ":9823"),
    )
    parser.add_argument(
        "--debug",
        dest="debug",
        required=False,
        action="store_true",
        help="Enable debug",
        default=os.environ.get("DEBUG", 0) == 1,
    )
    return parser.parse_args()


def load_cfg(args):
    with open(args.config_file, "r") as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)


def config(cfg, path):
    subcfg = cfg
    for part in path.split("."):
        subcfg = subcfg[part]

    return subcfg


def extract_port_and_address(args):
    address, port = args.listen_address.split(":")
    address = address if address != "" else "0.0.0.0"

    return address, port


def main():
    try:
        args = parse_args()

        # Parse cfg
        cfg = load_cfg(args)
        grafana_address = config(cfg, "global.grafana.api.url")

        collector = GrafanaCollector(cfg, args.debug)
        REGISTRY.register(collector)

        address, port = extract_port_and_address(args)

        app = make_wsgi_app()
        httpd = make_server(address, int(port), app)

        print("Polling {}. Serving at {}:{}".format(grafana_address, address, port))

        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Interrupted")
        sys.exit(0)


if __name__ == "__main__":
    main()
