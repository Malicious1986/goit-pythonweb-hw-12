from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware
from src.api import contacts, utils, users
from src.conf.limiter import register_rate_limit_handler
from src.conf.config import config
import uvicorn


app = FastAPI()
origins = [origin.strip() for origin in config.ORIGINS]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_rate_limit_handler(app)


app.include_router(utils.router, prefix="/api")
app.include_router(contacts.router, prefix="/api")
app.include_router(users.router, prefix="/api")

if __name__ == "__main__":

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
