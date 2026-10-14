from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import HyperspectralSignature
from app.schemas.hyperspectral import HyperspectralSignatureResponse

router = APIRouter()


@router.get("", response_model=List[HyperspectralSignatureResponse])
async def list_hyperspectral_signatures(project_id: int = None, db: AsyncSession = Depends(get_db)):
    query = select(HyperspectralSignature)
    if project_id:
        query = query.where(HyperspectralSignature.project_id == project_id)
    result = await db.execute(query)
    return result.scalars().all()
