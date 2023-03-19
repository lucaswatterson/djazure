#!/usr/bin/env python3

"""
Description of what the script does.
"""

import os
import subprocess
import socket


def main():
    get_sql_server = subprocess.run(
        [
            "az",
            "resource",
            "list",
            "--resource-group",
            os.getenv("RESOURCE_GROUP_NAME"),
            "--resource-type",
            "'Microsoft.Sql/servers'",
            "--query",
            "[].name",
            "-o",
            "tsv",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    hostname = socket.gethostname()

    create_firewall_rule = subprocess.run(
        [
            "az",
            "sql",
            "server",
            "firewall-rule",
            "create",
            "-g",
            os.getenv("RESOURCE_GROUP_NAME"),
            "-s",
            get_sql_server,
            "-n",
            "github_access",
            "--start-ip-address",
            hostname,
            "--end-ip-address",
            hostname,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


if __name__ == "__main__":
    main()
