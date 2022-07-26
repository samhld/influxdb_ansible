#!/usr/bin/env python3
import argparse
import requests


parser = argparse.ArgumentParser(description="Create a remote+replication.")
parser.add_argument(
    "--influxdb-host",
    dest="influxdb",
    type=str,
    required=True,
)
parser.add_argument(
    "--username",
    dest="username",
    type=str,
    required=True,
)
parser.add_argument(
    "--password",
    dest="password",
    type=str,
    required=True,
)
parser.add_argument(
    "--organization",
    dest="organization",
    type=str,
    required=True,
)
parser.add_argument(
    "--bucket",
    dest="bucket",
    type=str,
    required=True,
)
parser.add_argument(
    "--cloud-host",
    dest="cloud_host",
    type=str,
    required=True,
)
parser.add_argument(
    "--cloud-bucket",
    dest="cloud_bucket",
    type=str,
    required=True,
)
parser.add_argument(
    "--cloud-org",
    dest="cloud_org",
    type=str,
    required=True,
)
parser.add_argument(
    "--cloud-token",
    dest="cloud_token",
    type=str,
    required=True,
)
parser.add_argument(
    "--task-file",
    dest="task_file",
    type=str,
    required=True,
)


class AnsiblePlugin:
    def __init__(self, args):
        self.influxdb_host = "http://"+ args.influxdb + ":8086"
        self.cloud_host = args.cloud_host
        self.cloud_bucket = args.cloud_bucket
        self.cloud_org = args.cloud_org
        self.cloud_token = args.cloud_token

        self.bucket_id = ""
        self.org_id = ""
        self.token = ""

    def setup(self, args):
        res = requests.post(
            self.influxdb_host + "/api/v2/setup",
            json={
                "username": args.username,
                "password": args.password,
                "org": args.organization,
                "bucket": args.bucket,
            },
        )

        if res.status_code >= 400:
            print("Request failed: ", res.text)
            return

        js = res.json()
        self.bucket_id = js["bucket"]["id"]
        self.org_id = js["bucket"]["orgID"]
        self.token = js["auth"]["token"]

        return self.token

    def create_remote(self):
        res = requests.post(
            self.influxdb_host + "/api/v2/remotes",
            json={
                "orgID": self.org_id,
                "name": "cloud-backup",
                "remoteURL": self.cloud_host,
                "remoteAPIToken": self.cloud_token,
                "remoteOrgID": self.cloud_org,
            },
            headers={"Authorization": f"Token {self.token}"},
        )
        if res.status_code >= 400:
            print("Request failed: ", res.text)
            return

        return res.json()["id"]

    def create_replication(self, remoteID):
        res = requests.post(
            self.influxdb_host + "/api/v2/replications",
            json={
                "orgID": self.org_id,
                "name": "cloud-backup",
                "remoteID": remoteID,
                "localBucketID": self.bucket_id,
                "remoteBucketID": self.cloud_bucket,
            },
            headers={"Authorization": f"Token {self.token}"},
        )
        if res.status_code >= 400:
            print("Request failed: ", res.text)
            return

        return res.json()["id"]

    def create_task(self, task_file):
        with open(task_file, "r") as f:
            flux = f.readlines()

        flux = "".join(flux)
        res = requests.post(
            self.influxdb_host + "/api/v2/tasks",
            json={
                "flux": flux,
                "orgID": self.org_id,
                "status": "active",
            },
            headers={"Authorization": f"Token {self.token}"},
        )
        if res.status_code >= 400:
            print("Request failed: ", res.text)
            return


def main():
    args = parser.parse_args()

    ansible = AnsiblePlugin(args)
    token = ansible.setup(args)
    print(f"Operator token is: {token}. Make sure not to lose this token.")
    remoteID = ansible.create_remote()
    ansible.create_replication(remoteID)
    ansible.create_task(args.task_file)


if __name__ == "__main__":
    main()
