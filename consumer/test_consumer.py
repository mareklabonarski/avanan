import pytest

from consumer.__main__ import detect_data_leak, update_patterns
from web.models import DataLeak


@pytest.mark.parametrize(
    "message, dcm_rt, pci_rt, delete_called, dcm_called, pci_called, leak_created", [
        (pytest.lazy_fixture('message_fine'), None, None, True, False, False, False),
        (pytest.lazy_fixture('message_visa_card'), Exception, None, False, True, True, False),
        (pytest.lazy_fixture('message_visa_card'), None, Exception, False, True, True, False),
        (pytest.lazy_fixture('message_visa_card'), None, None, True, True, True, True),
    ]
)
@pytest.mark.asyncio
@pytest.mark.django_db
async def test__detect_data_leak__scenarios(
        mocker, visa_card_pattern, message, dcm_rt, pci_rt, delete_called, dcm_called, pci_called, leak_created):
    dcm = mocker.patch('consumer.__main__.delete_chat_message', side_effect=dcm_rt)
    pci = mocker.patch('consumer.__main__.post_chat_info', side_effect=pci_rt)

    await update_patterns(once=True)

    E = dcm_rt or pci_rt
    try:
        await detect_data_leak(message)
    except Exception:
        if not E:
            pytest.fail(f'{E} raised')
    else:
        if E:
            pytest.fail(f'{E} not raised')

    assert message.delete.called == delete_called
    assert dcm.called == dcm_called
    assert pci.called == pci_called
    assert await DataLeak.objects.filter(message=message.body).aexists() == leak_created

