from dataclasses import dataclass

from chalice import CORSConfig


@dataclass
class Config:
    cors: CORSConfig = CORSConfig()
    timeout: int = 60
