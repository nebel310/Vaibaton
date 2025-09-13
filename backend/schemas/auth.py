from pydantic import BaseModel, ConfigDict, EmailStr
from datetime import datetime
from typing import Optional, List

class SRole(BaseModel):
    id: int
    name: str
    
    model_config = ConfigDict(from_attributes=True)

class SUserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    password_confirm: str

class SUserLogin(BaseModel):
    email: EmailStr
    password: str

class SUser(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: SRole  # Добавляем информацию о роли
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)



class SEventBase(BaseModel):
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    max_participants: int

class SEventCreate(SEventBase):
    pass

class SEvent(SEventBase):
    id: int
    current_participants: int
    is_active: bool
    created_at: datetime
    is_user_registered: Optional[bool] = False  # Флаг, зарегистрирован ли текущий пользователь
    
    model_config = ConfigDict(from_attributes=True)

class SEventWithUsers(SEvent):
    participants: List[SUser]
    
    model_config = ConfigDict(from_attributes=True)

class SUserEvent(BaseModel):
    id: int
    user_id: int
    event_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)