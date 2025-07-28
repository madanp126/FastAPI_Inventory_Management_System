from fastapi import FastAPI, APIRouter,Request,Form ,Response
from fastapi.responses import  HTMLResponse,RedirectResponse
from fastapi.templating import Jinja2Templates
from app.db import get_connection
from passlib.context import CryptContext
from ..utils.jwt import create_access_token

templates = Jinja2Templates(directory="app/templates")
router=APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.get('/login', response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post('/login')
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT user_id, password_hash FROM inv_users WHERE email = ?", (email,))
        result = cursor.fetchone()

        if result:
            user_id, db_password_hash = result

            if pwd_context.verify(password, db_password_hash):
                token_data = {"sub": email, "user_id": user_id}
                token = create_access_token(token_data)

                request.session["user"] = email
                request.session["token"] = token
                print("Generated JWT Token:", token)

                return RedirectResponse(url="/dashboard", status_code=303)

        # Invalid login
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid email or password"
        })

    except Exception as e:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": f"Login failed: {str(e)}"
        })
    finally:
        cursor.close()
        conn.close()


@router.get('/signup', response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@router.post("/signup")
async def signup(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    print ( " debugger hit on signup")
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Check if email already exists
        cursor.execute("SELECT 1 FROM inv_users WHERE email = ?", (email,))
        if cursor.fetchone():
            return templates.TemplateResponse("signup.html", {
                "request": request,
                "error": "Email is already registered. Please try another email."
            })

        # Hash password
        password_hash = pwd_context.hash(password)

        # Insert new user
        cursor.execute("""
            INSERT INTO inv_users (user_firstname, user_lastname, email, password_hash)
            VALUES (?, ?, ?, ?)
        """, (first_name,last_name, email, password_hash))

        conn.commit()

        return RedirectResponse("/auth/login", status_code=303)

    except Exception as e:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": f"Signup failed: {str(e)}"
        })
    finally:
        cursor.close()
        conn.close()