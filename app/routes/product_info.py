from unittest import result

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from datetime import datetime
from uvicorn import logging

from app.db import get_connection

router = APIRouter()

@router.post("/add")

async def add_product(
    request: Request,
    product_name: str = Form(...),
    category: str = Form(...),
    price: float = Form(...),
    quantity: int = Form(...),
    inserted_by: int = Form(None)  # optional fallback
):
    print("🟢 This route was hit!")
    conn = get_connection()
    cursor = conn.cursor()

    try:
        user_email = request.session.get("user")
        user_id = None

        if user_email:
            cursor.execute("SELECT user_id FROM inv_users WHERE is_active=1 and email = ?", (user_email,))
            result = cursor.fetchone()
            if result:
                user_id = result[0]

        if not user_id and inserted_by is not None:
            user_id = inserted_by

        if not user_id:
            raise Exception("User ID not found (session or form)")

        cursor.execute("""
            INSERT INTO inv_products (
                product_name, 
                category, 
                quantity, 
                price,
                inserted_by,
                is_sold,
                is_active,
                inserted_date
            ) VALUES (?, ?, ?, ?, ?, 0, 1, GETDATE())
        """, (
            product_name,
            category,
            quantity,
            price,
            user_id
        ))

        conn.commit()
        return RedirectResponse(url="/dashboard", status_code=303)

    except Exception as e:
        print("❌ Error adding product:", repr(e))
        conn.rollback()
        return RedirectResponse(url="/dashboard?error=product_add_failed", status_code=303)

    finally:
        cursor.close()
        conn.close()

@router.post("/restock")
async def restock_product(
        request: Request,
        product_id: int = Form(...),
        product_name: str = Form(...),
        category: str = Form(...),
        quantity: int = Form(...),
        price: float = Form(...),
        updated_by: int = Form(None)
):
    print("<UNK> This route was hit!")
    conn = get_connection()
    cursor = conn.cursor()
    try:
        user_email = request.session.get("user")
        user_id = None
        if user_email:
            cursor.execute("SELECT user_id FROM inv_users WHERE is_active=1 and email = ?", (user_email,))
            result = cursor.fetchone()
            if result:
                user_id = result[0]
        if not user_id and updated_by is not None:
                user_id = updated_by

        if not user_id:
            raise Exception("User ID not found (session or form)")
        cursor.execute(""" Update inv_products
                                SET product_name=?,
                                category=?,
                                quantity=?,
                                price=?,
                                inserted_date=GetDate(),
                                is_sold = 0,
                                updated_by=? WHERE product_id = ? """,
                       (product_name,category,quantity,price,user_id, product_id))

        # log record
        cursor.execute("""
            INSERT INTO inv_restock_records (product_name, category, quantity, price, inserted_date, inserted_by)
            VALUES (?, ?, ?, ?, GETDATE(), ?)
        """, (product_name, category, quantity, price, user_id))

        conn.commit()
        return RedirectResponse(url="/dashboard?updated=1", status_code=303)

    except Exception as e:
        print("<UNK> Error restocking product:", repr(e))
        conn.rollback()
        return RedirectResponse(url="/dashboard", status_code=303)
    finally:
        cursor.close()
        conn.close()



@router.post("/sell")
async def sell_product(
        request: Request,
        product_id: int = Form(...),
        inserted_by: int = Form(None)
):
    print("<UNK>  sell route was hit!")
    conn = get_connection()
    cursor = conn.cursor()
    try:
        user_email = request.session.get("user")
        user_id = None
        if user_email:
            cursor.execute("SELECT user_id FROM inv_users WHERE is_active=1 and email = ?", (user_email,))
            result = cursor.fetchone()
            if result:
                user_id = result[0]
        if not user_id and inserted_by is not None:
                user_id = inserted_by

        if not user_id:
            raise Exception("User ID not found (session or form)")
        cursor.execute("""
            UPDATE inv_products
            SET is_sold = 1,
                is_active= 0,
                updated_by = ?,
                inserted_date = GETDATE()
            WHERE is_sold=0 and product_id = ?
        """, (user_id, product_id))

        # log record
        cursor.execute("""
            INSERT INTO inv_sale_transaction (product_name, category, quantity, price, inserted_by, inserted_date)
            SELECT product_name, category, quantity, price, ?, GETDATE()
            FROM inv_products
            WHERE is_sold=1 and product_id = ?
        """, (user_id, product_id))

        conn.commit()
        return RedirectResponse(url="/dashboard?sold=1", status_code=303)

    except Exception as e:
        print("<UNK> Error selling product:", repr(e))
        conn.rollback()
        return RedirectResponse(url="/dashboard", status_code=303)
    finally:
        cursor.close()
        conn.close()



