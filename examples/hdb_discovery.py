#!/usr/bin/env python
# ===========
# pysap - Python library for crafting SAP's network protocols packets
#
# SECUREAUTH LABS. Copyright (C) 2020 SecureAuth Corporation. All rights reserved.
#
# The library was designed and developed by Martin Gallo from
# the SecureAuth Labs team.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# ==============

# Standard imports
import logging
from argparse import ArgumentParser
from socket import error as SocketError
# External imports
from scapy.config import conf
# Custom imports
import pysap
from pysap.SAPHDB import (SAPHDBConnection, SAPHDBTLSConnection, SAPHDBConnectionError,
                          SAPHDBOptionPartRow, SAPHDBPart, SAPHDBSegment, SAPHDB)


# Set the verbosity to 0
conf.verb = 0


# Command line options parser
def parse_options():

    description = "This example script performs discovery of HANA database tenants."

    usage = "%(prog)s [options] -d <remote host>"

    parser = ArgumentParser(usage=usage, description=description, epilog=pysap.epilog)

    target = parser.add_argument_group("Target")
    target.add_argument("-d", "--remote-host", dest="remote_host",
                        help="Remote host")
    target.add_argument("-p", "--remote-port", dest="remote_port", type=int, default=39013,
                        help="Remote port [%(default)d]")
    target.add_argument("--route-string", dest="route_string",
                        help="Route string for connecting through a SAP Router")
    target.add_argument("--tls", dest="tls", action="store_true",
                        help="Use TLS/SSL")

    discovery = parser.add_mutually_exclusive_group()
    discovery.add_argument("-t", "--tenants", dest="tenants", default="SYSTEMDB",
                           help="List of comma separated tenants to try [%(default)s]")
    discovery.add_argument("--dictionary", dest="dictionary", metavar="FILE",
                           help="File to read the list of tenants to try")

    misc = parser.add_argument_group("Misc options")
    misc.add_argument("-v", "--verbose", dest="verbose", action="store_true", help="Verbose output")

    options = parser.parse_args()

    if not options.remote_host:
        parser.error("Remote host is required")

    return options


# Main function
def main():
    options = parse_options()

    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)

    # Initiate the connection
    connection_class = SAPHDBConnection
    if options.tls:
        connection_class = SAPHDBTLSConnection

    # Build the list of tenants to try
    if options.dictionary:
        with open(options.dictionary, 'r') as fd:
            tenants = [tenant.strip() for tenant in fd.read().split("\n") if not tenant.startswith("#")]
    else:
        tenants = options.tenants.split(",")

    # Create the connection
    hdb = connection_class(options.remote_host,
                           options.remote_port,
                           route=options.route_string)

    print(tenants)
    try:
        for tenant in tenants:
            print("[*] Discovering tenant '{}'".format(tenant))
            try:
                hdb.connect()
                print("[*] Connected to HANA database %s:%d" % (options.remote_host, options.remote_port))
                hdb.initialize()
                print("[*] HANA database version %d/protocol version %d" % (hdb.product_version,
                                                                            hdb.protocol_version))

                hdb_dbconnectinfo_options = [SAPHDBOptionPartRow(key=1, type=29, value=tenant)]
                hdb_dbconnectinfo_part = SAPHDBPart(partkind=67, argumentcount=1, buffer=hdb_dbconnectinfo_options)
                hdb_dbconnectinfo_request = SAPHDB(sessionid=0, segments=[SAPHDBSegment(messagetype=82,
                                                                                        parts=[hdb_dbconnectinfo_part])])
                hdb_dbconnectinfo_request.show()

                hdb_dbconnectinfo_response = hdb.sr(hdb_dbconnectinfo_request)
                hdb_dbconnectinfo_response.show()

                hdb.close()

                print("[*] Connection with HANA database server closed")

            except SocketError as e:
                print("[-] Connection error: %s" % e.message)
            except SAPHDBConnectionError as e:
                print("[-] Connection error: %s" % e.message)

    except KeyboardInterrupt:
        print("[-] Connection canceled")


if __name__ == "__main__":
    main()