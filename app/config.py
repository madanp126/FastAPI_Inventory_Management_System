import os
from dotenv import load_dotenv
load_dotenv()

DB_CONFIG={
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'db': os.getenv('DB_NAME'),
    'port': int(os.getenv('DB_PORT',1234)),
}

JWT_SECRET = os.getenv('JWT_SECRET_KEY')

SMTP_CONFIG={
    'server':os.getenv('SMTP_SERVER'),
    'port':int(os.getenv('SMTP_PORT')),
    'username':os.getenv('SMTP_USER'),
    'password':os.getenv('SMTP_PASSWORD'),
}