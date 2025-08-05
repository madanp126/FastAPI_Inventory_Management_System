from fastapi import FastAPI, APIRouter,Request,Form,Depends,status
from fastapi.responses import RedirectResponse
from app.db import get_connection
from passlib.context import CryptContext
from app.routes.dashboard import templates

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router=APIRouter()

@router.get('/test')
def user_test():
    return {'message': 'User router is working'}

@router.post('/logout')
def logout(request: Request):
    request.session.clear()
    return templates.TemplateResponse('userProfile.html')

@router.post('/profile')
def profile(request: Request):
    email = request.session.get('user')
    if not email:
        return RedirectResponse('/auth/login',status_code=303)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("select user_firstname, user_lastname, email from inv_users where email = ? and is_active=1", (email,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    user = {
        'name': f"{row[0]} {row[1]}",
        'email': row[2],
    }

    return templates.TemplateResponse('userProfile.html',{"user_profile": user,"request":request})

@router.post('/changePassword')
def change_password(request: Request,
                    current_password: str= Form(...),
                    new_password: str= Form(...),
                    ):
    print("change_password hit",current_password,new_password)
    email = request.session.get('user')
    if not email:
        return RedirectResponse('/auth/login',status_code=303)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("select password_hash,user_id from inv_users where email = ? and is_active=1", (email,))
    row = cursor.fetchone()
    user_id=row[1]

    if not row or not pwd_context.verify(current_password, row[0]):
        return RedirectResponse('/profile?error=invalid',status_code=303)
    new_password_hash = pwd_context.hash(new_password)
    cursor.execute("""
                    UPDATE inv_users set password_hash = ? where email = ? and user_id=? and is_active = 1
    """, (new_password_hash, email,user_id))

    cursor.close()
    conn.close()
    return RedirectResponse(url="/profile",status_code=303)



