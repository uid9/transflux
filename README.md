# Transflux

A script to modify tag values or add new tags in influxdb. Compatible with both python 2.7 and 3.x. No dependencies apart from the python standard library.

Influxdb's inherent architecture does not allow modifications to tags. This script queries the database for a set of points, modifies tag values or adds new tags and then inserts the modified points into the specified database and measurement. Required parameters are the source database, source measurement and a mapping file which specifies the changes to be made. The destination database and measurement can be the same as the source. The original points in the source database are retained.

A fixed time range can be specified for the query using the start-time and end-time parameters. Or a time span N can be specified using the time-span (default=5) parameter which will query the database over N minutes upto end-time (end-time defaults to the last minute). This is useful if the script needs to be run regularly as a cron job.

The mapping file contains a list of changes i.e. which tag values to modify and what tags to add, in json format as such:

* One file per measurement having an array of arrays
* Each inner array is for a single mapping and must have two hashes, first for the list of tags to use in the WHERE clause for the SELECT query and second for the modifications plus any new tags to be added
* Outer array is for multiple mappings

E.g. usage

Mapping file:

```
[
[ { "host": "example.com", "instance": "bond0" }, { "host": "example.net", "bonded": "true" } ],
[ { "host": "example.com", "instance": "bond1" }, { "host": "example.net", "bonded": "true" } ],
]
```

Command:

```
/usr/local/bin/transflux.py --source-db collectd --dest-db collectd_new --source-measurement interface_tx
--mappings-file /tmp/mappings.txt --time-span 8
```

The above command will:

* Query the measurement interface_tx in the collectd database for points of the past 8 minutes where "host" = "example.com" and "instance" = ("bond0" or "bond1")
* Change values of the tag "host" to "example.net" and add a new tag "bonded" with value "true" (all other tags will be kept unmodified)
* Insert the modified points into a different database collectd_new using the same measurement name
