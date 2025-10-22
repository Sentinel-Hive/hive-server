from __future__ import annotations
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint, func, JSON

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    salt_hex: Mapped[str] = mapped_column(String(64))
    pass_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    tokens: Mapped[list["AuthToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

class AuthToken(Base):
    __tablename__ = "auth_tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id_fk: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    issued_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    revoked_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="tokens")
    __table_args__ = (UniqueConstraint("token", name="uq_auth_tokens_token"),)

class Event(Base):
    """
    Generic event table for all types of network/security/application events.
    Further expand next sprint with better idea of exactly what we want to log/store for analytics/alerts.
    """
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(100), nullable=False, index=True)
    timestamp = Column(DateTime, default=func.now(), nullable=False, index=True)
    source = Column(String(100), nullable=True, index=True)
    details = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<Event(id={self.id}, type='{self.event_type}', timestamp='{self.timestamp}')>"

class DataStore(Base):
    __tablename__ = "data_store"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
