from aws_xray_sdk.core import xray_recorder

from coworks.extension.xray import XRay
from website import WebsiteMicroService

app = WebsiteMicroService()
XRay(app, xray_recorder)
