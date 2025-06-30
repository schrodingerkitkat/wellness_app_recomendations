from fastapi import FastAPI, HTTPException, Path, Depends, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from typing import List, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from pydantic import BaseSettings, Field, validator
import boto3
import json
import jwt
from jwt.exceptions import JWTError
import logging
import uuid
from datetime import datetime, timedelta
import models

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s", "trace_id": "%(trace_id)s"}'
)
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # Secrets Manager ARNs
    database_secret_arn: str = Field(..., env="DATABASE_SECRET_ARN")
    jwt_secret_arn: str = Field(..., env="JWT_SECRET_ARN")
    redis_url: str = Field("redis://localhost:6379", env="REDIS_URL")
    environment: str = Field("development", env="ENVIRONMENT")
    
    class Config:
        env_file = ".env"

settings = Settings()

# AWS Secrets Manager client
secrets_client = boto3.client('secretsmanager')

def get_secret(secret_arn: str) -> dict:
    """Retrieve secret from AWS Secrets Manager"""
    try:
        response = secrets_client.get_secret_value(SecretId=secret_arn)
        return json.loads(response['SecretString'])
    except Exception as e:
        logger.error(f"Failed to retrieve secret {secret_arn}: {str(e)}")
        raise HTTPException(status_code=500, detail="Configuration error")

# Load secrets
db_config = get_secret(settings.database_secret_arn)
jwt_config = get_secret(settings.jwt_secret_arn)

# Database setup
database_url = f"postgresql+asyncpg://{db_config['username']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
database = create_async_engine(database_url, echo=False)
async_session = sessionmaker(database, class_=AsyncSession, expire_on_commit=False)

app = FastAPI(
    title="Wellness App API",
    description="Secure wellness recommendation API",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://wellness-app.com"],  # Restrict to production domains
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# Rate limiting setup
@app.on_event("startup")
async def startup():
    import redis.asyncio as redis
    redis_client = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(redis_client)
    
    # Create database tables
    async with database.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

@app.on_event("shutdown")
async def shutdown():
    await FastAPILimiter.close()
    await database.dispose()

async def get_db_session():
    async with async_session() as session:
        yield session

async def authenticate_user(token: str = Depends(oauth2_scheme)) -> str:
    """Validate JWT token and return user_id"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token, 
            jwt_config['secret_key'], 
            algorithms=[jwt_config['algorithm']]
        )
        user_id: str = payload.get("sub")
        exp: int = payload.get("exp")
        
        if user_id is None or exp is None:
            raise credentials_exception
            
        # Check token expiration
        if datetime.utcnow().timestamp() > exp:
            raise HTTPException(status_code=401, detail="Token expired")
            
        return user_id
    except JWTError as e:
        logger.warning(f"JWT validation failed: {str(e)}", extra={"trace_id": str(uuid.uuid4())})
        raise credentials_exception

@app.get(
    "/user/{user_id}/content/recommendations", 
    response_model=models.RecommendationResponse,
    dependencies=[Depends(RateLimiter(times=100, per=60))]  # 100 requests per minute
)
async def get_content_recommendations(
    user_id: str = Path(..., description="The ID of the user", regex="^[a-zA-Z0-9_-]+$"),
    db_session: AsyncSession = Depends(get_db_session),
    authenticated_user_id: str = Depends(authenticate_user)
):
    """Get personalized content recommendations for a user"""
    trace_id = str(uuid.uuid4())
    logger.info(f"Fetching recommendations for user {user_id}", extra={"trace_id": trace_id})
    
    # Authorization check - users can only access their own data
    if user_id != authenticated_user_id:
        logger.warning(f"Unauthorized access attempt: {authenticated_user_id} tried to access {user_id}", 
                      extra={"trace_id": trace_id})
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    try:
        # Use parameterized query to prevent SQL injection
        query = text("""
            SELECT r.*, c.title, c.category, c.description 
            FROM recommendations r
            JOIN content c ON r.content_id = c.content_id
            WHERE r.user_id = :user_id 
            ORDER BY r.score DESC 
            LIMIT 10
        """)
        
        result = await db_session.execute(query, {"user_id": user_id})
        recommendations = result.fetchall()
        
        if not recommendations:
            logger.info(f"No recommendations found for user {user_id}", extra={"trace_id": trace_id})
            return models.RecommendationResponse(recommendations=[])
        
        # Convert to response model
        content_items = [
            models.ContentItem(
                contentId=rec.content_id,
                title=rec.title,
                contentType=rec.category,
                description=rec.description
            )
            for rec in recommendations
        ]
        
        logger.info(f"Returned {len(content_items)} recommendations for user {user_id}", 
                   extra={"trace_id": trace_id})
        
        return models.RecommendationResponse(recommendations=content_items)
        
    except Exception as e:
        logger.error(f"Database error for user {user_id}: {str(e)}", extra={"trace_id": trace_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Internal server error occurred"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}'
                }
            }
        }
    )