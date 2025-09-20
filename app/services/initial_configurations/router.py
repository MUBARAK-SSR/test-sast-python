from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, Request, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.auth import JWTBearer
from app.common.factories.activity_factory import ActivityFactory
from app.common.pagination import PaginatedResponse
from app.config.database import get_db_instance
from app.services.cycle_configurations.constants import PaymentAccountType
from app.services.initial_configurations.handlers import toggle_activation_user, list_users, register_users, \
    update_sub_client_payment_account, create_user_payment_account, update_user_payment_account, list_payment_account, \
    toggle_activation_payment_account, list_activities, create_operator, update_operator, toggle_activation_operator, \
    list_operator, create_sub_client_payment_account, update_client, update_sub_client, toggle_activation_client, \
    toggle_activation_sub_client, list_client, create_client_with_sub_client, create_merchant_account, \
    update_merchant_account, create_sub_client, sub_client_activities
from app.services.initial_configurations.schemas import CreateUserOutSchema, CreateUserSchema, \
    SubClientPaymentAccountSchema, UserPaymentAccountSchema, PaymentAccountResponseSchema, ActivityOut, \
    OperatorResponseSchema, OperatorCreateSchema, SubClientCreateSchema, ClientResponseSchemaOut, SubClientResponse, \
    ClientResponseOut, ClientSchema, ClientResponseSchema, ClientCreateSchema, MerchantPaymentAccountSchema, \
    SubClientActivitiesSchema

router = APIRouter(prefix="/v1/api/initial_settings", tags=["Initial Settings"])



@router.post("/client-with-sub-clients", response_model=ClientResponseSchema)
async def create_client_with_sub_client_route(
        payload: ClientCreateSchema,
        db: AsyncSession = Depends(get_db_instance),
): return await create_client_with_sub_client(payload, db)


@router.post("/sub-clients", response_model=SubClientCreateSchema, dependencies=[Depends(JWTBearer())])
async def create_sub_client_route(
        payload: SubClientCreateSchema,
        db: AsyncSession = Depends(get_db_instance),
): return await create_sub_client(payload, db)


# @router.put("/client-with-sub-clients/{id}", response_model=ClientResponseSchema, dependencies=[Depends(JWTBearer())])
# async def update_client_with_sub_client_route(
#         payload: ClientCreateSchema,
#         id: UUID,
#         db: AsyncSession = Depends(get_db_instance),
# ): return await update_client_with_sub_client(payload, db, id)


@router.put("/client/{id}", response_model=ClientResponseOut, dependencies=[Depends(JWTBearer())])
async def update_client_route(
        payload: ClientSchema,
        id: UUID,
        db: AsyncSession = Depends(get_db_instance),
): return await update_client(payload, db, id)


@router.put("/sub-client/{id}", response_model=SubClientResponse, dependencies=[Depends(JWTBearer())])
async def update_sub_client_route(
        payload: SubClientCreateSchema,
        id: UUID,
        db: AsyncSession = Depends(get_db_instance),
): return await update_sub_client(payload, db, id)


@router.delete("/client/{id}", dependencies=[Depends(JWTBearer())])
async def toggle_activation_client_route(id: UUID, db: AsyncSession = Depends(get_db_instance)):
    return await toggle_activation_client(db, id)


@router.delete("/sub-client/{id}", dependencies=[Depends(JWTBearer())])
async def toggle_activation_sub_client_route(id: UUID, db: AsyncSession = Depends(get_db_instance)):
    return await toggle_activation_sub_client(db, id)


@router.get("/client", response_model=PaginatedResponse[ClientResponseSchemaOut], dependencies=[Depends(JWTBearer())])
async def list_client_route(
        request: Request,
        page: int = Query(1, ge=1),
        size: int = Query(10, gt=0, le=30),
        client_id: Optional[UUID] = Query(None),
        db: AsyncSession = Depends(get_db_instance),
): return await list_client(db, page, size, str(request.url_for("list_client_route")), client_id)


