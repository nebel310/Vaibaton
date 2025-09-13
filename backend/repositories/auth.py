import os
from dotenv import load_dotenv
from database import new_session
from models.auth import UserOrm, RefreshTokenOrm, BlacklistedTokenOrm, RoleOrm, EventOrm, UserEventOrm
from schemas.auth import SUserRegister, SEventCreate
from sqlalchemy import select, delete, func, and_, or_
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timezone, timedelta
from typing import List




load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS'))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserRepository:
    @classmethod
    async def register_user(cls, user_data: SUserRegister) -> int:
        async with new_session() as session:
            query = select(UserOrm).where(UserOrm.email == user_data.email)
            result = await session.execute(query)
            if result.scalars().first():
                raise ValueError("Пользователь с таким email уже существует")
              
            hashed_password = pwd_context.hash(user_data.password)
            
            user = UserOrm(
                username=user_data.username,
                email=user_data.email,
                hashed_password=hashed_password
            )
            session.add(user)
            await session.flush()
            await session.commit()
            return user.id
    
    @classmethod
    async def authenticate_user(cls, email: str, password: str) -> UserOrm | None:
        async with new_session() as session:
            # Добавляем join с таблицей ролей
            query = select(UserOrm).join(RoleOrm).where(UserOrm.email == email)
            result = await session.execute(query)
            user = result.scalars().first()
            
            if not user or not pwd_context.verify(password, user.hashed_password):
                return None
            
            return user
    
    @classmethod
    async def get_user_by_email(cls, email: str) -> UserOrm | None:
        async with new_session() as session:
            # Добавляем join с таблицей ролей
            query = select(UserOrm).join(RoleOrm).where(UserOrm.email == email)
            result = await session.execute(query)
            return result.scalars().first()
    
    @classmethod
    async def get_user_by_id(cls, user_id: int) -> UserOrm | None:
        async with new_session() as session:
            # Добавляем join с таблицей ролей
            query = select(UserOrm).join(RoleOrm).where(UserOrm.id == user_id)
            result = await session.execute(query)
            return result.scalars().first()
    
    @classmethod
    async def get_user_by_refresh_token(cls, refresh_token: str) -> UserOrm | None:
        async with new_session() as session:
            query = select(RefreshTokenOrm).where(RefreshTokenOrm.token == refresh_token)
            result = await session.execute(query)
            refresh_token_orm = result.scalars().first()
            
            if not refresh_token_orm or refresh_token_orm.expires_at < datetime.now(timezone.utc):
                return None
            
            return await cls.get_user_by_id(refresh_token_orm.user_id)
    
    @classmethod
    async def create_refresh_token(cls, user_id: int) -> str:
        async with new_session() as session:
            # Удаляем старый refresh токен пользователя, если он существует
            delete_query = delete(RefreshTokenOrm).where(RefreshTokenOrm.user_id == user_id)
            await session.execute(delete_query)
            
            # Создаем новый refresh токен
            refresh_token = jwt.encode({"sub": str(user_id)}, SECRET_KEY, algorithm=ALGORITHM)
            expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
            
            refresh_token_orm = RefreshTokenOrm(
                user_id=user_id,
                token=refresh_token,
                expires_at=expires_at
            )
            session.add(refresh_token_orm)
            await session.commit()
            return refresh_token

    @classmethod
    async def revoke_refresh_token(cls, user_id: int):
        async with new_session() as session:
            query = delete(RefreshTokenOrm).where(RefreshTokenOrm.user_id == user_id)
            await session.execute(query)
            await session.commit()

    @classmethod
    async def add_to_blacklist(cls, token: str):
        async with new_session() as session:
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
            except JWTError:
                return

            blacklisted_token = BlacklistedTokenOrm(
                token=token,
                expires_at=expires_at,
                created_at=datetime.now(timezone.utc)
            )
            session.add(blacklisted_token)
            await session.commit()



class EventRepository:
    @classmethod
    async def create_event(cls, event_data: SEventCreate) -> int:
        async with new_session() as session:
            event = EventOrm(**event_data.model_dump())
            session.add(event)
            await session.flush()
            await session.commit()
            return event.id
    
    @classmethod
    async def get_all_events(cls, offset: int = 0, limit: int = 10, user_id: int = None) -> List[EventOrm]:
        async with new_session() as session:
            query = select(EventOrm)
            
            if user_id is not None:
                # Добавляем флаг, зарегистрирован ли пользователь на мероприятие
                query = query.add_columns(
                    select(UserEventOrm.id)
                    .where(and_(
                        UserEventOrm.user_id == user_id,
                        UserEventOrm.event_id == EventOrm.id
                    ))
                    .exists()
                    .label("is_user_registered")
                )
            
            query = query.offset(offset).limit(limit).order_by(EventOrm.created_at.desc())
            result = await session.execute(query)
            
            if user_id is not None:
                events = []
                for event, is_registered in result:
                    event.is_user_registered = is_registered
                    events.append(event)
                return events
            else:
                return result.scalars().all()
    
    @classmethod
    async def get_event_by_id(cls, event_id: int, user_id: int = None) -> EventOrm:
        async with new_session() as session:
            query = select(EventOrm).where(EventOrm.id == event_id)
            
            if user_id is not None:
                query = query.add_columns(
                    select(UserEventOrm.id)
                    .where(and_(
                        UserEventOrm.user_id == user_id,
                        UserEventOrm.event_id == event_id
                    ))
                    .exists()
                    .label("is_user_registered")
                )
            
            result = await session.execute(query)
            
            if user_id is not None:
                event, is_registered = result.first()
                if event:
                    event.is_user_registered = is_registered
                return event
            else:
                return result.scalars().first()
    
    @classmethod
    async def register_for_event(cls, user_id: int, event_id: int) -> bool:
        async with new_session() as session:
            # Проверяем, существует ли мероприятие
            event = await cls.get_event_by_id(event_id)
            if not event or not event.is_active or event.current_participants >= event.max_participants:
                return False
            
            # Проверяем, не зарегистрирован ли уже пользователь
            existing_registration = await session.execute(
                select(UserEventOrm).where(and_(
                    UserEventOrm.user_id == user_id,
                    UserEventOrm.event_id == event_id
                ))
            )
            
            if existing_registration.scalars().first():
                return False
            
            # Регистрируем пользователя
            user_event = UserEventOrm(user_id=user_id, event_id=event_id)
            session.add(user_event)
            
            # Увеличиваем счетчик участников
            event.current_participants += 1
            await session.commit()
            return True
    
    @classmethod
    async def cancel_registration(cls, user_id: int, event_id: int) -> bool:
        async with new_session() as session:
            # Находим регистрацию
            registration = await session.execute(
                select(UserEventOrm).where(and_(
                    UserEventOrm.user_id == user_id,
                    UserEventOrm.event_id == event_id
                ))
            )
            registration = registration.scalars().first()
            
            if not registration:
                return False
            
            # Удаляем регистрацию
            await session.delete(registration)
            
            # Уменьшаем счетчик участников
            event = await cls.get_event_by_id(event_id)
            if event:
                event.current_participants -= 1
                if event.current_participants < 0:
                    event.current_participants = 0
            
            await session.commit()
            return True
    
    @classmethod
    async def get_user_events(cls, user_id: int) -> List[EventOrm]:
        async with new_session() as session:
            query = select(EventOrm).join(UserEventOrm).where(UserEventOrm.user_id == user_id)
            result = await session.execute(query)
            return result.scalars().all()