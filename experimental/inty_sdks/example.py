import os
from inty import Inty
from dotenv import load_dotenv

load_dotenv()

client = Inty(
    base_url="http://localhost:8000",
    api_key=os.environ.get("INTY_API_KEY"),  # This is the default and can be omitted
)

response = client.api.v1.auth.create_guest()
print(response.code)