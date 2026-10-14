from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class TrainingLossHistory(Base):
    __tablename__ = "training_loss_history"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)

    epoch = Column(Integer, nullable=False)
    elbo_loss = Column(Float, nullable=False)
    kl_divergence = Column(Float, nullable=False)
    reconstruction_loss = Column(Float, nullable=False)
    val_rmse = Column(Float, nullable=False)
    ece_score = Column(Float, nullable=False)

    project = relationship("Project", back_populates="training_history")
