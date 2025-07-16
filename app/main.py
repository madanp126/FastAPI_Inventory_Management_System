import secrets

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.routes import auth,user,sale,inventory,dashboard,product_info
from starlette.middleware.sessions import SessionMiddleware


app = FastAPI()
secret_key = secrets.token_hex(16)
app.add_middleware(SessionMiddleware, secret_key=secret_key)

# app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(auth.router,prefix="/auth")
app.include_router(user.router,prefix="/users")
app.include_router(sale.router,prefix="/sales")
app.include_router(inventory.router,prefix="/inventory")
app.include_router(product_info.router,prefix="/product_info")

app.include_router(dashboard.router)


