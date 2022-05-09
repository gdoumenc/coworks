from abc import ABC
from abc import abstractmethod

import requests


class CwsProxy(ABC):

    def __init__(self):
        self.__initialized = False
        self.url = f"https://{self.id}.execute-api.{self.region}.amazonaws.com/{self.stage}"
        self.headers = {
            "Authorization": self.token,
            "Content-Type": self.content_type,
            "Accept": self.accept,
        }

    def call(self, method, path, **kwargs):
        return requests.request(method, f"{self.url}{path}", headers=self.headers, **kwargs)

    @property
    @abstractmethod
    def id(self):
        ...

    @property
    @abstractmethod
    def token(self):
        ...

    @property
    def stage(self):
        return 'dev'

    @property
    def content_type(self):
        return 'application/json'

    @property
    def accept(self):
        return 'application/json'

    @property
    def region(self):
        return 'eu-west-1'
