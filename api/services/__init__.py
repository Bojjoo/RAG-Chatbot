from api.config import *

# For chatbot
import ast
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import OpenAIEmbeddings
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.document_compressors.flashrank_rerank import FlashrankRerank
from flashrank import Ranker
from langchain.retrievers import ContextualCompressionRetriever
from pydantic import BaseModel
from dotenv import load_dotenv, find_dotenv
from langchain.callbacks import AsyncIteratorCallbackHandler
from langchain_google_community import GoogleSearchAPIWrapper
from langchain_core.tools import Tool
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_google_community.search import GoogleSearchResults


import asyncio
from typing import AsyncIterable

# For vectorstore_faiss
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    DirectoryLoader,
    TextLoader,
    CSVLoader,
    UnstructuredWordDocumentLoader
)
from langchain_community.vectorstores import FAISS
import os
from fastapi import UploadFile, File, Form
import shutil
from langchain.retrievers.ensemble import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_experimental.text_splitter import SemanticChunker
import tiktoken


from api.database.database import SQLDatabase


# For csv_agent
from langchain.agents import AgentType
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_google_genai import ChatGoogleGenerativeAI
import pandas as pd

sql_conn = SQLDatabase()

# Counting token
tokenizer = tiktoken.get_encoding("cl100k_base")


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


class WebSearchKey(BaseModel):
    google_search_id: str
    google_search_key: str
    serper_key: str


