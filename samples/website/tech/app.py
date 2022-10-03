from config import DevConfig
from config import LocalConfig
from config import ProdConfig
from website import WebsiteMicroService

app = WebsiteMicroService(configs=[LocalConfig(), DevConfig(), ProdConfig()])
