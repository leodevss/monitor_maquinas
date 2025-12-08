from sqlalchemy import Column, BigInteger, String, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from database import Base

class Machine(Base):
    __tablename__ = "machines"

    id = Column(BigInteger, primary_key=True, index=True)
    hostname = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), server_default=func.now())

    metrics = relationship("Metric", back_populates="machine")


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(BigInteger, primary_key=True, index=True)
    machine_id = Column(BigInteger, ForeignKey("machines.id"))
    cpu_percent = Column(Float)
    ram_percent = Column(Float)
    ts = Column(DateTime(timezone=True), server_default=func.now())

    machine = relationship("Machine", back_populates="metrics")
