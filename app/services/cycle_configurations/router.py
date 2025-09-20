from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.auth import JWTBearer
from app.common.pagination import PaginatedResponse
from app.config.database import get_db_instance
from app.services.cycle_configurations.constants import CycleState, ValidatorFlag, PenalityFlag
from app.services.cycle_configurations.handlers import (create_cycle, create_or_update_cycle_config,
                                                        create_penalty_category,
                                                        create_or_update_validator_config,
                                                        update_inactive_cycle, list_cycles, update_penalty_category,
                                                        create_office_member, update_guarantee,
                                                        create_guarantee,
                                                        create_loan_config, list_loan_config,
                                                        list_validator_config,
                                                        list_penalty_category,
                                                        create_or_update_penalty_sanction_config, list_penalty,
                                                        list_guarantee, list_office_members,
                                                        list_cycle_config,
                                                        toggle_activation_validator_config,
                                                        open_inactive_cycle, close_active_cycle, delete_guarantee,
                                                        delete_penalty_category, update_penalty_sanction_config,
                                                        update_manual_penalty_sanction, create_manual_penalty_sanction,
                                                        toggle_activation_manual_penalty, update_role, create_role,
                                                        list_roles, toggle_activation_role)
from app.services.cycle_configurations.schemas import CycleResponseSchema, CycleCreateSchema, CycleConfigCreateSchema, \
    CycleConfigResponseSchema, LoanConfigCreateSchema, LoanConfigResponseSchema, PenaltyCategoryCreateSchema, \
    PenaltyCategoryResponseSchema, ValidatorConfigCreateSchema, ValidatorConfigResponseSchema, \
    PenaltySanctionConfigResponseSchema, PenaltySanctionConfigCreateSchema, CreateOfficeSchema, \
    GuaranteeResponseSchema, GuaranteeCreateSchema, OfficeResponseSchema, EnumItem, PenaltySanctionConfigUpdateSchema, \
    PenaltySanctionConfigCreateBase, RoleCreateSchema, RoleResponseSchema

router = APIRouter(prefix="/v1/api/cycle_settings", tags=["Cycle Settings"])






@router.post("", response_model=CycleResponseSchema)
async def create_cycle_route(
        payload: CycleCreateSchema,
        db: AsyncSession = Depends(get_db_instance),
): return await create_cycle(payload, db)


@router.put("/{id}", response_model=CycleResponseSchema, dependencies=[Depends(JWTBearer())])
async def update_cycle_route(
        payload: CycleCreateSchema,
        id: UUID,
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer())
): return await update_inactive_cycle(payload, db, id, token)


# @router.delete("/{id}", dependencies=[Depends(JWTBearer())])
# async def toggle_activation_cycle_route(
#         id: UUID,
#         db: AsyncSession = Depends(get_db_instance),
# ): return await toggle_activation_inactive_cycle(db, id)


@router.get("", response_model=PaginatedResponse[CycleResponseSchema], dependencies=[Depends(JWTBearer())])
async def list_cycles_route(
        request: Request,
        page: int = Query(1, ge=1),
        size: int = Query(10, gt=0, le=30),
        state: Optional[CycleState] = Query(None),
        id: Optional[UUID] = Query(None),
        office: Optional[bool] = Query(None),
        db: AsyncSession = Depends(get_db_instance),
): return await list_cycles(db, page, size, str(request.url_for("list_cycles_route")), state, id, office)


@router.post("/config", response_model=CycleConfigResponseSchema, dependencies=[Depends(JWTBearer())])
async def create_or_update_cycle_config_route(
        payload: CycleConfigCreateSchema,
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer())
): return await create_or_update_cycle_config(payload, db, token)


# @router.delete("/config/{id}", dependencies=[Depends(JWTBearer())])
# async def toggle_activation_cycle_config_route(
#         id: UUID,
#         db: AsyncSession = Depends(get_db_instance),
# ): return await toggle_activation_cycle_config(db, id)


@router.get("/config", response_model=PaginatedResponse[CycleConfigResponseSchema], dependencies=[Depends(JWTBearer())])
async def list_cycle_config_route(
        request: Request,
        page: int = Query(1, ge=1),
        size: int = Query(10, gt=0, le=30),
        cycle_id: Optional[UUID] = Query(None),
        db: AsyncSession = Depends(get_db_instance),
): return await list_cycle_config(db, page, size, str(request.url_for("list_cycle_config_route")), cycle_id)


@router.post("/role", response_model=RoleResponseSchema)
async def create_role_route(
    data: RoleCreateSchema,
    db: AsyncSession = Depends(get_db_instance),
    token: str = Depends(JWTBearer())
): return await create_role(data, db, token)


@router.put("/role/{id}", response_model=RoleResponseSchema)
async def update_role_route(
    id: UUID,
    data: RoleCreateSchema,
    db: AsyncSession = Depends(get_db_instance),
    token: str = Depends(JWTBearer())
): return await update_role(data, db, token, id)