@router.post("/{sub_client_id}/users")
async def register_users_route(
        sub_client_id: UUID,
        data: List[CreateUserSchema],
        db: AsyncSession = Depends(get_db_instance)
): return await register_users(sub_client_id, data, db)


@router.delete("/user/{id}", dependencies=[Depends(JWTBearer())])
async def toggle_activation_user_route(id: UUID, db: AsyncSession = Depends(get_db_instance)):
    return await toggle_activation_user(db, id)


@router.get("/user", response_model=PaginatedResponse[CreateUserOutSchema], dependencies=[Depends(JWTBearer())])
async def list_users_route(
        request: Request,
        page: int = Query(1, ge=1),
        size: int = Query(10, gt=0, le=30),
        state: bool = Query(None),
        id: Optional[UUID] = Query(None),
        db: AsyncSession = Depends(get_db_instance),
): return await list_users(db, page, size, str(request.url_for("list_users_route")), state, id)


# @router.post("/type-operators")
# async def create_type_operators(db: AsyncSession = Depends(get_db_instance)):
#     type_operator_factory = TypeOperatorFactory.build()
#     db.add(type_operator_factory)
#     await db.commit()
#     await db.refresh(type_operator_factory)
#     return type_operator_factory


# @router.post("/type-operator", response_model=TypeOperatorResponseSchema, dependencies=[Depends(JWTBearer())])
# async def create_type_operator_route(
#         payload: TypeOperatorCreateSchema,
#         db: AsyncSession = Depends(get_db_instance),
# ): return await create_type_operator(payload, db)
#
#
# @router.put("/type-operator/{common_id}", response_model=TypeOperatorResponseSchema,
#             dependencies=[Depends(JWTBearer())])
# async def update_type_operator_route(
#         payload: TypeOperatorCreateSchema,
#         common_id: str,
#         db: AsyncSession = Depends(get_db_instance),
# ): return await update_type_operator(payload, db, common_id)
#
#
# @router.delete("/type-operator/{common_id}", dependencies=[Depends(JWTBearer())])
# async def toggle_activation_type_operator_route(common_id: str, db: AsyncSession = Depends(get_db_instance)):
#     return await toggle_activation_type_operator(db, common_id)
#
#
# @router.get("/type-operator", response_model=PaginatedResponse[TypeOperatorResponseSchema],
#             dependencies=[Depends(JWTBearer())])
# async def list_type_operator_route(
#         request: Request,
#         page: int = Query(1, ge=1),
#         size: int = Query(10, gt=0, le=30),
#         cycle_id: Optional[UUID] = Query(None),
#         db: AsyncSession = Depends(get_db_instance),
# ): return await list_type_operator(db, page, size, str(request.url_for("list_type_operator_route")))


@router.post("/operator", response_model=OperatorResponseSchema, dependencies=[Depends(JWTBearer())])
async def create_operator_route(
        payload: OperatorCreateSchema,
        db: AsyncSession = Depends(get_db_instance),
): return await create_operator(payload, db)


@router.put("/operator/{common_id}", response_model=OperatorResponseSchema, dependencies=[Depends(JWTBearer())])
async def update_operator_route(
        common_id: str,
        payload: OperatorCreateSchema,
        db: AsyncSession = Depends(get_db_instance)
): return await update_operator(payload, db, common_id)


@router.delete("/operator/{common_id}", dependencies=[Depends(JWTBearer())])
async def toggle_activation_operator_route(common_id: str, db: AsyncSession = Depends(get_db_instance)):
    return await toggle_activation_operator(db, common_id)


@router.get("/operator", response_model=PaginatedResponse[OperatorResponseSchema], dependencies=[Depends(JWTBearer())])
async def list_operator_route(
        request: Request,
        page: int = Query(1, ge=1),
        size: int = Query(10, gt=0, le=30),
        id: Optional[UUID] = Query(None),
        active: Optional[bool] = Query(None),
        db: AsyncSession = Depends(get_db_instance),
): return await list_operator(db, page, size, str(request.url_for("list_operator_route")), active, id)


