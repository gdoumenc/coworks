from dataclasses import dataclass

from chalice import CORSConfig as ChaliceCORSConfig


class CORSConfig(ChaliceCORSConfig):

    def get_access_control_headers(self):
        if not self.allow_origin:
            return {}
        return super().get_access_control_headers()


@dataclass
class Config:
    cors: CORSConfig = CORSConfig(allow_origin='')
    timeout: int = 60
