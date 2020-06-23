
import logging

import ldf_adapter

from ldf_adapter.config import CONFIG

logger = logging.getLogger(__name__)


def test_backend(backend, userinfo):
    ldf_adapter.backend.User(userinfo)
