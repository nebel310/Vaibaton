from datetime import datetime, timezone
from sqlalchemy import ForeignKey, DateTime, Integer, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Model




class RoleOrm(Model):
    __tablename__ = 'roles'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class UserOrm(Model):
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str]
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    hashed_password: Mapped[str]
    is_confirmed: Mapped[bool] = mapped_column(default=False)
    role_id: Mapped[int] = mapped_column(ForeignKey('roles.id'), default=1)  # По умолчанию обычный пользователь
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class RefreshTokenOrm(Model):
    __tablename__ = 'refresh_tokens'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    token: Mapped[str] = mapped_column(unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class BlacklistedTokenOrm(Model):
    __tablename__ = 'blacklisted_tokens'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))



class EventOrm(Model):
    __tablename__ = 'events'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    description: Mapped[str] = mapped_column(Text)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    current_participants: Mapped[int] = mapped_column(default=0)
    max_participants: Mapped[int]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class UserEventOrm(Model):
    __tablename__ = 'user_events'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    event_id: Mapped[int] = mapped_column(ForeignKey('events.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Связи
    user: Mapped["UserOrm"] = relationship(backref="user_events")
    event: Mapped["EventOrm"] = relationship(backref="event_users")