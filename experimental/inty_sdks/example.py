import os
from inty import Inty
from dotenv import load_dotenv

load_dotenv()

client = Inty(
    base_url="http://localhost:8000",
    api_key=os.environ.get(
        "INTY_API_KEY"
    ),  # This is the default and can be omitted
)

response = client.api.v1.ai.agents.list()
print("Agents list response:", response)

# Create guest user and get token
guest_response = client.api.v1.auth.create_guest()
print("Guest response:", guest_response)

# Extract token from response and create new client with authentication
token = guest_response.data.token
authenticated_client = Inty(
    base_url="http://localhost:8000",
    api_key=token,
)

# Now use the authenticated client for protected endpoints
response = authenticated_client.api.v1.ai.agents.list()
print("Agents response:", response)
