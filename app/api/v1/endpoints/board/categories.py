"""게시판 카테고리 엔드포인트"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.core.database import get_db
from app.api.v1.dependencies.api_key import verify_api_key
from app.api.v1.dependencies.auth import verify_any_platform, AuthResult
from app.domain.board.models.category import BoardCategory
from app.domain.board.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
)

router = APIRouter()


@router.get("", response_model=list[CategoryResponse])
async def list_categories(
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """모든 게시판 카테고리 조회"""
    result = await db.execute(
        select(BoardCategory).where(BoardCategory.is_active == True).order_by(BoardCategory.order_index)
    )
    categories = result.scalars().all()
    return categories


@router.post("", response_model=CategoryResponse, status_code=201)
async def create_category(
    data: CategoryCreate,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    게시판 카테고리 생성 (인증 필수)

    관리자만 가능 (추후 권한 체크 추가)
    """
    # TODO: 관리자 권한 확인

    category = BoardCategory(
        name=data.name,
        slug=data.slug,
        color=data.color,
        order_index=data.order_index,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: UUID,
    data: CategoryUpdate,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """게시판 카테고리 수정 (인증 필수)"""
    # TODO: 관리자 권한 확인

    result = await db.execute(select(BoardCategory).where(BoardCategory.id == category_id))
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(404, "Category not found")

    if data.name:
        category.name = data.name
    if data.slug:
        category.slug = data.slug
    if data.color:
        category.color = data.color
    if data.order_index is not None:
        category.order_index = data.order_index
    if data.is_active is not None:
        category.is_active = data.is_active

    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: UUID,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """게시판 카테고리 삭제 (인증 필수)"""
    # TODO: 관리자 권한 확인

    result = await db.execute(select(BoardCategory).where(BoardCategory.id == category_id))
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(404, "Category not found")

    await db.delete(category)
    await db.commit()
