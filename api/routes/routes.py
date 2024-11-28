from api.routes import *


@router.get("/")
def read_root():
    return {
        'Hello This is Rag Langchain application on FastAPI !!!'
    }


@router.post("/get_retriever/")
def get_retriever(user_folder: RetrievalUser):
    user_vectorstore = VectorStore(user_folder.user_id, user_folder.folder_id,
                                   openai_embedding_key=openai_embedding_apikey_cache[f"{user_folder.admin_department}"])

    try:
        if retriever_cache[f'{user_folder.user_id}']:
            retriever_cache[f'{user_folder.user_id}'].update(dict([(user_folder.folder_id, user_vectorstore.user_retriever)]))
            vectorstore_cache[f'{user_folder.user_id}'].update(dict([(user_folder.folder_id, user_vectorstore.user_db)]))
            bm25_retriever_cache[f'{user_folder.user_id}'].update(dict([(user_folder.folder_id, user_vectorstore.user_bm25_retriever)]))
    except:
        retriever_cache[f'{user_folder.user_id}'] = dict([(user_folder.folder_id, user_vectorstore.user_retriever)])
        vectorstore_cache[f'{user_folder.user_id}'] = dict([(user_folder.folder_id, user_vectorstore.user_db)])
        bm25_retriever_cache[f'{user_folder.user_id}'] = dict([(user_folder.folder_id, user_vectorstore.user_bm25_retriever)])
    if user_vectorstore.user_db is not None:
        return {"OK"}
    else:
        return {"None"}


@router.post("/save_websearch_google_api/")
async def save_websearch_google_api(key: WebsearchGoogleKey):
    google_api_key[key.user_id] = [key.search_id, key.search_key]


@router.post("/save_websearch_serper_api/")
async def save_websearch_serper_api(key: WebsearchSerperKey):
    serper_api_key[key.user_id] = key.key


@router.get("/check_websearch_google_api/")
async def check_websearch_google_api(user_id: UserID):
    try:
        if google_api_key[user_id.user_id]:
            return 1
    except:
        return 0


@router.get("/check_websearch_serper_api/")
async def check_websearch_serper_api(user_id: UserID):
    try:
        if serper_api_key[user_id.user_id]:
            return 1
    except:
        return 0


@router.delete("/delete_folder_user/")
def delete_folder_user(folder: FolderUser):
    user_id = folder.user_id
    folder_id = folder.folder_id

    if os.path.exists(f"./vectorstores/db_faiss_for_user/{user_id}/{folder_id}"):
        shutil.rmtree(f"./vectorstores/db_faiss_for_user/{user_id}/{folder_id}")
    if os.path.exists(f"./data/data_user/{user_id}/{folder_id}"):
        shutil.rmtree(f"./data/data_user/{user_id}/{folder_id}")
    sql_conn.delete_folder_user(folder_id)


@router.post('/upload_data/')
async def upload_file(file: UploadFile = File(...), user_id: str = Form(...), folder_id: str = Form(),
                      semantic_chunking: bool = Form()):
    admin_department = sql_conn.get_admin_department(user_id)
    vectorstore = VectorStore(user_id, folder_id,
                              openai_embedding_key=openai_embedding_apikey_cache[f"{admin_department}"])
    #chunks = vectorstore.upload_file(file, user_id, folder_id, semantic_chunking)
    chunks = await asyncio.to_thread(vectorstore.upload_file, file, user_id, folder_id, semantic_chunking)
    new_vectorstore = VectorStore(user_id, folder_id,
                                  openai_embedding_key=openai_embedding_apikey_cache[f"{admin_department}"])
    return chunks


@router.post('/add_prompt_template/')
async def add_prompt_template(prompt_template: PromptTemplate):
    sql_conn.add_prompt_template(prompt_template.title, prompt_template.prompt_text, prompt_template.user_id)


