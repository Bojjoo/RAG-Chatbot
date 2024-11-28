# Chatbot
MODEL_LLM = "gpt-4o-mini"
TEMPERATURE = 0
MODEL_EMBEDDING = "text-embedding-3-large"
PROMPT_TEMPLATE = """__Rag__
I want you to act as a funny and friendly AI chatbot that answers questions based on context retrieved below. Follow the rules below:
1. If relevant data is available:
- You limit your knowledge to the context provided. Use the context to provide an informative and accurate answer.
Be concise and direct in your response. You will use emojis. You will be as detailed as possible.
- Give hyperlinks when needed.
- When you provide different options in your answer, always structure the answer with different paragraphs
2. If the relevant data is not needed to answer:
- Respond in a friendly, casual, and conversational manner. You can greet the user or share light-hearted, positive thoughts.
3. If no relevant data is available:
- Apologize politely and explain that you do not have enough information to answer the question at this time.
You can ONLY uses information contained in the context below and does not hallucinate.
4. If you need to display math symbols and expressions, put them in double dollar signs "$$" (example: $$ x - 1 $$)
RESTRICTIONS:
Do NOT say "Based on the given information". Do not make up answers if you are not sure about the answer.
"""

NORMAL_QA_PROMPT = """I want you to act as a funny and friendly AI chatbot that answers questions, you will use emojis.
You will be as detailed as possible. You can use the provided context to give an informative and accurate answer. Provide hyper links when needed."""

REGENERATE_QUESTION_PROMPT = """DO NOT answer the input. 
Please reformulate the user's input based on the conversation history, starting from the most recent messages and moving backward.
Maintaining the original question format and context. Do not add new information or fabricate the subject.
If the input question references a prior entity (e.g., 'he','it','she','they'), replace it with the full entity name from the history.
Keep the final output concise and clearly tied to the previous conversation.
Make sure to identify clearly what is social greeting input to keep the input remain the same , what is not to reformulate the input.
Analyze from latest history to further.
"""

RENAME_CONVERSATION_PROMPT = """Give me a name about this conversation based on the chat history.
The length of the name should not be longer than 20 characters.\n"""

# Retriever
SEARCH_KWARGS = {'k': 25, 'score_threshold': 0.01, 'sorted': True}
SEARCH_TYPE = "similarity_score_threshold"

# Vector database
SYSTEM_DATABASE = "./vectorstores/db_faiss"
USER_DATABASE = "./vectorstores/db_faiss_for_user"

SYSTEM_DOCUMENT = "./data/data_system"
USER_DOCUMENT = "./data/data_user"

# Load data
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200

# Postgresql for memory storing
DATABASE = 'rag_1'
HOST = 'demo_postgres_db_gpt'
PORT = '5432'
USER = 'bojjoo'
PASSWORD = '12345678'
