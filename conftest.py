# pylint: disable=global-statement

import pytest

from ldf_adapter.config import CONFIG


# this is from:
# https://docs.pytest.org/en/stable/example/parametrize.html#deferring-the-setup-of-parametrized-resources
def pytest_generate_tests(metafunc):
    if 'backend' in metafunc.fixturenames:
        metafunc.parametrize('backend', ['bwidm', 'local_unix'], indirect=True)

@pytest.fixture
def backend(request):
    global CONFIG
    CONFIG['ldf_adapter']['backend'] = request.param
    return CONFIG