@router.post('/get_answer_about_users_data/')
async def get_answer_about_users_data(question_request: QuestionRequest):
    if question_request.model in model_openai:
        bot = ChatBot(
            openai_apikey=apikeys_cache[question_request.admin_department]["openaikey"],
            openai_embedding_key=openai_embedding_apikey_cache[question_request.admin_department]
        )
    else:
        bot = ChatBot(
            gemini_apikey=apikeys_cache[question_request.admin_department]["geminikey"],
            openai_embedding_key=openai_embedding_apikey_cache[question_request.admin_department]
        )
    try:
        user_retriever = retriever_cache[f'{question_request.user_id}'][f'{question_request.folder_id}']
        user_bm25_retriever = bm25_retriever_cache[f'{question_request.user_id}'][f'{question_request.folder_id}']
    except:
        user_retriever = None
        user_bm25_retriever = None
    if len(question_request.search_tool) > 0:
        websearchkey = WebSearchKey(google_search_id=google_api_key.get(question_request.user_id, ["", ""])[0],
                                    google_search_key=google_api_key.get(question_request.user_id, ["", ""])[1],
                                    serper_key=serper_api_key.get(question_request.user_id, ""))
    else:
        websearchkey = WebSearchKey(google_search_id="", google_search_key="", serper_key="")
    prompt = await bot.question_handler(user_retriever, user_bm25_retriever, question_request, websearchkey)
    if question_request.model in model_openai:
        generator = bot.send_message_openai(prompt, question_request.model)
    else:
        generator = bot.send_message_gemini(prompt, question_request.model)

    return StreamingResponse(generator, media_type="text/event-stream")


@router.post('/get_answer_about_system_data/')
async def get_response(question_request: QuestionRequest) -> StreamingResponse:
    bot = ChatBot(
        openai_apikey=apikeys_cache[question_request.admin_department]["openaikey"] if question_request.model in model_openai else None,
        gemini_apikey=apikeys_cache[question_request.admin_department]["geminikey"] if question_request.model in model_gemini else None,
        openai_embedding_key=openai_embedding_apikey_cache[question_request.admin_department]
    )
    # nếu folder_id được truyền về thì lấy ra retriever cho folder_id đó, ngược lại để None
    try:
        system_retriever = retriever_cache_admin[f'{question_request.admin_department}'][f'{question_request.folder_id}']
        system_bm25_retriever = bm25_retriever_cache_admin[f'{question_request.admin_department}'][f'{question_request.folder_id}']
    except:
        system_retriever = None
        system_bm25_retriever = None
    if len(question_request.search_tool) > 0:
        websearchkey = WebSearchKey(google_search_id=google_api_key.get(question_request.user_id, ["", ""])[0],
                                    google_search_key=google_api_key.get(question_request.user_id, ["", ""])[1],
                                    serper_key=serper_api_key.get(question_request.user_id, ""))

    else:
        websearchkey = WebSearchKey(google_search_id="", google_search_key="", serper_key="")
    prompt = await bot.question_handler_system(system_retriever, system_bm25_retriever, question_request, websearchkey)
    generator = bot.send_message_openai(prompt, question_request.model) if question_request.model in model_openai \
        else bot.send_message_gemini(prompt, question_request.model)

    return StreamingResponse(generator, media_type="text/event-stream")


@router.post('/upload_CSV_file/')
async def csv_file_handler(file: UploadFile = File(...), user_id: str = Form(...), admin_department: str = Form(...)):
    file_formats = {
        "csv": pd.read_csv,
        "xls": pd.read_excel,
        "xlsx": pd.read_excel,
        "xlsm": pd.read_excel,
        "xlsb": pd.read_excel,
    }
    try:
        ext = os.path.splitext(file.filename)[1][1:].lower()
    except:
        ext = file.filename.split(".")[-1]
    if ext in file_formats:
        df = file_formats[ext](file.file)
        # Nếu trước đó đã up file lên rồi
        try:
            df.name = file.filename
            dataframe_cache[f"{user_id}"].append(df)
            df = dataframe_cache[f"{user_id}"]
            agent_cache[f"{user_id}"] = CSVAgent(api_key=apikeys_cache[f"{admin_department}"]["openaikey"], df=df)

        # nếu chưa từng up file lên
        except:
            df.name = file.filename
            dataframe_cache[f'{user_id}'] = [df]
            agent_cache[f"{user_id}"] = CSVAgent(api_key=apikeys_cache[f"{admin_department}"]["openaikey"], df=df)

        return [df.name for df in dataframe_cache[f"{user_id}"]]
    else:
        return f"Unsupported file format: {ext}"


