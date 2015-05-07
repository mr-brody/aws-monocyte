# Monocyte - Search and Destroy unwanted AWS Resources relentlessly.
# Copyright 2015 Immobilien Scout GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from boto import rds2
from monocyte.handler import Resource, Handler

SKIPPING_CREATION_STATEMENT = "Currently in creation. Skipping."
SKIPPING_AUTOGENERATED_STATEMENT = "Not a manually created Snapshot. Skipping."
SKIPPING_DELETION_STATEMENT = "Deletion already in progress. Skipping."
DELETION_STATEMENT = "Initiating deletion sequence for %s."

CREATION_STATUS = "creating"
AUTOMATED_STATUS = "automated"
DELETION_STATUS = "deleting"


class Instance(Handler):

    def fetch_regions(self):
        return rds2.regions()

    def fetch_unwanted_resources(self):
        for region in self.regions:
            connection = rds2.connect_to_region(region.name)
            resources = connection.describe_db_instances() or []
            for resource in resources["DescribeDBInstancesResponse"]["DescribeDBInstancesResult"]["DBInstances"]:
                resource_wrapper = Resource(resource, region.name)
                if resource['DBInstanceIdentifier'] in self.ignored_resources:
                    self.logger.info('IGNORE ' + self.to_string(resource_wrapper))
                    continue
                yield resource_wrapper

    def to_string(self, resource):
        return "Database Instance found in {region}, ".format(**vars(resource)) + \
               "with name {DBInstanceIdentifier}, with status {DBInstanceStatus}".format(**resource.wrapped)

    def delete(self, resource):
        if self.dry_run:
            return
        if resource.wrapped["DBInstanceStatus"] == DELETION_STATUS:
            self.logger.info(SKIPPING_DELETION_STATEMENT)
            return
        self.logger.info(DELETION_STATEMENT % resource.wrapped["DBInstanceIdentifier"])
        connection = rds2.connect_to_region(resource.region)
        response = connection.delete_db_instance(resource.wrapped["DBInstanceIdentifier"], skip_final_snapshot=True)
        return response["DeleteDBInstanceResponse"]["DeleteDBInstanceResult"]["DBInstance"]


class Snapshot(Handler):

    def fetch_regions(self):
        return rds2.regions()

    def fetch_unwanted_resources(self):
        for region in self.regions:
            connection = rds2.connect_to_region(region.name)
            resources = connection.describe_db_snapshots() or []
            for resource in resources["DescribeDBSnapshotsResponse"]["DescribeDBSnapshotsResult"]["DBSnapshots"]:
                resource_wrapper = Resource(resource, region.name)
                if resource['DBSnapshotIdentifier'] in self.ignored_resources:
                    self.logger.info('IGNORE ' + self.to_string(resource_wrapper))
                    continue
                yield resource_wrapper

    def to_string(self, resource):
        return "Database Snapshot found in {region}, ".format(**vars(resource)) + \
               "with name {DBSnapshotIdentifier}, with status {Status}".format(**resource.wrapped)

    def delete(self, resource):
        if self.dry_run:
            return
        if resource.wrapped["Status"] == DELETION_STATUS:
            self.logger.info(SKIPPING_DELETION_STATEMENT)
            return
        if resource.wrapped["Status"] == CREATION_STATUS:
            self.logger.info(SKIPPING_CREATION_STATEMENT)
            return
        if resource.wrapped["SnapshotType"] == AUTOMATED_STATUS:
            self.logger.info(SKIPPING_AUTOGENERATED_STATEMENT)
            return
        self.logger.info(DELETION_STATEMENT % resource.wrapped["DBSnapshotIdentifier"])
        connection = rds2.connect_to_region(resource.region)
        response = connection.delete_db_snapshot(resource.wrapped["DBSnapshotIdentifier"])
        return response["DeleteDBSnapshotResponse"]["DeleteDBSnapshotResult"]["DBSnapshot"]
