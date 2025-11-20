# FastAPI + MongoDB Atlas example
Example project showing how integrate [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) into a FastAPI application.

This project assumes an existing database named `library` and a collection named `books`.

Project setup:
```bash
# Create the virtual environment
python3 -m venv venv
# Activate the virtual environment
source venv/bin/activate
# Install requirements
pip install -r requirements.txt
# Create .env file with `MONGODB_URI="mongodb+srv://<user>:<password>@<mongodb-atlas-domain>"`
# Run app
uvicorn app:app --reload
```

For a more complex full-stack projec setup, you can check the [Full Stack FastAPI, React, MongoDB (FARM) Base Project Generator](https://github.com/mongodb-labs/full-stack-fastapi-mongodb).
