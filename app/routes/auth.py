from fastapi import FastAPI, APIRouter,Request,Form
from fastapi.responses import  HTMLResponse,RedirectResponse
from fastapi.templating import Jinja2Templates
from app.db import get_connection
from passlib.context import CryptContext

templates = Jinja2Templates(directory="app/templates")
router=APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.get('/login', response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.get('/dashboard', response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@router.post('/login')
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Fetch user by email
        cursor.execute("SELECT password_hash FROM inv_users WHERE email = ?", (email,))
        result = cursor.fetchone()

        if result:
            db_password_hash = result[0]
            # Verify password
            if pwd_context.verify(password, db_password_hash):
                request.session["user"] = email

                return RedirectResponse(url="/dashboard", status_code=303)
            print(request.session)
        # If no match or password invalid
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
