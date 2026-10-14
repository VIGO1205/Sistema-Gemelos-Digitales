from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"] = Field(..., description="Rol del mensaje")
    content: str = Field(..., description="Contenido del mensaje")


class ChatContext(BaseModel):
    active_bench: Optional[int] = Field(None, description="Banco activo Z")
    selected_block_id: Optional[str] = Field(None, description="ID del bloque seleccionado")
    selected_block_cu: Optional[float] = Field(None, description="Ley Cu del bloque seleccionado")
    selected_block_lithology: Optional[str] = Field(None, description="Litología del bloque seleccionado")
    project_name: Optional[str] = Field(None, description="Nombre del proyecto")
    cut_off_grade: Optional[float] = Field(None, description="Cut-off grade")
    avg_bench_grade: Optional[float] = Field(None, description="Ley promedio del banco")
    total_bench_tonnage: Optional[float] = Field(None, description="Tonelaje total del banco")
    user_role: Optional[str] = Field(None, description="Rol del usuario")
    user_name: Optional[str] = Field(None, description="Nombre del usuario")


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., description="Historial de mensajes de la conversación")
    context: Optional[ChatContext] = Field(None, description="Contexto geológico actual del proyecto")
    session_id: Optional[str] = Field(None, description="ID de sesión para persistencia de memoria en LangFlow")


class ChatResponse(BaseModel):
    message: ChatMessage = Field(..., description="Respuesta del asistente IA")
    model: str = Field(..., description="Modelo utilizado")
