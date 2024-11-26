from api.services import *


class ChatBot:
    def __init__(self, openai_apikey=None, gemini_apikey=None, openai_embedding_key=None):
        self.model_llm = None
        self.openai_apikey = openai_apikey
        self.gemini_apikey = gemini_apikey
        self.model_reformulate_question = ChatOpenAI(temperature=TEMPERATURE, model=MODEL_LLM,
                                                     api_key=openai_embedding_key)
        self.sender = ['human', 'ai']

    # Reformulate the question based on history
    async def reformulate_question(self, question, history):
        reformulate_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", REGENERATE_QUESTION_PROMPT),
                ("system", "Chat history: \n {chat_history}\n"),
                ("system", "Reformulate this input: {question}"),
            ]
        )

        question_pt = reformulate_prompt.format(chat_history=history, question=question)
        new_question = await self.model_reformulate_question.ainvoke(question_pt)
        return new_question.content

    # Retrieve relevant data
    async def retriever(self, question, retriever, bm25_retriever):
        ensemble_retriever = EnsembleRetriever(retrievers=[bm25_retriever, retriever], weights=[0.5, 0.5])

        compressed_docs = await ensemble_retriever.ainvoke(question)
        content_text = "\n\n---\n\n".join([doc.page_content for doc in compressed_docs[:6]])
        return content_text

    def prompt_rag(self, question, context, web_search_context, history, prompt_template, prompt_folder):
        llm_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "**Instruction 1:**\n {prompt_folder}\n"),
                ("system", "**Instruction 2:**\n {prompt_template}\n"),
                ("system", "**Chat history:**\n {chat_history}\n"),
                ("system", "**Context about relevant data:**\n{context}\n"),
                ("system", "**Context received from google search:**\n{web_search_context}\n"),
                ("system", "**Answer the question:** {question}"),
            ]
        )
        prompt = llm_prompt.format(prompt_folder=prompt_folder, prompt_template=prompt_template,
                                   chat_history=history, context=context, web_search_context=web_search_context,
                                   question=question)
        return prompt

    def prompt_normalqa(self, question, history, web_search_context, prompt_template, prompt_folder):
        llm_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "**Instruction 1:**\n {prompt_folder}\n"),
                ("system", "**Instruction 2:**\n {prompt_template}\n"),
                ("system", "**Chat history:** \n {chat_history}\n"),
                ("system", "**Context received from google search:**\n{web_search_context}\n"),
                ("system", "**Answer the question:** {question}"),
            ]
        )
        prompt = llm_prompt.format(prompt_folder=prompt_folder, prompt_template=prompt_template,
                                   chat_history=history, web_search_context=web_search_context, question=question)
        return prompt

    # Handle all above elements --> prompt for llm
    async def question_handler(self, retriever, bm25_retriever, question_request: QuestionRequest,
                               websearchkey: WebSearchKey):
        new_question = False
        # Get history and generate new question
        history = sql_conn.get_chat_history(question_request.conversation_id)[-6::]

        # Nếu web_search là True thì thêm tìm kiếm google search, còn không thì thôi
        if question_request.search_tool == "google_search":
            new_question = await self.reformulate_question(question_request.question, history[::-1])
            google_search = GoogleWebSearch(websearchkey.google_search_key, websearchkey.google_search_id)
            try:
                web_search_context = await google_search.search(new_question)
            except:
                web_search_context = ""
        elif question_request.search_tool == "serper_search":
            new_question = await self.reformulate_question(question_request.question, history[::-1])
            search = SerperSearch(serper_api_key=websearchkey.serper_key)
            try:
                web_search_context = await search.search(new_question)
            except:
                web_search_context = ""
        else:
            web_search_context = ""

        # Nếu prompt template là system rag thì sử dụng retriever để retrieve data, còn không thì thôi
        if retriever:
            if question_request.prompt_template.startswith("__Rag__"):
                if not new_question:
                    new_question = await self.reformulate_question(question_request.question, history[::-1])
                context = await self.retriever(new_question, retriever, bm25_retriever)
                prompt = self.prompt_rag(new_question, context, web_search_context, history,
                                         question_request.prompt_template, question_request.prompt_folder)
            else:
                prompt = self.prompt_normalqa(new_question, history, web_search_context,
                                              question_request.prompt_template, question_request.prompt_folder) if new_question \
                    else self.prompt_normalqa(question_request.question, history, web_search_context,
                                              question_request.prompt_template, question_request.prompt_folder)
            return prompt
        else:
            prompt = self.prompt_normalqa(new_question, history, web_search_context,
                                          question_request.prompt_template, question_request.prompt_folder) if new_question \
                else self.prompt_normalqa(question_request.question, history, web_search_context,
                                          question_request.prompt_template, question_request.prompt_folder)
            return prompt

    async def question_handler_system(self, retriever, bm25_retriever, question_request: QuestionRequest,
                                      websearchkey: WebSearchKey):
        new_question = False
        # Get history and generate new question
        history = sql_conn.get_chat_history_system(question_request.conversation_id)[-6::]
        # Nếu web_search là True thì thêm tìm kiếm google search, còn không thì thôi
        if question_request.search_tool == "google_search":
            new_question = await self.reformulate_question(question_request.question, history[::-1])
            google_search = GoogleWebSearch(websearchkey.google_search_key, websearchkey.google_search_id)
            try:
                web_search_context = await google_search.search(new_question)
            except:
                web_search_context = ""
        elif question_request.search_tool == "serper_search":
            new_question = await self.reformulate_question(question_request.question, history[::-1])
            search = SerperSearch(serper_api_key=websearchkey.serper_key)
            try:
                web_search_context = await search.search(new_question)
            except:
                web_search_context = ""
        else:
            web_search_context = ""

        # Nếu prompt template là system rag thì sử dụng retriever để retrieve data, còn không thì thôi
        if retriever:
            if question_request.prompt_template.startswith("__Rag__"):
                if not new_question:
                    new_question = await self.reformulate_question(question_request.question, history[::-1])
                context = await self.retriever(new_question, retriever, bm25_retriever)
                prompt = self.prompt_rag(new_question, context, web_search_context, history,
                                         question_request.prompt_template, question_request.prompt_folder)
            else:
                prompt = self.prompt_normalqa(new_question, history, web_search_context,
                                              question_request.prompt_template, question_request.prompt_folder) if new_question \
                    else self.prompt_normalqa(question_request.question, history, web_search_context,
                                              question_request.prompt_template, question_request.prompt_folder)
            return prompt
        else:
            prompt = self.prompt_normalqa(new_question, history, web_search_context,
                                          question_request.prompt_template, question_request.prompt_folder) if new_question \
                else self.prompt_normalqa(question_request.question, history, web_search_context,
                                          question_request.prompt_template, question_request.prompt_folder)
            return prompt

    # Streaming response to fastapi endpoint
    async def send_message_openai(self, prompt: str, model: str) -> AsyncIterable[str]:
        callback = AsyncIteratorCallbackHandler()
        self.model_llm = ChatOpenAI(temperature=TEMPERATURE, model=model, streaming=True, callbacks=[callback],
                                    api_key=self.openai_apikey)
        task = asyncio.create_task(
            self.model_llm.ainvoke(prompt)
        )

        try:
            async for token in callback.aiter():
                yield token
        except Exception as e:
            print(f"Caught exception: {e}")
        finally:
            callback.done.set()
        await task

    async def send_message_gemini(self, prompt: str, model: str) -> AsyncIterable[str]:
        self.model_llm = ChatGoogleGenerativeAI(temperature=TEMPERATURE, model=model, streaming=True,
                                                api_key=self.gemini_apikey)
        async for i in self.model_llm.astream(prompt):
            yield i.content
    
    async def rename_conversation(self, history):
        rename_conversation_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", RENAME_CONVERSATION_PROMPT),
                ("system", "Chat history: \n {chat_history}\n"),
            ]
        )
        rename_pt = rename_conversation_prompt.format(chat_history=history)
        new_name = await self.model_reformulate_question.ainvoke(rename_pt)
        return new_name.content


