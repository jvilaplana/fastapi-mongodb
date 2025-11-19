import os
from typing import Optional, List

from fastapi import FastAPI, Body, HTTPException, status
from fastapi.responses import Response
from pydantic import ConfigDict, BaseModel, Field
from pydantic.functional_validators import BeforeValidator
from dotenv import load_dotenv
import certifi

from typing_extensions import Annotated

from bson import ObjectId
from pymongo import AsyncMongoClient
from pymongo import ReturnDocument

# Load environment variables from a .env file
load_dotenv()

# MongoDB connection URI (Cloud-hosted MongoDB Atlas in this case)
MONGODB_URI = os.getenv("MONGODB_URI")
client = AsyncMongoClient(MONGODB_URI, tlsCAFile=certifi.where())

db = client["library"]
book_collection = db.get_collection("books")

# Represents an ObjectId field in the database.
# It will be represented as a `str` on the model so that it can be serialized to JSON.
PyObjectId = Annotated[str, BeforeValidator(str)]

class BookModel(BaseModel):
    """
    Class for a book record.
    """
    # The primary key for the BookModel, stored as a `str` on the instance.
    # This will be aliased to `_id` when sent to MongoDB,
    # but provided as `id` in the API requests and responses.
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    title: str = Field(...)
    isbn: str = Field(...)
    author: str = Field(...)
    pages: int = Field(...)
    editorial: Optional[str]
    
    model_config = ConfigDict(
        populate_by_name=True,          # https://docs.pydantic.dev/2.0/usage/model_config/#populate-by-name
        arbitrary_types_allowed=True,   # https://docs.pydantic.dev/2.0/usage/model_config/#arbitrary-types-allowed
    )

class UpdateBookModel(BaseModel):
    """
    A set of optional updates to be made to a document in the database.
    """

    title: Optional[str] = None
    isbn: Optional[str] = None
    author: Optional[str] = None
    pages: Optional[int] = None
    editorial: Optional[str] = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )

class BookCollection(BaseModel):
    """
    A container holding a list of `BookModel` instances.

    This exists because providing a top-level array in a JSON response can be a [vulnerability](https://haacked.com/archive/2009/06/25/json-hijacking.aspx/)
    """

    books: List[BookModel]

app = FastAPI(
    title="FastAPI + MongoDB Atlas example",
    summary="A sample application showing how to use FastAPI + MongoDB Atlas.",
)

@app.get(
    "/test-db-connection/",
    response_description="Test MongoDB Atlas connection",
)
async def test_db_connection():
    """
    Test the DB connection.
    """
    try:
        await client.admin.command('ping')
        return {"message": "Pinged your deployment. You successfully connected to MongoDB Atlas!"}
    except Exception as e:
        return {"error": e}


@app.get(
    "/books/",
    response_description="List all books",
    response_model=BookCollection,
    response_model_by_alias=False,
)
async def list_books():
    """
    List all of the books in the database.

    The response is unpaginated and limited to 1000 results.
    """
    return BookCollection(books=await book_collection.find().to_list(1000))


@app.get(
    "/books/{isbn}",
    response_description="Get a single book by ISBN",
    response_model=BookModel,
    response_model_by_alias=False,
)
async def get_book(isbn: str):
    """
    Get the record for a specific book, looked up by `isbn`.
    """
    if (
        book := await book_collection.find_one({"isbn": isbn})
    ) is not None:
        return book

    raise HTTPException(status_code=404, detail=f"Book with ISBN {isbn} was not found")


@app.post(
    "/books/",
    response_description="Add new book",
    response_model=BookModel,
    status_code=status.HTTP_201_CREATED,
    response_model_by_alias=False,
)
async def create_book(book: BookModel = Body(...)):
    """
    Insert a new book record.

    A unique `id` will be created and provided in the response.
    """
    new_book = book.model_dump(by_alias=True, exclude=["id"])
    result = await book_collection.insert_one(new_book)
    new_book["_id"] = result.inserted_id

    return new_book


@app.put(
    "/books/{id}",
    response_description="Update a book",
    response_model=BookModel,
    response_model_by_alias=False,
)
async def update_book(id: str, book: UpdateBookModel = Body(...)):
    """
    Update individual fields of an existing book record.

    Only the provided fields will be updated.
    Any missing or `null` fields will be ignored.
    """
    book = {
        k: v for k, v in book.model_dump(by_alias=True).items() if v is not None
    }

    if len(book) >= 1:
        update_result = await book_collection.find_one_and_update(
            {"_id": ObjectId(id)},
            {"$set": book},
            return_document=ReturnDocument.AFTER,
        )
        if update_result is not None:
            return update_result
        else:
            raise HTTPException(status_code=404, detail=f"Book {id} not found")

    # The update is empty, but we should still return the matching document:
    if (existing_book := await book_collection.find_one({"_id": id})) is not None:
        return existing_book

    raise HTTPException(status_code=404, detail=f"Book {id} not found")


@app.delete("/books/{id}", response_description="Delete a book")
async def delete_book(id: str):
    """
    Remove a single book record from the database.
    """
    delete_result = await book_collection.delete_one({"_id": ObjectId(id)})

    if delete_result.deleted_count == 1:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"Book {id} not found")
