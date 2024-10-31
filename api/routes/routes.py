from api.routes import *


@router.get("/")
def read_root():
    return {
        'Hello This is Rag Langchain application on FastAPI !!!'
    }


@router.post("/get_retriever/")
def get_retriever(user_id: UserID):
    user_vectorstore = VectorStore(user_id.user_id, openai_embedding_key=openai_embedding_apikey_cache[f"{user_id.admin_department}"])

    retriever_cache[f'{user_id.user_id}'] = user_vectorstore.user_retriever
    vectorstore_cache[f'{user_id.user_id}'] = user_vectorstore.user_db
    bm25_retriever_cache[f'{user_id.user_id}'] = user_vectorstore.user_bm25_retriever
    if user_vectorstore.user_db is not None:
        return {"OK"}
    else:
        return {"None"}


@router.post('/upload_data')
async def upload_file(file: UploadFile = File(...), user_id: str = Form(...)):
    admin_department = sql_conn.get_admin_department(user_id)
    vectorstore = VectorStore(user_id, openai_embedding_key=openai_embedding_apikey_cache[f"{admin_department}"])
    chunks = vectorstore.upload_file(file, user_id)

    new_vectorstore = VectorStore(user_id, openai_embedding_key=openai_embedding_apikey_cache[f"{admin_department}"])

    retriever_cache[f'{user_id}'] = new_vectorstore.user_retriever
    vectorstore_cache[f'{user_id}'] = new_vectorstore.user_db
    bm25_retriever_cache[f'{user_id}'] = new_vectorstore.user_bm25_retriever

    return chunks


@router.post('/add_prompt_template/')
async def add_prompt_template(prompt_template: PromptTemplate):
    sql_conn.add_prompt_template(prompt_template.title, prompt_template.prompt_text, prompt_template.user_id)


@router.post('/get_answer_about_users_data/')
async def get_response(question_request: QuestionRequest):
    # try:
        # With openai model
        if question_request.model in model_openai:
            apikey = apikeys_cache[f"{question_request.admin_department}"]["openaikey"]
            bot = ChatBot(openai_apikey=apikey, openai_embedding_key=openai_embedding_apikey_cache[f"{question_request.admin_department}"])

            user_retriever = retriever_cache[f'{question_request.user_id}']
            user_bm25_retriever = bm25_retriever_cache[f'{question_request.user_id}']

            prompt = await bot.question_handler(user_retriever, user_bm25_retriever, question_request)
            generator = bot.send_message_openai(prompt, question_request.model)

            return StreamingResponse(generator, media_type="text/event-stream")

        # With gemini model
        else:
            apikey = apikeys_cache[f"{question_request.admin_department}"]["geminikey"]
            bot = ChatBot(gemini_apikey=apikey, openai_embedding_key=openai_embedding_apikey_cache[f"{question_request.admin_department}"])

            user_retriever = retriever_cache[f'{question_request.user_id}']
            user_bm25_retriever = bm25_retriever_cache[f'{question_request.user_id}']

            prompt = await bot.question_handler(user_retriever, user_bm25_retriever, question_request)
            generator = bot.send_message_gemini(prompt, question_request.model)

            return StreamingResponse(generator, media_type="text/event-stream")

    # except:
    #     return {"Error"}