@router.post("/sub-client-parent-merchant", dependencies=[Depends(JWTBearer())])
async def save_sub_client_parent_merchant_account(
        payload: MerchantPaymentAccountSchema,
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer()),
): return await create_merchant_account(payload, db, token, "mere")


@router.put("/sub-client-parent-merchant/{id}", dependencies=[Depends(JWTBearer())])
async def edit_sub_client_parent_merchant_account(
        id: UUID,
        payload: MerchantPaymentAccountSchema,
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer()),
): return await update_merchant_account(payload, db, token, id, "mere")


@router.post("/sub-client-child-merchant", dependencies=[Depends(JWTBearer())])
async def save_sub_client_child_merchant_account(
        payload: MerchantPaymentAccountSchema,
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer()),
): return await create_merchant_account(payload, db, token, "fille")


@router.put("/sub-client-child-merchant/{id}", dependencies=[Depends(JWTBearer())])
async def edit_sub_client_child_merchant_account(
        id: UUID,
        payload: MerchantPaymentAccountSchema,
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer()),
): return await update_merchant_account(payload, db, token, id, "fille")


@router.post("/sub-client-payment-account", dependencies=[Depends(JWTBearer())])
async def save_sub_client_payment_account(
        payload: SubClientPaymentAccountSchema = Depends(SubClientPaymentAccountSchema.as_form),
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer()),
): return await create_sub_client_payment_account(payload, db, token)


@router.put("/sub-client-payment-account/{id}", dependencies=[Depends(JWTBearer())])
async def edit_sub_client_payment_account(
        id: UUID,
        payload: SubClientPaymentAccountSchema = Depends(SubClientPaymentAccountSchema.as_form),
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer())
): return await update_sub_client_payment_account(payload, db, token, id)


@router.post("/user-payment-account", dependencies=[Depends(JWTBearer())])
async def save_user_payment_account(
        payload: UserPaymentAccountSchema = Depends(UserPaymentAccountSchema.as_form),
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer())
): return await create_user_payment_account(payload, db, token)


@router.put("/user-payment-account/{id}", dependencies=[Depends(JWTBearer())])
async def edit_user_payment_account(
        id: UUID,
        payload: UserPaymentAccountSchema = Depends(UserPaymentAccountSchema.as_form),
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer()),
): return await update_user_payment_account(payload, db, token, id)


@router.delete("/payment-account/{id}", dependencies=[Depends(JWTBearer())])
async def toggle_activation_payment_account_route(id: UUID, db: AsyncSession = Depends(get_db_instance)):
    return await toggle_activation_payment_account(db, id)


@router.get("/payment-account", response_model=PaginatedResponse[PaymentAccountResponseSchema])
async def list_payment_account_route(
        request: Request,
        page: int = Query(1, ge=1),
        size: int = Query(10, gt=0, le=30),
        user_id: Optional[UUID] = Query(None),
        sub_client_id: Optional[UUID] = Query(None),
        account_type: Optional[PaymentAccountType] = Query(None),
        db: AsyncSession = Depends(get_db_instance),
): return await list_payment_account(db, page, size, str(request.url_for("list_payment_account_route")), user_id,
                                     sub_client_id, account_type)


@router.post("/activities")
async def create_activity(db: AsyncSession = Depends(get_db_instance)):
    activity = ActivityFactory.build()  # Crée une instance d'Activity
    db.add(activity)
    await db.commit()
    await db.refresh(activity)
    return activity


@router.get("/activities", response_model=PaginatedResponse[ActivityOut])
async def list_activities_route(
        request: Request,
        page: int = Query(1, ge=1),
        size: int = Query(10, gt=0, le=30),
        id: Optional[UUID] = Query(None),
        db: AsyncSession = Depends(get_db_instance),
): return await list_activities(db, page, size, str(request.url_for("list_activities_route")), id)


@router.post("/sub-client/{sub_client_id}/activities")
async def sub_client_activities_route(
        sub_client_id: UUID,
        data: SubClientActivitiesSchema,
        db: AsyncSession = Depends(get_db_instance)
): return await sub_client_activities(sub_client_id, data, db)
