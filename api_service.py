from fastapi import FastAPI, HTTPException, Path, Depends, status
from fastapi.security import OAuth2PasswordBearer
from typing import List
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from pydantic import BaseSettings
import models  # Assuming models.py contains SQLAlchemy models for our API

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://user:password@localhost/dbname"
    jwt_secret_key: str = "secret-key"
    jwt_algorithm: str = "HS256"

    class Config:
        env_file = ".env"

settings = Settings()

database = create_async_engine(settings.database_url)
async_session = sessionmaker(database, class_=AsyncSession, expire_on_commit=False)

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

async def get_db_session():
    async with async_session() as session:
        yield session

async def authenticate_user(token: str = Depends(oauth2_scheme)):
    # To DO!! authentication logic
    
    if token != "valid_token":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return token

@app.on_event("startup")
async def startup():
    async with database.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

@app.on_event("shutdown")
async def shutdown():
    await database.dispose()

@app.get("/user/{user_id}/content/recommendations", response_model=models.RecommendationResponse)
async def get_content_recommendations(
    user_id: str = Path(..., description="The ID of the user to fetch recommendations for"),
    db_session: AsyncSession = Depends(get_db_session),
    token: str = Depends(authenticate_user)
):
    try:
        query = "SELECT * FROM recommendations WHERE user_id = :user_id"
        result = await db_session.execute(query, {"user_id": user_id})
        recommendation = result.fetchone()
        if not recommendation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return models.RecommendationResponse(**recommendation)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