class CheckAPIKey:
    def __init__(self, apikey, type):
        if type == "openaikey" or type == "openai_embedding_key":
            self.model = ChatOpenAI(model="gpt-4o-mini", api_key=apikey)
            self.model.invoke("hello")
        elif type == "geminikey":
            self.model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", api_key=apikey)
            self.model.invoke("hello")


class GoogleWebSearch:
    def __init__(self, google_api_key, google_cse_id):
        self.gg_search = GoogleSearchAPIWrapper(google_api_key=google_api_key, google_cse_id=google_cse_id)
        self.search_tool = GoogleSearchResults(api_wrapper=self.gg_search, num_results=10)

    async def search(self, question):
        results = await self.search_tool.arun(question)
        results = ast.literal_eval(results)
        context = " ".join(i['snippet'] for i in results)
        link = [str(i['link']) for i in results[:3]]
        web_search_context = context + str(link)
        return web_search_context


class SerperSearch:
    def __init__(self, serper_api_key):
        self.search_tool = GoogleSerperAPIWrapper(gl="vn", serper_api_key=serper_api_key)

    async def search(self, question):
        results = await self.search_tool.aresults(question)
        context = " ".join(i['snippet'] for i in results['organic'])
        link = [str(i['link']) for i in results['organic'][:3]]
        web_search_context = context + str(link)
        return web_search_context


