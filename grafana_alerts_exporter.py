#!/usr/bin/python

import re
import time
import requests
import argparse
from pprint import pprint
import yaml

import os
from sys import exit
from prometheus_client import Summary, make_wsgi_app
from prometheus_client.core import GaugeMetricFamily, REGISTRY
from wsgiref.simple_server import make_server

DEBUG = int(os.environ.get('DEBUG', '0'))

COLLECTION_TIME = Summary('grafana_alerts_collector_collect_seconds',
                          'Time spent to collect metrics from Grafana Alerts')


class GrafanaCollector(object):
    # The build statuses we want to export about.
    statuses = ["lastBuild", "lastCompletedBuild", "lastFailedBuild",
                "lastStableBuild", "lastSuccessfulBuild", "lastUnstableBuild",
                "lastUnsuccessfulBuild"]

    def __init__(cfg, debug):
        self._cfg = cfg
        self._debug = debug
        
        apiCfg = config(cfg, "global.grafana.api")
        self._url = apiCfg["url"].rstrip("/")
        self._params = apiCfg["params"]
        self._headers = apiCfg["headers"]
        self._insecure = apiCfg["insecure"]

    def collect(self):
        start = time.time()

        # Request data from Grafana
        jobs = self._request_data()

        self._setup_empty_prometheus_metrics()

        for job in jobs:
            name = job['fullName']
            if DEBUG:
                print("Found Job: {}".format(name))
                pprint(job)
            self._get_metrics(name, job)

        for status in self.statuses:
            for metric in self._prometheus_metrics[status].values():
                yield metric

        duration = time.time() - start
        COLLECTION_TIME.observe(duration)

    def _request_data(self):
        # Request exactly the information we need from Grafana
        url = '{0}/alerts'.format(self._target)
        jobs = "[fullName,number,timestamp,duration,actions[queuingDurationMillis,totalDurationMillis," \
               "skipCount,failCount,totalCount,passCount]]"
        tree = 'jobs[fullName,url,{0}]'.format(
            ','.join([s + jobs for s in self.statuses]))
        params = {
            'tree': tree,
        }

        def parsejobs(myurl):
            # params = tree: jobs[name,lastBuild[number,timestamp,duration,actions[queuingDurationMillis...
            if self._user and self._password:
                response = requests.get(myurl, params=params, auth=(
                    self._user, self._password), verify=(not self._insecure))
            else:
                response = requests.get(
                    myurl, params=params, verify=(not self._insecure))
            if DEBUG:
                pprint(response.text)
            if response.status_code != requests.codes.ok:
                raise Exception("Call to url %s failed with status: %s" % (
                    myurl, response.status_code))
            result = response.json()
            if DEBUG:
                pprint(result)

            jobs = []
            for job in result['jobs']:
                if job['_class'] == 'com.cloudbees.hudson.plugins.folder.Folder' or \
                   job['_class'] == 'grafana.branch.OrganizationFolder' or \
                   job['_class'] == 'org.grafanaci.plugins.workflow.multibranch.WorkflowMultiBranchProject':
                    jobs += parsejobs(job['url'] + '/api/json')
                else:
                    jobs.append(job)
            return jobs

        return parsejobs(url)

    def _setup_empty_prometheus_metrics(self):
        # The metrics we want to export.
        self._prometheus_metrics = {}
        for status in self.statuses:
            snake_case = re.sub('([A-Z])', '_\\1', status).lower()
            self._prometheus_metrics[status] = {
                'number':
                    GaugeMetricFamily('grafana_job_{0}'.format(snake_case),
                                      'Grafana build number for {0}'.format(status), labels=["jobname"]),
                'duration':
                    GaugeMetricFamily('grafana_job_{0}_duration_seconds'.format(snake_case),
                                      'Grafana build duration in seconds for {0}'.format(status), labels=["jobname"]),
                'timestamp':
                    GaugeMetricFamily('grafana_job_{0}_timestamp_seconds'.format(snake_case),
                                      'Grafana build timestamp in unixtime for {0}'.format(status), labels=["jobname"]),
                'queuingDurationMillis':
                    GaugeMetricFamily('grafana_job_{0}_queuing_duration_seconds'.format(snake_case),
                                      'Grafana build queuing duration in seconds for {0}'.format(
                                          status),
                                      labels=["jobname"]),
                'totalDurationMillis':
                    GaugeMetricFamily('grafana_job_{0}_total_duration_seconds'.format(snake_case),
                                      'Grafana build total duration in seconds for {0}'.format(status), labels=["jobname"]),
                'skipCount':
                    GaugeMetricFamily('grafana_job_{0}_skip_count'.format(snake_case),
                                      'Grafana build skip counts for {0}'.format(status), labels=["jobname"]),
                'failCount':
                    GaugeMetricFamily('grafana_job_{0}_fail_count'.format(snake_case),
                                      'Grafana build fail counts for {0}'.format(status), labels=["jobname"]),
                'totalCount':
                    GaugeMetricFamily('grafana_job_{0}_total_count'.format(snake_case),
                                      'Grafana build total counts for {0}'.format(status), labels=["jobname"]),
                'passCount':
                    GaugeMetricFamily('grafana_job_{0}_pass_count'.format(snake_case),
                                      'Grafana build pass counts for {0}'.format(status), labels=["jobname"]),
            }

    def _get_metrics(self, name, job):
        for status in self.statuses:
            if status in job.keys():
                status_data = job[status] or {}
                self._add_data_to_prometheus_structure(
                    status, status_data, job, name)

    def _add_data_to_prometheus_structure(self, status, status_data, job, name):
        # If there's a null result, we want to pass.
        if status_data.get('duration', 0):
            self._prometheus_metrics[status]['duration'].add_metric(
                [name], status_data.get('duration') / 1000.0)
        if status_data.get('timestamp', 0):
            self._prometheus_metrics[status]['timestamp'].add_metric(
                [name], status_data.get('timestamp') / 1000.0)
        if status_data.get('number', 0):
            self._prometheus_metrics[status]['number'].add_metric(
                [name], status_data.get('number'))
        actions_metrics = status_data.get('actions', [{}])
        for metric in actions_metrics:
            if metric.get('queuingDurationMillis', False):
                self._prometheus_metrics[status]['queuingDurationMillis'].add_metric(
                    [name], metric.get('queuingDurationMillis') / 1000.0)
            if metric.get('totalDurationMillis', False):
                self._prometheus_metrics[status]['totalDurationMillis'].add_metric(
                    [name], metric.get('totalDurationMillis') / 1000.0)
            if metric.get('skipCount', False):
                self._prometheus_metrics[status]['skipCount'].add_metric(
                    [name], metric.get('skipCount'))
            if metric.get('failCount', False):
                self._prometheus_metrics[status]['failCount'].add_metric(
                    [name], metric.get('failCount'))
            if metric.get('totalCount', False):
                self._prometheus_metrics[status]['totalCount'].add_metric(
                    [name], metric.get('totalCount'))
                # Calculate passCount by subtracting fails and skips from totalCount
                passcount = metric.get(
                    'totalCount') - metric.get('failCount') - metric.get('skipCount')
                self._prometheus_metrics[status]['passCount'].add_metric(
                    [name], passcount)


def parse_args():
    parser = argparse.ArgumentParser(
        description='grafana exporter args grafana address and port'
    )

    parser.add_argument(
        '--config.file',
        metavar='config_file',
        required=True,
        help='Path to config file',
        default=os.environ.get('CONFIG_FILE')
    )
    parser.add_argument(
        '--web.listen-address',
        metavar='listen_address',
        required=False,
        type=int,
        help='Listen to this address and port',
        default=int(os.environ.get('LISTEN_ADDRESS', ':5555'))
    )
    parser.add_argument(
        '--debug',
        dest='debug',
        required=False,
        action='store_true',
        help='Allow connection to insecure Grafana API',
        default=False
    )
    return parser.parse_args()


def load_cfg(args):
    with open(args.config_file, 'r') as stream:
        try:
            return yaml.safe_load(stream)
        except:
            yaml.YAMLError as exc:
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

        print("Polling {}. Serving at {}:{}".format(
            grafana_address, address, port))

        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Interrupted")
        exit(0)


if __name__ == "__main__":
    main()