@router.post('/get_answer_about_system_data/')
async def get_response(question_request: QuestionRequestSystem):
    # try:
        # With openai model
        if question_request.model in model_openai:
            apikey = apikeys_cache[f"{question_request.admin_department}"]["openaikey"]
            bot = ChatBot(openai_apikey=apikey, openai_embedding_key=openai_embedding_apikey_cache[f"{question_request.admin_department}"])

            system_retriever = retriever_cache_admin[f'{question_request.admin_department}'][f'{question_request.folder_id}']
            system_bm25_retriever = bm25_retriever_cache_admin[f'{question_request.admin_department}'][f'{question_request.folder_id}']

            prompt = await bot.question_handler_system(system_retriever, system_bm25_retriever, question_request)
            generator = bot.send_message_openai(prompt, question_request.model)

            return StreamingResponse(generator, media_type="text/event-stream")

        # With gemini model
        else:
            apikey = apikeys_cache[f"{question_request.admin_department}"]["geminikey"]
            bot = ChatBot(gemini_apikey=apikey, openai_embedding_key=openai_embedding_apikey_cache[f"{question_request.admin_department}"])

            system_retriever = retriever_cache_admin[f'{question_request.admin_department}'][f'{question_request.folder_id}']
            system_bm25_retriever = bm25_retriever_cache_admin[f'{question_request.admin_department}'][f'{question_request.folder_id}']

            prompt = await bot.question_handler_system(system_retriever, system_bm25_retriever, question_request)
            generator = bot.send_message_gemini(prompt, question_request.model)

            return StreamingResponse(generator, media_type="text/event-stream")

    # except:
    #     return {"Error"}

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
        try:
            #dataframe_cache[f"{user_id}"]:
            dataframe_cache[f"{user_id}"].append(df)
            df = dataframe_cache[f"{user_id}"]
            agent_cache[f"{user_id}"] = CSVAgent(api_key=apikeys_cache[f"{admin_department}"]["openaikey"], df=df)
        except:
            dataframe_cache[f'{user_id}'] = [df]
            agent_cache[f"{user_id}"] = CSVAgent(api_key=apikeys_cache[f"{admin_department}"]["openaikey"], df=df)
        return "Saved dataframe successfully!"
    else:
        return f"Unsupported file format: {ext}"


@router.post('/get_answer_about_csv_file/')
async def get_response(question: CSVQuestion):
    agent = agent_cache[f"{question.user_id}"]
    agent.model = question.model
    response = await agent.get_response(question.question)
    return response


@router.delete("/delete_file/")
def delete_file(file: FileDelete):
    user_id = file.user_id
    file_name = file.file_name
    admin_department = sql_conn.get_admin_department(user_id)
    vectorstore = VectorStore(user_id, openai_embedding_key=openai_embedding_apikey_cache[f"{admin_department}"])

    try:
        vectorstore.delete_from_vectorstore(file_name, user_id)
        retriever_cache[f'{user_id}'] = vectorstore.user_retriever
        vectorstore_cache[f'{user_id}'] = vectorstore.user_db
        bm25_retriever_cache[f'{user_id}'] = vectorstore.user_bm25_retriever
        return 1
    except:
        return 0


# Router for UI
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
    #return len(apikeys_cache[f'{admin_department.admin_department}'])


@router.post('/upload_data_admin/')
async def upload_file_admin(file: UploadFile = File(...), admin_department: str = Form(...), folder_id: str = Form(...)):
    vectorstore = VectorStoreAdmin(admin_department, folder_id, openai_embedding_key=openai_embedding_apikey_cache[f"{admin_department}"])
    chunks = vectorstore.upload_file(file, admin_department, folder_id)

    new_vectorstore = VectorStoreAdmin(admin_department, folder_id, openai_embedding_key=openai_embedding_apikey_cache[f"{admin_department}"])

    # retriever_cache_admin[f'{admin_department}'].update(dict([(folder_id, new_vectorstore.admin_retriever)]))
    # vectorstore_cache_admin[f'{admin_department}'].update(dict([(folder_id, new_vectorstore.admin_db)]))
    # bm25_retriever_cache_admin[f'{admin_department}'].update(dict([(folder_id, new_vectorstore.admin_bm25_retriever)]))

    return chunks


@router.delete("/delete_file_admin/")
def delete_file_admin(file: FileDeleteAdmin):
    admin_department = file.admin_department
    file_name = file.file_name
    folder_id = file.folder_id
    vectorstore = VectorStoreAdmin(admin_department, folder_id, openai_embedding_key=openai_embedding_apikey_cache[f"{admin_department}"])

    retriever_cache_admin[f'{admin_department}'].update(dict([(folder_id, vectorstore.admin_retriever)]))
    vectorstore_cache_admin[f'{admin_department}'].update(dict([(folder_id, vectorstore.admin_db)]))
    bm25_retriever_cache_admin[f'{admin_department}'].update(dict([(folder_id, vectorstore.admin_bm25_retriever)]))

    try:
        vectorstore.delete_from_vectorstore(file_name, admin_department, folder_id)
        return 1
    except:
        return 0

@router.delete("/delete_folder/")
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
    sql_conn.add_prompt_template_admin(prompt_template.title, prompt_template.prompt_text, prompt_template.admin_department)