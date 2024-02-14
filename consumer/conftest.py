from unittest.mock import Mock
from uuid import uuid4

import pytest
import pytest_asyncio

from utils import prepare_message_attributes
from web.models import SensitiveDataPattern


event1 = {
    "ts": "1707933703.452479",
    "channel": "C06JK5TE5PC",
    "user": "U06JG84SRMK"
}



@pytest_asyncio.fixture
@pytest.mark.django_db
async def visa_card_pattern():
    pattern = '.*(4[0-9]{3} [0-9]{4} [0-9]{4} (?:[0-9]{4})?).*'
    p = await SensitiveDataPattern.objects.acreate(name='Visa Card', pattern=pattern)
    yield p
    await p.adelete()


@pytest.fixture
def message_fine():
    mock = Mock(
        body='Hello World',
        message_attributes=prepare_message_attributes(event1),
        delete=Mock()
    )
    return mock


@pytest.fixture
def message_visa_card():
    mock = Mock(
        body='Hello World 4056 2106 0266 6505 sensitive data',
        message_attributes=prepare_message_attributes(event1),
        delete=Mock(),
        message_id=uuid4()
    )
    return mock
