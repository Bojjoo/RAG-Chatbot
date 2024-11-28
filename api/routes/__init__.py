from api.services.chatbot import ChatBot, CheckAPIKey
from api.services.vectorstore_faiss import VectorStore, VectorStoreAdmin
from fastapi import UploadFile, File, Form, APIRouter
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from api.database.database import SQLDatabase
from api.services.csv_agent import CSVAgent
import pandas as pd
import os
import shutil
import asyncio

# LLM API keys
openai_embedding_apikey_cache = {}
apikeys_cache = {}
router = APIRouter()

# Web search api key
google_api_key = {}
serper_api_key = {}

# for users's files
retriever_cache = {}
vectorstore_cache = {}
bm25_retriever_cache = {}

# for admin's files
retriever_cache_admin = {}
vectorstore_cache_admin = {}
bm25_retriever_cache_admin = {}


dataframe_cache = {}
sql_conn = SQLDatabase()

agent_cache = {}
agent_conversation_cache = {}

model_openai = ["gpt-4", "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
model_gemini = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro", "gemini-1.5-flash-002", "gemini-1.5-pro-002",
                "gemini-1.5-flash-8b"]


class QuestionRequest(BaseModel):
    question: str
    conversation_id: str
    prompt_template: str
    user_id: str
    model: str
    admin_department: str
    folder_id: str
    prompt_folder: str
    search_tool: str


class UserID(BaseModel):
    user_id: str
    admin_department: str


class RetrievalUser(BaseModel):
    user_id: str
    folder_id: str
    admin_department: str


class FileDelete(BaseModel):
    file_name: str
    user_id: str
    folder_id: str


class PromptTemplate(BaseModel):
    title: str
    prompt_text: str
    user_id: str


class PromptTemplateAdmin(BaseModel):
    title: str
    prompt_text: str
    admin_department: str


class HistoryChat(BaseModel):
    history: str
    admin_department: str


class CSVFile(BaseModel):
    file_name: str
    user_id: str
    admin_department: str


class CSVQuestion(BaseModel):
    user_id: str
    question: str
    model: str


class SignInAccount(BaseModel):
    user_name: str
    password: str


class SignUpAccount(BaseModel):
    user_name: str
    password: str
    admin_department: str


class SignInAdminAccount(BaseModel):
    admin_username: str
    admin_password: str


class AdminID(BaseModel):
    admin_department: str


class AdminRetriever(BaseModel):
    admin_department: str
    folder_id: str


class FileDeleteAdmin(BaseModel):
    file_name: str
    admin_department: str
    folder_id: str


class Folder(BaseModel):
    folder_id: str
    admin_department: str


class FolderUser(BaseModel):
    folder_id: str
    user_id: str


class APIKey(BaseModel):
    apikey: str
    type: str


class WebsearchSerperKey(BaseModel):
    user_id: str
    key: str


class WebsearchGoogleKey(BaseModel):
    user_id: str
    search_id: str
    search_key: str


class WebSearchKey(BaseModel):
    google_search_id: str
    google_search_key: str
    serper_key: str
