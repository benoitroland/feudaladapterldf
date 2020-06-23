
import logging

from ldf_adapter.backend import Backend

from ldf_adapter.config import CONFIG

logger = logging.getLogger(__name__)


def test_backend(config, userinfo):
    logger.debug('Backend: %s', CONFIG['ldf_adapter']['backend'])

    backend = Backend()
    backend.User(userinfo)

    assert False
