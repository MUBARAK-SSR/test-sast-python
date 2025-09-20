# import pytest
# from app.common.conftest import *
# from app.common.test_utils import auth_token, activities
#
#
# @pytest.fixture(scope="function")
# async def create_cycle_data(activities):
#     return {
#         "activity_id": activities[0],
#         "name": "epargne projet A",
#         "description": "string",
#         "start_date": "2025-01-01",
#         "end_date": "2025-12-31",
#         # "day_number": 0,
#         "frequency_cycle": "weekly",
#         "frequency_week": "first",
#         "week_day": "monday",
#         "currency": "XAF"
#     }
#
# @pytest.mark.asyncio
# async def test_create_cycle_valid(async_client, auth_token, create_cycle_data):
#     response = await async_client.post("/v1/api/cycle_settings/", json=create_cycle_data, headers={"Authorization": f"Bearer {auth_token}"})
#     print(response.json())
#     assert response.status_code == 200
#     assert response.json()["name"] == create_cycle_data["name"]
#
#
# @pytest.mark.asyncio
# async def test_create_cycle_start_date_invalid(async_client, auth_token, create_cycle_data):
#     create_cycle_data["start_date"] = "2025-07-10"
#     create_cycle_data["end_date"] = "2025-07-01"
#
#     response = await async_client.post("/v1/api/cycle_settings/", json=create_cycle_data, headers={"Authorization": f"Bearer {auth_token}"})
#     print(response.json())
#
#     assert response.status_code == 400
#     assert "La date de début doit être antérieure à la date de fin." in response.json()["message"]
#
#
# @pytest.mark.asyncio
# async def test_create_cycle_activity_not_found(async_client, auth_token, create_cycle_data):
#     create_cycle_data["activity_id"] = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
#     response = await async_client.post("/v1/api/cycle_settings/", json=create_cycle_data, headers={"Authorization": f"Bearer {auth_token}"})
#     print(response.json())
#
#     assert response.status_code == 404
#     assert "L'activité avec l'ID" in response.json()["message"]
#
#
# @pytest.mark.asyncio
# async def test_create_cycle_name_duplicate(async_client, auth_token, create_cycle_data):
#     # Créez d'abord un cycle avec un nom unique
#     await async_client.post("/v1/api/cycle_settings/", json=create_cycle_data, headers={"Authorization": f"Bearer {auth_token}"})
#
#     # Essayez de créer un cycle avec le même nom
#     response = await async_client.post("/v1/api/cycle_settings/", json=create_cycle_data, headers={"Authorization": f"Bearer {auth_token}"})
#     print(response.json())
#
#     assert response.status_code == 422
#     assert f"Un cycle avec le nom '{create_cycle_data['name']}' existe déjà." in response.json()["message"]
#
#
# @pytest.mark.asyncio
# async def test_create_cycle_invalid_token(async_client, create_cycle_data):
#     response = await async_client.post("/v1/api/cycle_settings/", json=create_cycle_data, headers={"Authorization": "Bearer invalid_token"})
#     assert response.status_code == 401
#     assert response.json()["message"] == "Invalid token"