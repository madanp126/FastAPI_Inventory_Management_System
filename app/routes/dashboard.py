from fastapi import APIRouter, Request ,Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from starlette.responses import RedirectResponse

from app.db import get_connection

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request,updated : int = Query(0)):
    user = request.session.get("user")

    if not user:
        return RedirectResponse("/auth/login", status_code=303)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT TOP 10 product_id,product_name, category, quantity, price,
                CASE WHEN quantity > 0 THEN 'In Stock' ELSE 'Out of Stock' END as status
            FROM inv_products where is_active =1
            ORDER BY inserted_date DESC
        """)
        rows = cursor.fetchall()

        recent_products = [
            {
                "product_id":row[0],
                "product_name": row[1],
                "category": row[2],
                "quantity": row[3],
                "price": row[4],
                "status": row[5]
            }
            for row in rows
        ]
        cursor.execute("""
                 SELECT TOP 10 sale_transaction_id,product_name, category, quantity, price,
                     CASE WHEN quantity > 0 THEN 'In Stock' ELSE 'Out of Stock' END as status
                 FROM inv_sale_transaction where is_active =1 and is_sold=1
                 ORDER BY inserted_date DESC
             """)
        rows = cursor.fetchall()

        sold_products = [
            {
                "product_id": row[0],
                "product_name": row[1],
                "category": row[2],
                "quantity": row[3],
                "price": row[4],
                "status": row[5]

            }
            for row in rows
        ]

    except Exception as e:
        print("Error fetching products:", e)
        recent_products = []
        sold_products = []
    finally:
        cursor.close()
        conn.close()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "recent_products": recent_products,
        "updated": updated,
        "sold_products": sold_products,
    })