@router.delete("/role/{id}", response_model=dict)
async def toggle_activation_role_route(
    id: UUID,
    db: AsyncSession = Depends(get_db_instance)
): return await toggle_activation_role(db, id)


@router.get("/role", response_model=PaginatedResponse[RoleResponseSchema])
async def list_roles_route(
    db: AsyncSession = Depends(get_db_instance),
    page: int = Query(1, ge=1),
    size: int = Query(10, le=100),
    base_url: str = Query(""),
    sub_client_id: Optional[UUID] = None,
    not_for_sub_client: Optional[bool] = None
): return await list_roles(db, page, size, base_url, sub_client_id, not_for_sub_client)


@router.post("/office", dependencies=[Depends(JWTBearer())])
async def register_office(
        data: CreateOfficeSchema,
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer())
): return await create_office_member(data, db, token)


# @router.put("/office/{id}", dependencies=[Depends(JWTBearer())])
# async def update_office_route(
#         id: UUID,
#         data: CreateOfficeSchema,
#         db: AsyncSession = Depends(get_db_instance),
#         token: str = Depends(JWTBearer())
# ): return await update_office_member(id, data, db, token)
#
#
# @router.delete("/office/{id}", dependencies=[Depends(JWTBearer())])
# async def toggle_activation_office(
#         id: UUID,
#         db: AsyncSession = Depends(get_db_instance),
# ): return await toggle_activation_office_member(db, id)


@router.get("/office", response_model=PaginatedResponse[OfficeResponseSchema],  dependencies=[Depends(JWTBearer())])
async def list_office_route(
        request: Request,
        page: int = Query(1, ge=1),
        size: int = Query(10, gt=0, le=30),
        user_id: Optional[UUID] = Query(None),
        role_id: Optional[UUID] = Query(None),
        db: AsyncSession = Depends(get_db_instance),
): return await list_office_members(db, page, size, str(request.url_for("list_office_route")), user_id, role_id)


@router.get("/validator-flags", response_model=List[EnumItem],  dependencies=[Depends(JWTBearer())])
async def list_validator_flags():
    return [{"name": flag.name, "value": flag.value, "description": flag.description} for flag in ValidatorFlag]


@router.post("/validator-config", response_model=ValidatorConfigResponseSchema, dependencies=[Depends(JWTBearer())])
async def create_validator_config_route(
        payload: ValidatorConfigCreateSchema,
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer())
): return await create_or_update_validator_config(payload, db, token)

@router.delete("/validator-config/{id}", dependencies=[Depends(JWTBearer())])
async def toggle_activation_validator_config_route(id: UUID, db: AsyncSession = Depends(get_db_instance)):
    return await toggle_activation_validator_config(db, id)

@router.get("/validator-config", response_model=PaginatedResponse[ValidatorConfigResponseSchema])
async def list_validator_config_route(
        request: Request,
        page: int = Query(1, ge=1),
        size: int = Query(10, gt=0, le=30),
        cycle_id: Optional[UUID] = Query(None),
        db: AsyncSession = Depends(get_db_instance),
): return await list_validator_config(db, page, size, str(request.url_for("list_validator_config_route")), cycle_id)


@router.post("/penalty-category", response_model=PenaltyCategoryResponseSchema, dependencies=[Depends(JWTBearer())])
async def create_penalty_category_route(
        payload: PenaltyCategoryCreateSchema,
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer())
): return await create_penalty_category(payload, db, token)


@router.put("/penalty-category/{id}", response_model=PenaltyCategoryResponseSchema, dependencies=[Depends(JWTBearer())])
async def update_penalty_category_route(
        payload: PenaltyCategoryCreateSchema,
        id: UUID,
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer())
): return await update_penalty_category(payload, db, token, id)


@router.delete("/penalty-category/{id}", dependencies=[Depends(JWTBearer())])
async def delete_penalty_category_route(
        id: UUID,
        db: AsyncSession = Depends(get_db_instance),
): return await delete_penalty_category(db, id)


@router.get("/penalty-category", response_model=PaginatedResponse[PenaltyCategoryResponseSchema],  dependencies=[Depends(JWTBearer())])
async def list_penalty_category_route(
        request: Request,
        page: int = Query(1, ge=1),
        size: int = Query(10, gt=0, le=30),
        cycle_id: Optional[UUID] = Query(None),
        db: AsyncSession = Depends(get_db_instance),
): return await list_penalty_category(db, page, size, str(request.url_for("list_penalty_category_route")), cycle_id)


@router.get("/penalty-flags", response_model=List[EnumItem],  dependencies=[Depends(JWTBearer())])
async def list_penality_flags():
    return [{"name": flag.name, "value": flag.value, "description": flag.description} for flag in PenalityFlag]


