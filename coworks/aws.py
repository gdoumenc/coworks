import os

import boto3

from coworks.error import CwsError


class Boto3Mixin:

    def __init__(self, service='s3', profile_name=None, env_var_access_key='aws_access_key_id',
                 env_var_secret_key='aws_secret_access_key', env_var_region='aws_region',
                 **kwargs):
        super().__init__(**kwargs)
        self.__session__ = self.__client__ = None
        self.__service = service
        self.__env_var_access_key = env_var_access_key
        self.__env_var_secret_key = env_var_secret_key
        self.__env_var_region = env_var_region

        self.__profile_name = profile_name

    @property
    def aws_access_key(self):
        value = os.getenv(self.__env_var_access_key)
        if not value:
            raise EnvironmentError(f"{self.__env_var_access_key} not defined in environment")
        return value

    @property
    def aws_secret_access_key(self):
        value = os.getenv(self.__env_var_secret_key)
        if not value:
            raise EnvironmentError(f"{self.__env_var_secret_key} not defined in environment")
        return value

    @property
    def region_name(self):
        if self.__session__:
            return self.__session__.region_name

        value = os.getenv(self.__env_var_region)
        if not value and self.aws_access_key and self.aws_secret_access_key:
            raise EnvironmentError(f"{self.__env_var_region} not defined in environment")
        return value

    @property
    def client(self):
        if self.__client__ is None:
            self.__client__ = self.__session.client(self.__service)
        return self.__client__

    @property
    def __session(self):
        if self.__session__ is None:
            if self.__profile_name is not None:
                try:
                    self.__session__ = boto3.Session(profile_name=self.__profile_name)
                except Exception:
                    raise CwsError(f"Cannot create session for profile {self.__profile_name}.")
            else:
                access_key = self.aws_access_key
                secret_key = self.aws_secret_access_key
                region_name = self.region_name
                try:
                    self.__session__ = boto3.Session(access_key, secret_key, region_name=region_name)
                except Exception:
                    raise CwsError(
                        f"Cannot create session for key {access_key}, secret {secret_key} and region {region_name}.")
        return self.__session__


class AwsS3Session(Boto3Mixin):

    def __init__(self, **kwargs):
        super().__init__(service='s3', **kwargs)


class AwsSFNSession(Boto3Mixin):

    def __init__(self, **kwargs):
        super().__init__(service='stepfunctions', **kwargs)
