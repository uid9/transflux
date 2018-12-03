#!/usr/bin/python

import argparse
import requests
import re
import json
from datetime import datetime, timedelta

time_format = '%Y-%m-%dT%H:%M:%SZ'
epoch = datetime(1970, 1, 1)
yesterday = datetime.now() - timedelta(days=1)

parser = argparse.ArgumentParser()
parser.add_argument('--host', help='influxdb hostname / IP', default='localhost')
parser.add_argument('--port', help='influxdb port', default='8086')
parser.add_argument('--source-db', help='source database name', required=True)
parser.add_argument('--dest-db', help='destination database name (defaults to source database)')
parser.add_argument('--source-measurement', help='source measurement name', required=True)
parser.add_argument('--dest-measurement', help='destination measurement name (defaults to source measurement)')
parser.add_argument('--mappings-file', help='file containing mappings of tags in json format', required=True)
parser.add_argument('--start-time', help='start timestamp of measurement in influxdb format')
parser.add_argument('--time-span', help='time in minutes between start and end time (ignored if start time is specified, defaults to 5)', default=5)
parser.add_argument('--end-time', help='end timestamp of measurement in influxdb format (defaults to end of the previous minute)')

args = parser.parse_args()

# Set defaults
read_url = 'http://' + args.host + ':' + args.port + '/query'
write_url = 'http://' + args.host + ':' + args.port + '/write'
source_db = args.source_db
if not args.dest_db:
    dest_db = args.source_db
else:
    dest_db = args.dest_db
source_measurement = args.source_measurement
if not args.dest_measurement:
    dest_measurement = args.source_measurement
else:
    dest_measurement = args.dest_measurement

if not args.start_time:
    if not args.time_span:
        time_span = 5
    else:
        time_span = int(args.time_span)
    start_time = datetime.strftime((datetime.now() - timedelta(minutes=time_span)).replace(second=0), time_format)
else:
    start_time = args.start_time

if not args.end_time:
    end_time = datetime.strftime((datetime.now() - timedelta(minutes=1)).replace(second=59), time_format)
else:
    end_time = args.end_time

with open(args.mappings_file, 'r') as f:
    mappings = json.load(f)

# For loop for every tag that needs to be modified
l = len(mappings)
for (n, mapping) in enumerate(mappings):
    print(n+1, "of", l, ":", mapping[1]['domain'])

    # First fetch data points by running a query using the source tags
    source = mapping[0]
    tag_query = ""
    for k,v in source.items():
        tag_query = tag_query + k + " = '" + v + "' and "
    influx_query = "select * from " + source_measurement + " where " + tag_query + "time >= '" + start_time + "' and time <= '" + end_time + "'"
    params = {'db': source_db, 'q': influx_query}
    r = requests.get(read_url, params=params)
    data = json.loads(r.text)

    # Skip to next tag(s) if there's no data
    if not 'series' in data['results'][0]:
        continue

    # Add destination tag(s) to the data
    dest = mapping[1]
    for k,v in dest.items():
        data['results'][0]['series'][0]['columns'].insert(-1, k)
        for value in data['results'][0]['series'][0]['values']:
            value.insert(-1, v)

    # Write the modified data to a file
    keys = data['results'][0]['series'][0]['columns'][1:-1]
    with open('/tmp/data.txt', 'w') as f:
        for values in data['results'][0]['series'][0]['values']:
            ts = str(int((datetime.strptime(values[0], time_format) - epoch).total_seconds())).ljust(19, '0')
            value = values[-1]
            tags = dict(zip(keys, values[1:-1]))
            line = dest_measurement
            for k,v in tags.items():
                line = line + ',' + k + '=' + v
            line = line + ' value=' + str(value) + ' ' + ts + '\n'
            f.write(line)

    # Read the file in chunks of 5000 points and write it to influxdb
    with open('/tmp/data.txt', 'r') as f:
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        params = {'db': dest_db}
        lines = []
        for line in f:
            lines.append(line)
            if len(lines) == 5000:
                payload = '\n'.join(lines)
                r = requests.post(write_url, params=params, data=payload, headers=headers)
                lines = []
        else:
            if len(lines) > 0:
                payload = '\n'.join(lines)
                r = requests.post(write_url, params=params, data=payload, headers=headers)
