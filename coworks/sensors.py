import warnings

from coworks.biz.sensors import *  # legacy

warnings.warn(
    "This module is deprecated. Please use `coworks.biz` or `coworks.biz.sensors` instead.",
    DeprecationWarning,
    stacklevel=2,
)
