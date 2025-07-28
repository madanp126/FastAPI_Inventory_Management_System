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

# JWT_SECRET = os.getenv('JWT_SECRET_KEY')
JWT_SECRET ='vmFpf45O594QkATqukUP65ec94P0GjIYjO-UfJCQYSI'
