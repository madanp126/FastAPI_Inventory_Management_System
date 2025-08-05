from unittest import result

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse,StreamingResponse
from datetime import datetime,date

from flask import request
from html2image import Html2Image
from jinja2 import Template

from starlette.responses import StreamingResponse
from uvicorn import logging
from app.db import get_connection
import io
import os

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
    sell_quantity: int = Form(...),
    inserted_by: int = Form(None)
):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        user_email = request.session.get("user")
        user_id = None

        # Get user ID from session or fallback to inserted_by
        if user_email:
            cursor.execute("SELECT user_id FROM inv_users WHERE is_active = 1 AND email = ?", (user_email,))
            result = cursor.fetchone()
            if result:
                user_id = result[0]

        if not user_id and inserted_by is not None:
            user_id = inserted_by

        if not user_id:
            raise Exception("User ID not found (session or form)")

        # Fetch current stock
        cursor.execute("SELECT product_name, category, quantity, price FROM inv_products WHERE product_id = ? AND is_active = 1", (product_id,))
        product = cursor.fetchone()
        print("product ID:", product[0])

        if not product:
            raise Exception("Product not found or inactive")

        product_name, category, current_quantity, price = product

        if sell_quantity > current_quantity:
            raise Exception("Sell quantity exceeds available stock")

        remaining_quantity = current_quantity - sell_quantity

        if remaining_quantity == 0:
            # Mark product as sold and inactive
            cursor.execute("""
                UPDATE inv_products
                SET quantity = 0,
                    is_sold = 1,
                    is_active = 0,
                    updated_by = ?,
                    inserted_date = GETDATE()
                WHERE product_id = ?
            """, (user_id, product_id))
        else:
            # Only update quantity
            cursor.execute("""
                UPDATE inv_products
                SET quantity = ?,
                    updated_by = ?,
                    inserted_date = GETDATE()
                WHERE product_id = ?
            """, (remaining_quantity, user_id, product_id))

        # Insert into transaction log
        print("inv_products updated")
        cursor.execute("""
            INSERT INTO inv_sale_transaction (product_id, product_name, category, quantity, price, inserted_by, inserted_date)
            VALUES (?, ?, ?, ?, ?, ?, GETDATE())
        """, (product_id, product_name, category, sell_quantity, price, user_id))

        conn.commit()
        return RedirectResponse(url="/dashboard?sold=1", status_code=303)

    except Exception as e:
        print("[ERROR] sell_product:", repr(e))
        conn.rollback()
        return RedirectResponse(url="/dashboard?error=1", status_code=303)

    finally:
        cursor.close()
        conn.close()

@router.post("/generate_bill")
async def generate_bill(
        request: Request,
        product_name: str = Form(...),
    category: str = Form(...),
    quantity: int = Form(...),
    price: float = Form(...)
, customer_email=None):
    # 1. Get user email from session
    user_email = request.session.get("user")
    customer_name = "Customer"  # default fallback

    if user_email:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT user_firstname,user_lastname,email FROM inv_users WHERE email = ? AND is_active = 1", (user_email,))
            row = cursor.fetchone()
            if row:
                customer_name = row[0]+" "+row[1]
                customer_email = row[2]
        finally:
            cursor.close()
            conn.close()

    total_price = quantity * price

    product_data = {
        "customer": customer_name,  # Can be dynamic later
        "customer_email": customer_email,
        "date": date.today().strftime("%d-%m-%Y"),
        "items": [
            {"name": product_name, "qty": quantity, "price": price}
        ],
        "total": total_price
    }

    html_template = """
      <html>
        <head>
          <style>
            body { font-family: Arial; padding: 30px; }
            h2 { text-align: center; color: #333; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { border: 1px solid #aaa; padding: 10px; text-align: left; }
            th { background-color: #f2f2f2; }
          </style>
        </head>
        <body>
          <h2>Invoice</h2>
          <p><strong>Customer:</strong> {{ customer }}</p>
          <p><strong>Customer:</strong> {{ customer_email }}</p>
          <p><strong>Date:</strong> {{ date }}</p>

          <table>
            <tr>
              <th>Sr.No.</th>
              <th>Product</th>
              <th>Qty</th>
              <th>Price</th>
              <th>Total</th>
            </tr>
            {% for item in items %}
            <tr>
              <td>{{ loop.index }}</td>
              <td>{{ item.name }}</td>
              <td>{{ item.qty }}</td>
              <td>₹{{ item.price }}</td>
              <td>₹{{ item.qty * item.price }}</td>
            </tr>
            {% endfor %}
          </table>

          <h3 style="text-align:right;">Total: ₹{{ total }}</h3>
        </body>
      </html>
      """

    rendered_html = Template(html_template).render(**product_data)

    # Generate PNG from HTML
    hti = Html2Image()
    temp_image_path = "bill_image.png"
    hti.screenshot(html_str=rendered_html, save_as=temp_image_path)

    with open(temp_image_path, "rb") as f:
        image_bytes = f.read()
    os.remove(temp_image_path)

    return StreamingResponse(io.BytesIO(image_bytes), media_type="image/png")






