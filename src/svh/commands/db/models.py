
"""
Database models for SentinelHive.

Core tables:
- User: client app users
- ServerAuth: JWT tokens for logged-in users
- Event: generic event table for analytics

The Event table is designed for flexible analytics and can be used 
to power graphs such as requests per user per minute/hour/day, etc.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    """
    Client app users table.
    """
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    userID = Column(String(100), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="user")
    timestamp = Column(DateTime, default=func.now(), nullable=False)

    # Relationship to server auth tokens
    auth_tokens = relationship("ServerAuth", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, userID='{self.userID}', role='{self.role}')>"

class ServerAuth(Base):
    """
    Server authentication table for storing JWT tokens for logged-in users.
    """
    __tablename__ = "server_auth"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    jwt_token = Column(Text, nullable=False)
    login_timestamp = Column(DateTime, default=func.now(), nullable=False)

    user = relationship("User", back_populates="auth_tokens")

    def __repr__(self):
        return f"<ServerAuth(id={self.id}, user_id={self.user_id}, login_timestamp='{self.login_timestamp}')>"

class Event(Base):
    """
    Generic event table for all types of network/security/application events.
    Designed for analytics and flexible event storage (Splunk-like).
    """
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(100), nullable=False, index=True)  # e.g., 'sign_in', 'network', 'alert', etc.
    timestamp = Column(DateTime, default=func.now(), nullable=False, index=True)
    source = Column(String(100), nullable=True, index=True)  # e.g., 'firewall', 'auth', 'proxy', etc.
    details = Column(JSON, nullable=True)  # Flexible event-specific data

    def __repr__(self):
        return f"<Event(id={self.id}, type='{self.event_type}', timestamp='{self.timestamp}')>"
