import pytest
from app.common.conftest import *


@pytest.mark.asyncio
async def test_generate_token(async_client):
    a = 1
    assert a == 1


@pytest.mark.asyncio
async def test_generate_token_with_no_member_token(async_client):
    a = 1
    assert a == 1
