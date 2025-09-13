import uvicorn
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import create_tables, delete_tables
from router.auth import router as auth_router
from models.auth import RoleOrm, UserOrm, EventOrm
from database import new_session
from sqlalchemy import select
from passlib.context import CryptContext
from datetime import datetime, timezone, timedelta

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await delete_tables()
    print('База очищена')
    await create_tables()
    print('База готова к работе')
    
    # Создаем стандартные роли и тестовые данные
    async with new_session() as session:
        # Проверяем, существуют ли уже роли
        result = await session.execute(select(RoleOrm))
        existing_roles = result.scalars().all()
        
        if not existing_roles:
            # Создаем стандартные роли
            user_role = RoleOrm(name="user")
            admin_role = RoleOrm(name="admin")
            
            session.add(user_role)
            session.add(admin_role)
            await session.flush()
            
            # Создаем тестового пользователя
            hashed_password = pwd_context.hash("testpassword")
            test_user = UserOrm(
                username="testuser",
                email="test@example.com",
                hashed_password=hashed_password,
                role_id=user_role.id
            )
            
            admin_user = UserOrm(
                username="admin",
                email="admin@example.com",
                hashed_password=pwd_context.hash("adminpassword"),
                role_id=admin_role.id
            )
            
            session.add(test_user)
            session.add(admin_user)
            await session.flush()
            
            # Создаем тестовые мероприятия
            now = datetime.now(timezone.utc)
            events = [
                EventOrm(
                    title="Хакатон Vaibaton",
                    description="Крутой хакатон с призами и возможностью проявить себя",
                    start_time=now + timedelta(hours=2),
                    end_time=now + timedelta(days=2),
                    current_participants=0,
                    max_participants=100,
                    is_active=True
                ),
                EventOrm(
                    title="Мастер-класс по FastAPI",
                    description="Научимся создавать API на FastAPI",
                    start_time=now + timedelta(days=1),
                    end_time=now + timedelta(days=1, hours=3),
                    current_participants=0,
                    max_participants=30,
                    is_active=True
                ),
                EventOrm(
                    title="Воркшоп по Docker",
                    description="Узнаем как контейнеризировать приложения",
                    start_time=now + timedelta(days=3),
                    end_time=now + timedelta(days=3, hours=4),
                    current_participants=0,
                    max_participants=25,
                    is_active=True
                )
            ]
            
            for event in events:
                session.add(event)
            
            await session.commit()
            print('Тестовые данные созданы')
    
    yield
    print('Выключение')


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Your App",
        version="1.0.0",
        description="Base nebel's FastApi template with JWT Auth",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    
    secured_paths = {
        # Авторизация
        "/auth/me": {"method": "get", "security": [{"Bearer": []}]},
        "/auth/logout": {"method": "post", "security": [{"Bearer": []}]},
        
        # Мероприятия - добавляем новые защищенные пути
        "/auth/events": {
            "method": "post", 
            "security": [{"Bearer": []}]
        },
        "/auth/events": {
            "method": "get", 
            "security": [{"Bearer": []}]
        },
        "/auth/events/{event_id}/register": {
            "method": "post", 
            "security": [{"Bearer": []}]
        },
        "/auth/events/{event_id}/cancel": {
            "method": "post", 
            "security": [{"Bearer": []}]
        },
        "/auth/my-events": {
            "method": "get", 
            "security": [{"Bearer": []}]
        }
    }
    
    for path, config in secured_paths.items():
        if path in openapi_schema["paths"]:
            openapi_schema["paths"][path][config["method"]]["security"] = config["security"]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app = FastAPI(lifespan=lifespan)
app.openapi = custom_openapi
app.include_router(auth_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500"],  # Тут адрес фронтенда
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



#Раскоментить, когда будешь писать докер.
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host='0.0.0.0',
        port=3001,
        reload=True,
    )