@router.delete('/delete_csv_file/')
async def delete_csv_file(file: CSVFile):
    dataframe_cache[f"{file.user_id}"] = [i for i in dataframe_cache[f"{file.user_id}"] if i.name != file.file_name]
    agent_cache[f"{file.user_id}"] = CSVAgent(api_key=apikeys_cache[f"{file.admin_department}"]["openaikey"],
                                              df=dataframe_cache[f"{file.user_id}"])
    return [df.name for df in dataframe_cache[f"{file.user_id}"]]


@router.post('/get_answer_about_csv_file/')
async def get_response(question: CSVQuestion):
    agent = agent_cache[f"{question.user_id}"]
    agent.model = question.model
    response = await agent.get_response(question.question)
    return response


@router.get('/get_csv_file/')
async def get_csv_file(user_id: UserID):
    try:
        return [df.name for df in dataframe_cache[f"{user_id.user_id}"]]
    except:
        return 0


@router.delete("/delete_file/")
def delete_file(file: FileDelete):
    admin_department = sql_conn.get_admin_department(file.user_id)
    vectorstore = VectorStore(file.user_id, file.folder_id,
                              openai_embedding_key=openai_embedding_apikey_cache[f"{admin_department}"])

    try:
        vectorstore.delete_from_vectorstore(file.file_name, file.user_id, file.folder_id)
        # retriever_cache[f'{user_id}'] = vectorstore.user_retriever
        # vectorstore_cache[f'{user_id}'] = vectorstore.user_db
        # bm25_retriever_cache[f'{user_id}'] = vectorstore.user_bm25_retriever
        return 1
    except:
        return 0


# Router for UI
# Rename conversation
@router.post("/rename_conversation/")
async def rename_conversation(history_chat: HistoryChat):
    rename_bot = ChatBot(openai_apikey=apikeys_cache[f"{history_chat.admin_department}"]["openaikey"],
                         openai_embedding_key=openai_embedding_apikey_cache[f"{history_chat.admin_department}"])
    new_name = await rename_bot.rename_conversation(history_chat.history)
    return new_name


# Signin user endpoint
@router.post("/sign_in_user/")
async def verify_sign_in(account: SignInAccount):
    try:
        stored_password = sql_conn.get_password_of_user(account.user_name)
        user_id = sql_conn.get_userid_from_username(account.user_name)
        if stored_password == account.password:
            return user_id
        else:
            return 0
    except:
        return 0


@router.post("/register_account/")
async def register_account(new_acc: SignUpAccount):
    result = sql_conn.register_account(new_acc.user_name, new_acc.password, new_acc.admin_department)
    return result


# Router for Admin
# Signin admin endpoint
@router.post("/sign_in_admin/")
async def verify_sign_in(account: SignInAdminAccount):
    try:
        stored_password = sql_conn.get_password_of_admin(account.admin_username)
        admin_department = sql_conn.get_admin_department_from_admin_username(account.admin_username)
        if stored_password == account.admin_password:
            return admin_department
        else:
            return 0
    except:
        return 0