@router.post("/predefined-penalty", response_model=PenaltySanctionConfigResponseSchema, dependencies=[Depends(JWTBearer())])
async def create_or_update_penalty_route(
        payload: PenaltySanctionConfigCreateSchema,
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer())
): return await create_or_update_penalty_sanction_config(payload, db, token)


@router.put("/predefined-penalty/{id}", response_model=PenaltySanctionConfigResponseSchema, dependencies=[Depends(JWTBearer())])
async def update_penalty_route(
        id: UUID,
        payload: PenaltySanctionConfigUpdateSchema,
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer())
): return await update_penalty_sanction_config(payload, db, token, id)


@router.post("/manual-penalty", response_model=PenaltySanctionConfigResponseSchema, dependencies=[Depends(JWTBearer())])
async def create_manual_penalty_route(
        payload: PenaltySanctionConfigCreateBase,
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer())
): return await create_manual_penalty_sanction(payload, db, token)


@router.put("/manual-penalty/{id}", response_model=PenaltySanctionConfigResponseSchema, dependencies=[Depends(JWTBearer())])
async def update_manual_penalty_route(
        id: UUID,
        payload: PenaltySanctionConfigCreateBase,
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer())
): return await update_manual_penalty_sanction(payload, db, token, id)


@router.delete("/penalty/{id}", dependencies=[Depends(JWTBearer())])
async def toggle_activation_manual_penalty_route(
        id: UUID,
        db: AsyncSession = Depends(get_db_instance),
): return await toggle_activation_manual_penalty(db, id)


@router.get("/penalty", response_model=PaginatedResponse[PenaltySanctionConfigResponseSchema])
async def list_penalty_route(
        request: Request,
        page: int = Query(1, ge=1),
        size: int = Query(10, gt=0, le=30),
        cycle_id: Optional[UUID] = Query(None),
        manual: Optional[bool] = Query(None),
        db: AsyncSession = Depends(get_db_instance),
): return await list_penalty(db, page, size, str(request.url_for("list_penalty_route")), cycle_id, manual)


@router.post("/loan-config", response_model=LoanConfigResponseSchema, dependencies=[Depends(JWTBearer())])
async def create_loan_config_route(
        payload: LoanConfigCreateSchema,
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer())
): return await create_loan_config(payload, db, token)


# @router.put("/loan-config/{id}", response_model=LoanConfigResponseSchema, dependencies=[Depends(JWTBearer())])
# async def update_loan_config_route(
#         id: UUID,
#         payload: LoanConfigCreateSchema,
#         db: AsyncSession = Depends(get_db_instance),
#         token: str = Depends(JWTBearer())
# ): return await update_loan_config(payload, db, token, id)


# @router.delete("/loan-config/{id}", dependencies=[Depends(JWTBearer())])
# async def toggle_activation_loan_config_route(
#         id: UUID,
#         db: AsyncSession = Depends(get_db_instance),
# ): return await toggle_activation_loan_config(db, id)


@router.get("/loan-config", response_model=PaginatedResponse[LoanConfigResponseSchema],
            dependencies=[Depends(JWTBearer())])
async def list_loan_config_route(
        request: Request,
        page: int = Query(1, ge=1),
        size: int = Query(10, gt=0, le=30),
        cycle_id: Optional[UUID] = Query(None),
        db: AsyncSession = Depends(get_db_instance),
): return await list_loan_config(db, page, size, str(request.url_for("list_loan_config_route")), cycle_id)



@router.post("/guarantee", response_model=GuaranteeResponseSchema, dependencies=[Depends(JWTBearer())])
async def create_guarantee_route(
        payload: GuaranteeCreateSchema,
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer())
): return await create_guarantee(payload, db, token)


@router.put("/guarantee/{id}", response_model=GuaranteeResponseSchema, dependencies=[Depends(JWTBearer())])
async def update_guarantee_route(
        payload: GuaranteeCreateSchema,
        id: UUID,
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer())
): return await update_guarantee(payload, db, token, id)


@router.delete("/guarantee/{id}", dependencies=[Depends(JWTBearer())])
async def delete_guarantee_route(id: UUID, db: AsyncSession = Depends(get_db_instance)):
    return await delete_guarantee(db, id)


@router.get("/guarantee", response_model=PaginatedResponse[GuaranteeResponseSchema])
async def list_guarantee_route(
        request: Request,
        page: int = Query(1, ge=1),
        size: int = Query(10, gt=0, le=30),
        cycle_id: Optional[UUID] = Query(None),
        db: AsyncSession = Depends(get_db_instance),
): return await list_guarantee(db, page, size, str(request.url_for("list_guarantee_route")), cycle_id)


@router.post("/open/{id}")
async def open_cycle_route(
        id: UUID,
        db: AsyncSession = Depends(get_db_instance),
): return await open_inactive_cycle(db, id)


@router.post("/close/{id}")
async def close_cycle_route(
        id: UUID,
        db: AsyncSession = Depends(get_db_instance),
): return await close_active_cycle(db, id)