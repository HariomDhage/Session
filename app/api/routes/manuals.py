"""Manual API routes."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.manual import ManualCreate, ManualResponse, ManualListResponse
from app.services.manual_service import ManualService
from app.utils.exceptions import SessionServiceException

router = APIRouter()


@router.post(
    "",
    response_model=ManualResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new manual",
    description="Create a new instruction manual with steps. Steps must be sequential starting from 1.",
)
async def create_manual(
    manual_data: ManualCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new instruction manual.

    - **manual_id**: Unique identifier for the manual
    - **title**: Title of the manual
    - **steps**: List of steps (each with step_number, title, content)

    Example:
    ```json
    {
      "manual_id": "manual-abc",
      "title": "Introduction to Python",
      "steps": [
        {"step_number": 1, "title": "Hello, World!", "content": "Write a script that prints Hello, World!"},
        {"step_number": 2, "title": "Variables", "content": "Declare a variable and assign it a value."}
      ]
    }
    ```
    """
    try:
        service = ManualService(db)
        manual = await service.create_manual(manual_data)
        return service.to_response(manual)
    except SessionServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get(
    "",
    response_model=ManualListResponse,
    summary="List all manuals",
    description="Get a paginated list of all instruction manuals.",
)
async def list_manuals(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    db: AsyncSession = Depends(get_db)
):
    """List all manuals with pagination."""
    service = ManualService(db)
    manuals, total = await service.list_manuals(skip=skip, limit=limit)
    return ManualListResponse(
        manuals=[service.to_response(m) for m in manuals],
        total=total
    )


@router.get(
    "/{manual_id}",
    response_model=ManualResponse,
    summary="Get a manual",
    description="Get details of a specific instruction manual by its ID.",
)
async def get_manual(
    manual_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific manual by ID."""
    try:
        service = ManualService(db)
        manual = await service.get_manual_by_id(manual_id)
        return service.to_response(manual)
    except SessionServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.delete(
    "/{manual_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a manual",
    description="Delete an instruction manual. This will fail if there are active sessions using this manual.",
)
async def delete_manual(
    manual_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a manual by ID."""
    try:
        service = ManualService(db)
        await service.delete_manual(manual_id)
    except SessionServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
