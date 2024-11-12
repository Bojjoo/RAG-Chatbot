from api.services import *


class VectorStore:
    def __init__(self, user_id=None, folder_id=None, openai_embedding_key=None):
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
                                                            length_function=len)
        self.model_embedding = OpenAIEmbeddings(model=MODEL_EMBEDDING, api_key=openai_embedding_key, dimensions=3072)
        try:
            self.user_db = FAISS.load_local(f'{USER_DATABASE}/{user_id}/{folder_id}', self.model_embedding,
                                            allow_dangerous_deserialization=True)
            self.user_retriever = self.user_db.as_retriever(search_kwargs=SEARCH_KWARGS, search_type=SEARCH_TYPE)
            documents = list(self.user_db.docstore._dict.values())
            self.user_bm25_retriever = BM25Retriever.from_documents(documents)
            self.user_bm25_retriever.k = 25
        except:
            self.user_db = None
            self.user_retriever = None
            self.user_bm25_retriever = None

    # For user
    def counting_token(self, file):
        file_extension = os.path.splitext(file)[1].lower()
        loaders = {
            '.pdf': PyPDFLoader,
            '.txt': TextLoader,
            '.docx': UnstructuredWordDocumentLoader
        }
        if file_extension not in loaders:
            raise ValueError("Unsupported file type")

        loader = loaders[file_extension](file)
        contexts = ''.join(doc.page_content for doc in loader.load())
        tokens = tokenizer.encode(contexts)
        return len(tokens), len(contexts)

    def recursive_chunking(self, file_path):
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension == '.pdf':
            loader = PyPDFLoader(file_path)
        elif file_extension == '.txt':
            loader = TextLoader(file_path)
        elif file_extension == '.docx':
            loader = UnstructuredWordDocumentLoader(file_path)
        else:
            raise ValueError("Unsupported file type")
        documents = loader.load()
        chunks = self.text_splitter.split_documents(documents)
        return chunks

    def semantic_chunking(self, file_path):
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension == '.pdf':
            loader = PyPDFLoader(file_path)
        elif file_extension == '.txt':
            loader = TextLoader(file_path)
        elif file_extension == '.docx':
            loader = UnstructuredWordDocumentLoader(file_path)
        else:
            raise ValueError("Unsupported file type")
        documents = loader.load()

        text_splitter = SemanticChunker(self.model_embedding, breakpoint_threshold_type='percentile',
                                        breakpoint_threshold_amount=95)
        chunks = text_splitter.create_documents(texts=[document.page_content for document in documents],
                                                metadatas=[document.metadata for document in documents])
        return chunks

    # Lưu vào vectorstore
    def create_vectorstore(self, chunks):
        db = FAISS.from_documents(chunks, self.model_embedding)
        return db

    # thêm vào vectorstore
    def merge_to_vectorstore(self, old_db, new_db, user_id, folder_id):
        old_db.merge_from(new_db)
        old_db.save_local(f'{USER_DATABASE}/{user_id}/{folder_id}')
        return old_db

    # xóa khỏi vectorstore theo id của chunks
    def delete_from_vectorstore(self, file_name, user_id, folder_id):
        # db_user, retriever_user = self.check_user_db(user_id)
        db_user = self.user_db
        docstore = db_user.docstore._dict
        key_delete = []
        for key, values in docstore.items():
            if values.metadata['source'].endswith(f"{file_name}"):
                key_delete.append(key)
        db_user.delete(key_delete)
        db_user.save_local(f"{USER_DATABASE}/{user_id}/{folder_id}")
        os.remove(f"{USER_DOCUMENT}/{user_id}/{folder_id}/{file_name}")
        sql_conn.delete_file(file_name, folder_id)

    # upload file và lưu vào vectorstore faiss, lưu file vào folder của conversation_id
    def upload_file(self, file: UploadFile = File(...), user_id: str = Form(...), folder_id: str = Form(...),
                    semantic_chunking: bool = Form(...)):
        name = file.filename
        type = "text_file"
        if name.endswith('.pdf') or name.endswith('docx'):
            # Lấy ra file size
            file.file.seek(0, os.SEEK_END)
            file_size = round(file.file.tell() / (1024 * 1024), 2)
            file.file.seek(0)
            result = sql_conn.save_file_detail(file.filename, file_size, folder_id, type)
            # Nếu result =1: thỏa mãn yêu cầu về total_size <50 và file_size <20
            if result == 1:
                # Lưu file vào folder
                folder_path = f"{USER_DOCUMENT}/{user_id}/{folder_id}"
                os.makedirs(folder_path, exist_ok=True)

                with open(f"{folder_path}/{file.filename}", "wb") as buff:
                    shutil.copyfileobj(file.file, buff)
                # Chunking document
                if semantic_chunking:
                    chunks = self.semantic_chunking(f"{folder_path}/{file.filename}")
                else:
                    chunks = self.recursive_chunking(f"{folder_path}/{file.filename}")
                # bỏ vào vectorstore mới
                try:
                    new_db_for_user = self.create_vectorstore(chunks)
                    try:
                        # Nếu đã có db, hợp nhất db cũ với db mới
                        db_user = self.user_db
                        merged_db_user = self.merge_to_vectorstore(db_user, new_db_for_user, user_id, folder_id)
                        # return merged_db_user
                    except:  # Nếu chưa có db
                        new_db_for_user.save_local(f'{USER_DATABASE}/{user_id}/{folder_id}')
                        # return new_db_for_user
                    return f"Successfully uploaded {file.filename}, num_splits: {len(chunks)}"
                except:
                    sql_conn.delete_file(file.filename, user_id)
                    return "Incorrect API key provided, please make sure your API key is correct!"
            else:
                sql_conn.delete_file(file.filename, user_id)
                return """Failed to upload document, the total size limit is 50Mb and the file size limit is 20Mb.
                        You can delete existed document to upload an other one!"""
        else:
            return "Only pdf, docx files are supported"


