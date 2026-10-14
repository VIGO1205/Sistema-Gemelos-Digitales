from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base


class ActiveModel(Base):
    """Modelo activo persistido por el Motor IA para cada banco.
    
    Tabla creada por schema_models.sql del Motor IA.
    """
    __tablename__ = "active_models"

    id = Column(Integer, primary_key=True, index=True)
    bench = Column(Integer, nullable=False, unique=True, index=True)
    model_name = Column(String(50), nullable=False)
    composite_score = Column(Float, nullable=True)
    rmse = Column(Float, nullable=True)
    r2 = Column(Float, nullable=True)
    mae = Column(Float, nullable=True)
    mape = Column(Float, nullable=True)
    bias = Column(Float, nullable=True)
    activated_at = Column(DateTime(timezone=False), server_default=func.now())
    deactivated_at = Column(DateTime(timezone=False), nullable=True)
    is_current = Column(Boolean, default=True)
