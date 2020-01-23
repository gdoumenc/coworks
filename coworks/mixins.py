import os
import boto3
import logging

logger = logging.getLogger()


class Boto3Mixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__session__ = None

    @property
    def aws_access_key_id(self):
        value = os.getenv('aws_access_key_id')
        if not value:
            logger.info('aws_access_key_id not defined in environment')
            raise EnvironmentError('aws_access_key_id not defined in environment')
        return value

    @property
    def aws_secret_access_key(self):
        value = os.getenv('aws_secret_access_key')
        if not value:
            logger.info('aws_secret_access_key not defined in environment')
            raise EnvironmentError('aws_secret_access_key not defined in environment')
        return value

    @property
    def region_name(self):
        value = os.getenv('aws_region')
        if not value:
            logger.info('aws_region not defined in environment')
            raise EnvironmentError('aws_region not defined in environment')
        return value

    @property
    def boto3_session(self):
        if self.__session__ is None:
            try:
                self.__session__ = boto3.Session(self.aws_access_key_id, self.aws_secret_access_key,
                                                 region_name=self.region_name)
            except Exception:
                logger.error(
                    f"Cannot create session for key {self.aws_access_key_id} and sercret {self.aws_secret_access_key}"
                )
                raise
        return self.__session__
