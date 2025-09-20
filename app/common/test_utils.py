import json
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
import pytest
from fastapi import UploadFile
from app.common.conftest import *
from app.common.models.Activity import Activity


@pytest.fixture(scope="function")
async def auth_token(async_client):
    response = await async_client.post(
        "/v1/api/auth/generate_token",
        json={"member_id": "9784737c-ee68-43a3-a635-28fb4765cfca"}
    )
    assert response.status_code == 200
    assert "token" in response.json()
    assert response.json()["message"] == "Access granted"
    return response.json()["token"]


@pytest.fixture(scope="function")
async def activities(async_session: AsyncSession):
    activity_1 = Activity(id=uuid.uuid4(),title="saving")
    activity_2 = Activity(id=uuid.uuid4(),title="placement")
    async_session.add_all([activity_1, activity_2])
    await async_session.commit()
    await async_session.refresh(activity_1)
    await async_session.refresh(activity_2)
    return [str(activity_1.id), str(activity_2.id)]


async def mock_upload_file_success(file: UploadFile, folder: str, name: Optional[str] = None) -> tuple[str, str]:
    """Mocks a successful S3 file upload, mimicking the actual function's return."""
    ext = os.path.splitext(file.filename)[1]
    key = f"{folder}/test-{name}{ext}"
    url = f"https://test-bucket.s3.test-region.amazonaws.com/{key}"
    return url, key


def prepare_expected_users_validator_list(users_validator_dict: Dict[str, str]) -> List[str]:
    """
    Transforms a dictionary of users_validator (e.g., {"0": "uuid1", "1": "uuid2"})
    into an ordered list (e.g., ["uuid1", "uuid2"]) based on sorted integer keys.
    This mimics the behavior of the Pydantic model's @validator.

    Args:
        users_validator_dict: The dictionary of validators from your fixture.

    Returns:
        An ordered list of validator UUIDs (as strings).
    """
    if not users_validator_dict:
        return []

    expected_list = []
    try:
        # Sort keys numerically
        ordered_keys = sorted([int(k) for k in users_validator_dict.keys()])

        # Build the ordered list
        for key_int in ordered_keys:
            expected_list.append(users_validator_dict[str(key_int)])
    except ValueError as e:
        raise ValueError(
            f"Error preparing expected users_validator list: Dictionary keys must be integers. {e}"
        )
    except Exception as e:
        raise Exception(
            f"An unexpected error occurred while preparing expected users_validator list: {e}"
        )
    return expected_list


# You might also want a helper for target_users if it also gets transformed,
# but if it's always a simple list, direct comparison or sorted() might be enough.
def prepare_expected_target_users_list(target_users_data: Any) -> List[str]:
    """
    Ensures target_users data is a list of strings, handling None if needed.
    """
    if target_users_data is None:
        return []
    if isinstance(target_users_data, list):
        return [str(u) for u in target_users_data]  # Ensure all are strings
    # If it was sent as a JSON string and parsed by Pydantic, it would be a list
    # If it's a dict for some reason, you might need to handle it.
    return [str(target_users_data)]  # Fallback, adjust if needed
