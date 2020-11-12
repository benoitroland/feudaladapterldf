
import logging

from ldf_adapter import *

from ldf_adapter.config import CONFIG

logger = logging.getLogger(__name__)

def test_backend(backend, user_data):
    # TODO This is not a real test
    backend.User(UserInfo(user_data))