# For admin
class VectorStoreAdmin:
    def __init__(self, admin_department=None, folder_id=None, openai_embedding_key=None):
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
                                                            length_function=len)
        self.model_embedding = OpenAIEmbeddings(model=MODEL_EMBEDDING, api_key=openai_embedding_key)
        try:
            self.admin_db = FAISS.load_local(f'{SYSTEM_DATABASE}/{admin_department}/{folder_id}', self.model_embedding,
                                            allow_dangerous_deserialization=True)
            self.admin_retriever = self.admin_db.as_retriever(search_kwargs=SEARCH_KWARGS, search_type=SEARCH_TYPE)
            documents = list(self.admin_db.docstore._dict.values())
            self.admin_bm25_retriever = BM25Retriever.from_documents(documents)
            self.admin_bm25_retriever.k = 25
        except:
            self.admin_db = None
            self.admin_retriever = None
            self.admin_bm25_retriever = None

    def recursive_chunking(self, file_path):
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension == '.pdf':
            loader = PyPDFLoader(file_path)
        elif file_extension == '.txt':
            loader = TextLoader(file_path)
        elif file_extension == '.csv':
            loader = CSVLoader(file_path)
        elif file_extension == '.docx':
            loader = UnstructuredWordDocumentLoader(file_path)
        else:
            raise ValueError("Unsupported file type")
        documents = loader.load()
        chunks = self.text_splitter.split_documents(documents)
        return chunks

    def semantic_chunking(self, file_path):
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension == '.pdf':
            loader = PyPDFLoader(file_path)
        elif file_extension == '.txt':
            loader = TextLoader(file_path)
        elif file_extension == '.docx':
            loader = UnstructuredWordDocumentLoader(file_path)
        else:
            raise ValueError("Unsupported file type")
        documents = loader.load()

        text_splitter = SemanticChunker(self.model_embedding, breakpoint_threshold_type='percentile',
                                        breakpoint_threshold_amount=95)
        chunks = text_splitter.create_documents(texts=[document.page_content for document in documents],
                                                metadatas=[document.metadata for document in documents])
        return chunks

    # Lưu vào vectorstore
    def create_vectorstore(self, chunks):
        db = FAISS.from_documents(chunks, self.model_embedding)
        return db

    # thêm vào vectorstore
    def merge_to_vectorstore(self, old_db, new_db, admin_department, folder_id):
        old_db.merge_from(new_db)
        old_db.save_local(f'{SYSTEM_DATABASE}/{admin_department}/{folder_id}')
        return old_db

    # xóa khỏi vectorstore theo id của chunks
    def delete_from_vectorstore(self, file_name, admin_department, folder_id):
        # db_user, retriever_user = self.check_user_db(user_id)
        admin_db = self.admin_db
        docstore = admin_db.docstore._dict
        key_delete = []
        for key, values in docstore.items():
            if values.metadata['source'].endswith(f"{file_name}"):
                key_delete.append(key)
        admin_db.delete(key_delete)
        admin_db.save_local(f"{SYSTEM_DATABASE}/{admin_department}/{folder_id}")
        os.remove(f"{SYSTEM_DOCUMENT}/{admin_department}/{folder_id}/{file_name}")
        sql_conn.delete_file_admin(file_name, folder_id)

    def upload_file(self, file: UploadFile = File(...), admin_department: str = Form(...), folder_id: str = Form(...),
                    semantic_chunking: bool = Form(...)):
        name = file.filename
        if name.endswith('.pdf') or name.endswith('docx'):
            # Lấy ra file size
            file.file.seek(0, os.SEEK_END)
            file_size = round(file.file.tell() / (1024 * 1024), 2)
            file.file.seek(0)

            sql_conn.save_file_detail_admin(file.filename, file_size, folder_id)
            # Lưu file vào folder
            folder_path = f"{SYSTEM_DOCUMENT}/{admin_department}/{folder_id}"
            os.makedirs(folder_path, exist_ok=True)

            with open(f"{folder_path}/{file.filename}", "wb") as buff:
                shutil.copyfileobj(file.file, buff)
            if semantic_chunking:
                chunks = self.semantic_chunking(f"{folder_path}/{file.filename}")
            else:
                chunks = self.recursive_chunking(f"{folder_path}/{file.filename}")
            # bỏ vào vectorstore mới
            try:
                new_db_for_admin = self.create_vectorstore(chunks)
                try:
                    # Nếu đã có db, hợp nhất db cũ với db mới
                    admin_db = self.admin_db
                    merged_db_user = self.merge_to_vectorstore(admin_db, new_db_for_admin, admin_department, folder_id)
                    # return merged_db_user
                except:  # Nếu chưa có db
                    new_db_for_admin.save_local(f'{SYSTEM_DATABASE}/{admin_department}/{folder_id}')
                    # return new_db_for_user

                return f"Successfully uploaded {file.filename}, num_splits: {len(chunks)}"
            except:
                sql_conn.delete_file_admin(file.filename, folder_id)
                return "Incorrect API key provided, please make sure your API key is correct!"
        else:
            return "Only pdf, docx files are supported"
        

