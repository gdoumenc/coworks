import warnings

from coworks.biz.operators import * # legacy

warnings.warn(
    "This module is deprecated. Please use `coworks.biz` or `coworks.biz.operators` instead.",
    DeprecationWarning,
    stacklevel=2,
)
