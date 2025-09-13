from fastapi import APIRouter, Depends, HTTPException, Query
from schemas.auth import SUserRegister, SUserLogin, SUser, SEventCreate, SEvent, SEventWithUsers
from repositories.auth import UserRepository, EventRepository
from models.auth import UserOrm
from utils.security import create_access_token, get_current_user, oauth2_scheme
from typing import List




router = APIRouter(
    prefix="/auth",
    tags=['Пользователи']
)


@router.post("/register")
async def register_user(user_data: SUserRegister):
    try:
        user_id = await UserRepository.register_user(user_data)
        return {"success": True, "user_id": user_id, "message": "Подтверждение почты отправлено"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
async def login_user(login_data: SUserLogin):
    user = await UserRepository.authenticate_user(login_data.email, login_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Неверный email или пароль")
    
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = await UserRepository.create_refresh_token(user.id)
    return {"success": True, "message": "Вы вошли в аккаунт", "access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/refresh")
async def refresh_token(refresh_token: str):
    user = await UserRepository.get_user_by_refresh_token(refresh_token)
    if not user:
        raise HTTPException(status_code=400, detail="Неверный refresh токен")
    
    new_access_token = create_access_token(data={"sub": user.email})
    return {"access_token": new_access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(token: str = Depends(oauth2_scheme), current_user: UserOrm = Depends(get_current_user)):
    await UserRepository.add_to_blacklist(token)
    await UserRepository.revoke_refresh_token(current_user.id)
    return {"success": True}


@router.get("/me", response_model=SUser)
async def get_current_user_info(current_user: UserOrm = Depends(get_current_user)):
    return SUser.model_validate(current_user)


@router.post("/events", response_model=SEvent)
async def create_event(event_data: SEventCreate, current_user: UserOrm = Depends(get_current_user)):
    # Проверяем, является ли пользователь администратором
    if current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    event_id = await EventRepository.create_event(event_data)
    event = await EventRepository.get_event_by_id(event_id)
    return event

@router.get("/events", response_model=List[SEvent])
async def get_events(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: UserOrm = Depends(get_current_user)
):
    events = await EventRepository.get_all_events(offset, limit, current_user.id)
    return events

@router.post("/events/{event_id}/register")
async def register_for_event(event_id: int, current_user: UserOrm = Depends(get_current_user)):
    success = await EventRepository.register_for_event(current_user.id, event_id)
    if not success:
        raise HTTPException(status_code=400, detail="Не удалось зарегистрироваться на мероприятие")
    return {"success": True, "message": "Вы успешно зарегистрировались на мероприятие"}

@router.post("/events/{event_id}/cancel")
async def cancel_registration(event_id: int, current_user: UserOrm = Depends(get_current_user)):
    success = await EventRepository.cancel_registration(current_user.id, event_id)
    if not success:
        raise HTTPException(status_code=400, detail="Не удалось отменить регистрацию")
    return {"success": True, "message": "Регистрация на мероприятие отменена"}

@router.get("/my-events", response_model=List[SEvent])
async def get_my_events(current_user: UserOrm = Depends(get_current_user)):
    events = await EventRepository.get_user_events(current_user.id)
    return events