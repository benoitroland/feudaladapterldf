import pytest

from ldf_adapter import UserInfo, User

import settings


@pytest.mark.parametrize("data", settings.ALL_INPUT)
def test_get_status(user):
    # assert user.assurance_verifier() == True
    assert user.get_status().attributes == {"state": "not_deployed", "message": "No message"}
