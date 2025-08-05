from html2image import Html2Image
from jinja2 import Template

def generate_invoice_png(data, output_path="invoice.png"):
    template_html = """
    <html>
      <head>
        <style>
          body { font-family: Arial, sans-serif; padding: 30px; }
          h2 { text-align: center; color: #333; }
          table { width: 100%; border-collapse: collapse; margin-top: 20px; }
          th, td { border: 1px solid #aaa; padding: 10px; text-align: left; }
          th { background-color: #f2f2f2; }
        </style>
      </head>
      <body>
        <h2>Invoice</h2>
        <p><strong>Customer:</strong> {{ customer }}</p>
        <p><strong>Date:</strong> {{ date }}</p>

        <table>
          <tr>
            <th>#</th>
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
    rendered = Template(template_html).render(**data)

    hti = Html2Image(output_path='.')
    hti.screenshot(html_str=rendered, save_as=output_path)
