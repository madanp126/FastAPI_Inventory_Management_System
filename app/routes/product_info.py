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
):

    # Get logged-in user
    user_email = request.session.get("user")

    customer_name = "Customer"
    customer_email = ""

    if user_email:
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT user_firstname,
                       user_lastname,
                       email
                FROM inv_users
                WHERE email = ?
                  AND is_active = 1
            """, (user_email,))

            row = cursor.fetchone()

            if row:
                customer_name = f"{row[0]} {row[1]}"
                customer_email = row[2]

        finally:
            cursor.close()
            conn.close()

    total_price = quantity * price

    invoice_no = f"INV{datetime.now().strftime('%Y%m%d%H%M%S')}"

    product_data = {
        "invoice_no": invoice_no,
        "customer": customer_name,
        "customer_email": customer_email,
        "date": date.today().strftime("%d-%m-%Y"),
        "items": [
            {
                "name": product_name,
                "category": category,
                "qty": quantity,
                "price": price
            }
        ],
        "total": total_price
    }

    html_template = """
    <html>
    <head>
        <style>

            body {
                font-family: Arial, sans-serif;
                width: 1000px;
                margin: 0 auto;
                padding: 40px;
                color: #333;
                background: white;
            }

            .invoice-container {
                border: 3px solid #000;
                padding: 30px;
                border-radius: 10px;
            }

            .company-name {
                text-align: center;
                font-size: 42px;
                font-weight: bold;
                color: #1f2937;
                margin-bottom: 10px;
            }

            .company-subtitle {
                text-align: center;
                font-size: 22px;
                color: #6b7280;
                margin-bottom: 25px;
            }

            .invoice-title {
                text-align: center;
                font-size: 36px;
                font-weight: bold;
                color: #dc2626;
                margin-bottom: 25px;
            }

            .details {
                font-size: 24px;
                line-height: 2;
                margin-bottom: 25px;
            }

            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
                font-size: 22px;
            }

            th {
                background-color: #f3f4f6;
                font-size: 24px;
            }

            th, td {
                border: 2px solid #d1d5db;
                padding: 15px;
                text-align: center;
            }

            .total-section {
                margin-top: 30px;
                text-align: right;
                font-size: 32px;
                font-weight: bold;
                color: #dc2626;
            }

            .footer {
                margin-top: 50px;
                text-align: center;
                font-size: 22px;
                color: #6b7280;
            }

        </style>
    </head>

    <body>

        <div class="invoice-container">

            <div class="company-name">
                ELECTROSTOCK
            </div>

            <div class="company-subtitle">
                Inventory Management System
            </div>

            <div class="invoice-title">
                SALES INVOICE
            </div>

            <div class="details">
                <strong>Invoice No:</strong> {{ invoice_no }} <br>
                <strong>Customer Name:</strong> {{ customer }} <br>
                <strong>Email:</strong> {{ customer_email }} <br>
                <strong>Date:</strong> {{ date }}
            </div>

            <table>
                <thead>
                    <tr>
                        <th>Sr.No</th>
                        <th>Product</th>
                        <th>Category</th>
                        <th>Quantity</th>
                        <th>Unit Price</th>
                        <th>Total</th>
                    </tr>
                </thead>

                <tbody>

                    {% for item in items %}
                    <tr>
                        <td>{{ loop.index }}</td>
                        <td>{{ item.name }}</td>
                        <td>{{ item.category }}</td>
                        <td>{{ item.qty }}</td>
                        <td>₹{{ item.price }}</td>
                        <td>₹{{ item.qty * item.price }}</td>
                    </tr>
                    {% endfor %}

                </tbody>
            </table>

            <div class="total-section">
                Total Amount : ₹{{ total }}
            </div>

            <div class="footer">
                Thank You For Shopping With ElectroStock
            </div>

        </div>

    </body>
    </html>
    """

    rendered_html = Template(html_template).render(**product_data)

    # High Resolution Output
    hti = Html2Image(
        size=(1400, 1800)
    )

    image_file = f"invoice_{invoice_no}.png"

    hti.screenshot(
        html_str=rendered_html,
        save_as=image_file
    )

    with open(image_file, "rb") as file:
        image_bytes = file.read()

    os.remove(image_file)

    return StreamingResponse(
        io.BytesIO(image_bytes),
        media_type="image/png"
    )





