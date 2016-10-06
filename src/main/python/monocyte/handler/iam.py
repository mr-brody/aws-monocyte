from __future__ import print_function, absolute_import, division


from monocyte.handler import Resource, Handler
import boto3
from boto import iam

class User(Handler):

    def fetch_regions(self):
        return iam.regions()

    def get_users(self):
        iam = boto3.client('iam')
        user_response = iam.list_users()
        return user_response['Users']

    def fetch_unwanted_resources(self):
        for user in self.get_users():
            if self.is_user_in_whitelist(user) or self.is_user_in_ignored_resources(user):
                self.logger.info('IGNORE user with {0}'.format(user['Arn']))
                continue

            unwanted_resource = Resource(resource=user,
                                         resource_type=self.resource_type,
                                         resource_id=user['Arn'],
                                         creation_date=user['CreateDate'],
                                         region='global')
            yield unwanted_resource

    def is_user_in_whitelist(self, user):
        whitelist_arns = self.get_whitelist().get('Arns', [])
        for arn_with_reason in whitelist_arns:
            if user['Arn'] == arn_with_reason['Arn']:
                return True

        return False

    def is_user_in_ignored_resources(self, user):
        return user['Arn'] in self.ignored_resources

    def to_string(self, resource):
        return "iam user found {0}".format(resource.resource_id)

    def delete(self, resource):
        if self.dry_run:
            return
        raise NotImplementedError("Should have implemented this")


class Policy(Handler):
    def fetch_regions(self):
        return iam.regions()

    def show_action(self, policy_document):
        return policy_document['Statement'][0]['Action']

    def check_action(self, policy_document):
        for action in self.show_action(policy_document):
            if action == "*:*":
                return True
        return False

    def is_policy_in_whitelist(self, policy):
        whitelist_arns = self.get_whitelist().get('Arns', [])
        for arn_with_reason in whitelist_arns:
            if policy['Arn'](policy) == arn_with_reason['Arn']:
                return True
        return False
        return "unallowed policy action found {0}".format(resource.resource_id)

    def delete(self, resource):
        if self.dry_run:
            return
        raise NotImplementedError("Should have implemented this")


class IamPolicy(Policy):

    def get_policies(self):
        client = boto3.client('iam')
        return client.list_policies(Scope='Local')['Policies']

    def get_policy_document(self, arn, version):
        resource = boto3.resource('iam')
        return resource.PolicyVersion(arn, version).document

    def fetch_unwanted_resources(self):
        for policy in self.get_policies():
            if self.is_policy_in_whitelist(policy):
                continue
            if self.check_action(self.get_policy_document(policy['Arn'], policy['DefaultVersionId'])):
                unwanted_resource = Resource(resource=policy,
                                             resource_type=self.resource_type,
                                             resource_id=policy['Arn'],
                                             creation_date=policy['CreateDate'],
                                             region='global')
                yield unwanted_resource


class InlinePolicy(Policy):

    def get_iam_role_names(self):
        client = boto3.client('iam')
        roles_response = client.list_roles()
        role_names = []
        for i in range(0, len(roles_response['Roles'])):
            role_names.append(roles_response['Roles'][i]['RoleName'])
        return role_names

    def get_inline_policy_all(self, role_name):
        iam = boto3.resource('iam')
        role_policies = []
        role = iam.Role(role_name)
        for role_policy in role.policies.all():
            role_policies.append(role_policy)
        return role_policies

 #   def get_inline_policy_documents(self, role_policies):
 #       policy_documents = []
 #       for inline_policy in role_policies:
 #           policy_documents.append(inline_policy.policy_document['Statement'][0])
 #       return policy_documents


    def check_inline_policy_action(self, policy_document):
        if ('*:*' or '*:*') in policy_document:
            return True

    def fetch_unwanted_resources(self):
        for role in self.get_iam_role_names():
            policy_names = self.get_inline_policy_all(role)
            for policy in policy_names:
                if self.check_inline_policy_action(policy.policy_document['Statement'][0]):
                    unwanted_resource = Resource(resource=role,
                                             resource_type=self.resource_type,
                                             resource_id=role['Arn'],
                                             creation_date=role['CreateDate'],
                                             region='global')
                yield unwanted_resource