@router.post("/get_retriever_admin_file/")
def get_retriever(admin_department: AdminRetriever):
    admin_vectorstore = VectorStoreAdmin(admin_department.admin_department, admin_department.folder_id,
                                         openai_embedding_key=openai_embedding_apikey_cache[f"{admin_department.admin_department}"])
    try:
        if retriever_cache_admin[f'{admin_department.admin_department}']:
            retriever_cache_admin[f'{admin_department.admin_department}'].update(dict([(admin_department.folder_id, admin_vectorstore.admin_retriever)]))
            vectorstore_cache_admin[f'{admin_department.admin_department}'].update(dict([(admin_department.folder_id, admin_vectorstore.admin_db)]))
            bm25_retriever_cache_admin[f'{admin_department.admin_department}'].update(dict([(admin_department.folder_id, admin_vectorstore.admin_bm25_retriever)]))
    except:
        retriever_cache_admin[f'{admin_department.admin_department}'] = dict([(admin_department.folder_id, admin_vectorstore.admin_retriever)])
        vectorstore_cache_admin[f'{admin_department.admin_department}'] = dict([(admin_department.folder_id, admin_vectorstore.admin_db)])
        bm25_retriever_cache_admin[f'{admin_department.admin_department}'] = dict([(admin_department.folder_id, admin_vectorstore.admin_bm25_retriever)])
    if admin_vectorstore.admin_db is not None:
        return {"OK"}
    else:
        return {"None"}


@router.post("/get_apikey_admin/")
def get_apikey_admin(admin_department: AdminID):
    apikey = sql_conn.get_api_key(admin_department.admin_department)
    openai_embedding_key = sql_conn.get_embedding_apikey(admin_department.admin_department)
    # Lưu key vào cache
    openai_embedding_apikey_cache[f'{admin_department.admin_department}'] = openai_embedding_key
    apikeys_cache[f'{admin_department.admin_department}'] = dict(apikey)


@router.post('/upload_data_admin/')
async def upload_file_admin(file: UploadFile = File(...), admin_department: str = Form(...), folder_id: str = Form(...),
                            semantic_chunking: bool = Form()):
    vectorstore = VectorStoreAdmin(admin_department, folder_id,
                                   openai_embedding_key=openai_embedding_apikey_cache[f"{admin_department}"])
    # chunks = vectorstore.upload_file(file, admin_department, folder_id, semantic_chunking)
    chunks = await asyncio.to_thread(vectorstore.upload_file, file, admin_department, folder_id, semantic_chunking)

    new_vectorstore = VectorStoreAdmin(admin_department, folder_id,
                                       openai_embedding_key=openai_embedding_apikey_cache[f"{admin_department}"])

    return chunks


@router.delete("/delete_file_admin/")
def delete_file_admin(file: FileDeleteAdmin):
    admin_department = file.admin_department
    file_name = file.file_name
    folder_id = file.folder_id
    vectorstore = VectorStoreAdmin(admin_department, folder_id,
                                   openai_embedding_key=openai_embedding_apikey_cache[f"{admin_department}"])
    try:
        vectorstore.delete_from_vectorstore(file_name, admin_department, folder_id)
        return 1
    except:
        return 0


@router.delete("/delete_folder_admin/")
def delete_folder(folder: Folder):
    admin_department = folder.admin_department
    folder_id = folder.folder_id

    if os.path.exists(f"./vectorstores/db_faiss/{admin_department}/{folder_id}"):
        shutil.rmtree(f"./vectorstores/db_faiss/{admin_department}/{folder_id}")
    if os.path.exists(f"./data/data_system/{admin_department}/{folder_id}"):
        shutil.rmtree(f"./data/data_system/{admin_department}/{folder_id}")
    sql_conn.delete_folder(folder_id)


@router.post('/add_prompt_template_admin/')
async def add_prompt_template_admin(prompt_template: PromptTemplateAdmin):
    sql_conn.add_prompt_template_admin(prompt_template.title, prompt_template.prompt_text,
                                       prompt_template.admin_department)


@router.post('/test_key/')
async def test_key(apikey: APIKey):
    try:
        model_test = CheckAPIKey(apikey=apikey.apikey, type=apikey.type)
        return 1
    except:
        return 0
