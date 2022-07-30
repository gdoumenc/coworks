from config import DevConfig
from config import ProdConfig
from coworks.tech.directory import DirectoryMicroService

dev = DevConfig()
prod = ProdConfig()

app = DirectoryMicroService(configs=[dev, prod])
