from fastapi.testclient import TestClient
from src.main import app

# Create a TestClient instance with the FastAPI app
test_client = TestClient(app)


# Define a pytest test function
def test_hello_world():
    # Make a GET request to the root endpoint of the HelloWorld router
    response = test_client.get("/")

    # Assert the response status code is 200
    assert response.status_code == 200

    # Assert the response body contains the expected message
    assert response.json() == {"Hello": "World"}
