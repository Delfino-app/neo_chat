from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from api.services.indexar_service import indexar_post

router = APIRouter(prefix="/api", tags=["Indexação"])


class IndexarPostPayload(BaseModel):
    id: int
    title: str
    link: str
    autor: str
    conteudo: str
    categoria: str
    data : str
    tags: List[str] = []


@router.post("/indexar")
async def indexar(payload: IndexarPostPayload):
    try:
        logs = indexar_post(payload)
        return {
            "status": "success",
            "post_id": payload.id,
            "logs": logs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
