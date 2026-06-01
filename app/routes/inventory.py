from fastapi import APIRouter
from passlib.apps import custom_app_context

from app.db import get_connection

router=APIRouter()



@router.get('/Out_Of_Stock_Alert')
async def out_of_stock_alert():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("EXEC SP_INV_Get_Out_Of_Stock_Products")

    rows = cursor.fetchall()

    data = []

    for row in rows:
        data.append({
            "product_name": row.product_name,
            "category": row.category,
            "quantity": row.quantity
        })

    return data