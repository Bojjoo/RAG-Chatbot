import os
import requests
from api.database.database import SQLDatabase
from streamlit_float import *
from api.config import *
import time
from dotenv import load_dotenv
from datetime import datetime
import secrets
import streamlit as st
from streamlit_extras.bottom_container import bottom
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredWordDocumentLoader
)
import shutil
import tiktoken
import tempfile
import random

tokenizer = tiktoken.get_encoding("cl100k_base")

st.set_page_config(layout="wide")
float_init()

sql_conn = SQLDatabase()
st.session_state["image_files"] = [f for f in os.listdir("./logo/images")]

load_dotenv()
USER_URL = os.getenv("USER_URL")
SYSTEM_URL = os.getenv("SYSTEM_URL")
USER_RETRIEVER = os.getenv("USER_RETRIEVER")
CSV_QA_URL = os.getenv("CSV_QA_URL")
SYSTEM_RETRIEVER = os.getenv("SYSTEM_RETRIEVER")


def handler_input_user(question, conversation_id, user_id, url, model, prompt_template,
                       admin_department, folder_id, prompt_folder, search_tool):
    question_data = {
        "question": question,
        "conversation_id": conversation_id,
        "prompt_template": prompt_template,
        "user_id": user_id,
        "model": model,
        "admin_department": admin_department,
        "folder_id": folder_id,
        "prompt_folder": prompt_folder,
        "search_tool": search_tool
    }
    response = requests.post(url=url, json=question_data, stream=True)

    if response.status_code == 200:
        for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
            yield chunk
    else:
        yield f"Error: {response.status_code} - {response.reason}"


def handler_input_system(question, conversation_id, user_id, url, model,
                         admin_department, folder_id, prompt_template, prompt_folder, search_tool):
    question_data = {
        "question": question,
        "conversation_id": conversation_id,
        "prompt_template": prompt_template,
        "user_id": user_id,
        "model": model,
        "admin_department": admin_department,
        "folder_id": folder_id,
        "prompt_folder": prompt_folder,
        "search_tool": search_tool
    }
    response = requests.post(url=url, json=question_data, stream=True)

    if response.status_code == 200:
        for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
            yield chunk
    else:
        yield f"Error: {response.status_code} - {response.reason}"


def handler_input_csv(question: str, user_id: str, url, model):
    data = {
        "user_id": user_id,
        "question": question,
        "model": model
    }
    response = requests.post(url=url, json=data, stream=True)

    return response.json()


def get_apikey_for_admin(admin_department: str):
    data = {
        "admin_department": admin_department
    }
    url = os.getenv("GET_API_KEY")
    response = requests.post(url=url, json=data)
    return response.json()


def get_retriever(user_id: str, admin_department: str, folder_id: str):
    data = {
        "user_id": user_id,
        "folder_id": folder_id,
        "admin_department": admin_department
    }
    try:
        # Gửi yêu cầu POST đến endpoint FastAPI
        response = requests.post(url=USER_RETRIEVER, json=data)
        if response.status_code == 200:
            # Trả về nội dung phản hồi
            return response.json()
        else:
            # Nếu có lỗi, trả về thông báo lỗi
            return f"Error {response.status_code}: {response.text}"
    except Exception as e:
        return f"Error: {str(e)}"


def get_retriever_admin(admin_department: str, folder_id: str):
    data = {
        "admin_department": admin_department,
        "folder_id": folder_id
    }
    try:
        # Gửi yêu cầu POST đến endpoint FastAPI
        response = requests.post(url=SYSTEM_RETRIEVER, json=data)
        if response.status_code == 200:
            # Trả về nội dung phản hồi
            return response.json()
        else:
            # Nếu có lỗi, trả về thông báo lỗi
            return f"Error {response.status_code}: {response.text}"
    except Exception as e:
        return f"Error: {str(e)}"


def counting_token(file):
    file_extension = os.path.splitext(file.name)[1].lower()
    loaders = {
        '.pdf': PyPDFLoader,
        '.txt': TextLoader,
        '.docx': UnstructuredWordDocumentLoader
    }
    if file_extension not in loaders:
        raise ValueError("Unsupported file type")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_file_path = os.path.join(tmp_dir, file.name)
        with open(tmp_file_path, 'wb') as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
        loader = loaders[file_extension](tmp_file_path)

        contexts = ''.join(doc.page_content for doc in loader.load())
        tokens = tokenizer.encode(contexts)

    return len(tokens), len(contexts)


hide_st_style = """
                <style>
                #MainMenu {visibility: hidden;}
                footer {visibility: hidden;}
                header {visibility: hidden;}
                </style>
                """
st.markdown(hide_st_style, unsafe_allow_html=True)

# Màn hình đăng nhập
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

st.session_state["semantic_chunking"] = False

if not st.session_state["authenticated"]:
    User_tab, Admin_tab = st.tabs(["User", "Admin"])
    st.session_state["User_login"] = False
    st.session_state["Admin_login"] = False

    with User_tab:
        st.title("Login to access the chat")
        tab_login, tab_register = st.tabs(["Login", "Register"])
        with tab_register:
            col1, col2 = st.columns(2)
            with col1:
                with st.container(border=True):
                    new_username = st.text_input("New Username")
                    new_password = st.text_input("New Password", type="password")
                    confirm_password = st.text_input("Confirm Password", type="password")
                    department = st.radio("What is your department?", ["DG1", "DN1"])

                    if st.button("Register"):
                        if new_password != confirm_password:
                            st.warning("Passwords do not match!")
                        elif len(new_username) == 0 or len(new_password) == 0:
                            st.warning("Username and password cannot be empty!")
                        else:
                            register_data = {
                                "user_name": new_username,
                                "password": new_password,
                                "admin_department": department
                            }
                            try:
                                response = requests.post(url=os.getenv("REGISTER_ACCOUNT"), json=register_data)
                                if response.json() == 1:
                                    st.success("Account registered successfully!")
                                    user_id = sql_conn.get_userid_from_username(new_username)
                                    sql_conn.add_folder_user_csvfile(user_id)
                                    sql_conn.add_folder_user_textfile_non_folder(user_id)

                                    # Login ngay sau khi register
                                    st.spinner("Logging in")
                                    time.sleep(2)
                                    data = {
                                        "user_name": new_username,
                                        "password": new_password
                                    }
                                    response = requests.post(url=os.getenv("SIGN_IN_USER"), json=data)
                                    # Kiểm tra nếu mật khẩu đúng
                                    if response.json() != 0:
                                        st.session_state["authenticated"] = True
                                        st.session_state["user_name"] = new_username
                                        st.success("Login successful! Welcome to the chat application.")

                                        # Lấy ID user từ tên user
                                        st.session_state['user_id'] = response.json()

                                        # Lấy admin_department của user_id
                                        st.session_state["admin_department"] = sql_conn.get_admin_department(
                                            st.session_state["user_id"])

                                        # Lấy apikey của admin
                                        st.session_state["get_apikey"] = True
                                        if st.session_state["get_apikey"]:
                                            apikey = get_apikey_for_admin(st.session_state["admin_department"])
                                        st.session_state["get_apikey"] = False

                                        # Lấy db Faiss của user
                                        st.session_state["update_retriever"] = True
                                        folders = sql_conn.get_folders_user(st.session_state["user_id"])
                                        if st.session_state["update_retriever"]:
                                            for i in folders:
                                                user_retriever = get_retriever(st.session_state["user_id"],
                                                                               st.session_state["admin_department"],
                                                                               i[0])
                                        st.session_state["update_retriever"] = False
                                        st.session_state["google_api_key"] = False
                                        st.session_state["serper_api_key"] = False

                                        st.session_state["User_login"] = True

                                        st.rerun()
                                else:
                                    st.warning(f"The user name {new_username} is existed, please choose another user name!")
                            except Exception as e:
                                st.error(f"An error occurred: {str(e)}")
            with col2:
                st.image("./logo/login/user.svg", width=400)

        with tab_login:
            col1, col2 = st.columns(2)
            with col1:
                with st.container(border=True):
                    username = st.text_input("Username")
                    password = st.text_input("Password", type="password")

                    if st.button("Login", key="user_login"):
                        # Lấy mật khẩu từ cơ sở dữ liệu dựa trên username
                        data = {
                            "user_name": username,
                            "password": password
                        }
                        response = requests.post(url=os.getenv("SIGN_IN_USER"), json=data)
                        # Kiểm tra nếu mật khẩu đúng
                        if response.json() != 0:
                            st.session_state["authenticated"] = True
                            st.session_state["user_name"] = username
                            st.success("Login successful! Welcome to the chat application.")

                            # Lấy ID user từ tên user
                            st.session_state['user_id'] = response.json()

                            # Lấy admin_department của user_id
                            st.session_state["admin_department"] = sql_conn.get_admin_department(st.session_state["user_id"])

                            # Lấy apikey của admin
                            st.session_state["get_apikey"] = True
                            if st.session_state["get_apikey"]:
                                apikey = get_apikey_for_admin(st.session_state["admin_department"])
                            st.session_state["get_apikey"] = False

                            # Lấy db Faiss của user
                            st.session_state["update_retriever"] = True
                            folders = sql_conn.get_folders_user(st.session_state["user_id"])
                            if st.session_state["update_retriever"]:
                                for i in folders:
                                    user_retriever = get_retriever(st.session_state["user_id"],
                                                                   st.session_state["admin_department"], i[0])
                            st.session_state["update_retriever"] = False

                            # Lấy file csv của user đã upload
                            get_csv_file_endpoint = os.getenv("GET_CSV_FILE")
                            get_csv_data = {
                                "user_id": st.session_state["user_id"],
                                "admin_department": st.session_state["admin_department"]
                            }
                            response = requests.get(get_csv_file_endpoint, json=get_csv_data)
                            if response.json() == 0:
                                pass
                            else:
                                st.session_state["csv_file"] = response.json()

                            st.session_state["User_login"] = True

                            # check đã có key web search chưa
                            check_gg_websearch_key = {
                                "user_id": st.session_state["user_id"],
                                "admin_department": st.session_state["admin_department"]
                            }
                            gg_key_status = requests.get(url=os.getenv("CHECK_WEBSEARCH_GOOGLE_API"),
                                                          json=check_gg_websearch_key)
                            st.session_state["google_api_key"] = True if gg_key_status.json() == 1 else False

                            check_serper_key = {
                                "user_id": st.session_state["user_id"],
                                "admin_department": st.session_state["admin_department"]
                            }

                            serper_key_status = requests.get(url=os.getenv("CHECK_WEBSEARCH_SERPER_API"),
                                                             json=check_serper_key)
                            st.session_state["serper_api_key"] = True if serper_key_status.json() == 1 else False

                            st.rerun()

                        # Nếu mk sai
                        else:
                            st.warning("Invalid username or password. Please try again.")
            with col2:
                st.image("./logo/login/user.svg", width=400)

    with Admin_tab:
        col1, col2 = st.columns(2)
        with col1:
            with st.container(border=True):
                admin_username = st.text_input("Admin Username")
                password = st.text_input("Admin Password", type="password")

                if st.button("Login", key="admin_login"):
                    # Lấy mật khẩu từ cơ sở dữ liệu dựa trên username
                    data = {
                        "admin_username": admin_username,
                        "admin_password": password
                    }
                    response = requests.post(url=os.getenv("SIGN_IN_ADMIN"), json=data)
                    # Kiểm tra nếu mật khẩu đúng
                    if response.json() != 0:
                        st.session_state["authenticated"] = True
                        st.session_state["user_name"] = admin_username
                        st.success("Login Admin account successful! Welcome to the Admin's monitor.")

                        # Lấy admin_department từ tên admin
                        st.session_state['admin_department'] = response.json()

                        # Lấy apikey của admin
                        st.session_state["get_apikey"] = True
                        if st.session_state["get_apikey"]:
                            apikey = get_apikey_for_admin(st.session_state["admin_department"])
                        st.session_state["get_apikey"] = False

                        # Lấy db Faiss của admin
                        st.session_state["update_retriever"] = True
                        folders = sql_conn.get_folders(st.session_state["admin_department"])
                        if st.session_state["update_retriever"]:
                            for i in folders:
                                user_retriever = get_retriever_admin(st.session_state["admin_department"], i[0])
                        st.session_state["update_retriever"] = False

                        st.session_state["Admin_login"] = True

                        st.rerun()
                    # Nếu mk sai
                    else:
                        st.warning("Invalid username or password. Please try again.")
        with col2:
            st.image("./logo/login/admin.svg", width=400)

# Nếu người dùng đã đăng nhập thành công, hiển thị giao diện chat
if st.session_state["authenticated"]:
    new_header_css = """
        <style>
        .custom-header {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 8%;
            background-color: #849bca;
            color: black;
            padding: 10px;
            z-index: 50;
            display: flex;
            align-items: center;
            justify-content: space-between;
            background-image: url("https://media1.tenor.com/m/zBc1XhcbTSoAAAAd/nyan-cat-rainbow.gif");
            background-size: 6%;
        }

        .custom-header #MainMenu {
            position: relative;
            top: 0;
            right: 0;
            margin-right: 10px;
        }

        #MainMenu {
            visibility: visible;
        }

        header {
            visibility: hidden;
            height: 0;
        }

        .content {
            margin-top: 70px; /* Điều chỉnh để phù hợp với chiều cao của header */
        }
        </style>
        """
    st.markdown(new_header_css, unsafe_allow_html=True)
    st.markdown('''
                    <div class="custom-header">
                        <h1 style="margin:0;"></h1>
                        <!-- Menu sẽ được hiển thị ở đây -->
                        <div></div>
                    </div>
                    ''', unsafe_allow_html=True)

    if st.session_state["User_login"] == True and st.session_state["Admin_login"] == False:
        # Chat with admin's files
        def Chat_Session():

            # Định nghĩa prompt template
            if "prompt_template" not in st.session_state:
                st.session_state["prompt_template"] = PROMPT_TEMPLATE
            if "title_prompt_template" not in st.session_state:
                st.session_state["title_prompt_template"] = "Chat with document"

            with st.sidebar:
                st.info(f"Nice to meet you: {st.session_state['user_name']}", icon=":material/sentiment_satisfied:")
                st.session_state["folders"] = sql_conn.get_folders(st.session_state["admin_department"])

                # Lấy ra tất cả system conversation id
                st.session_state["conversations_system"] = []
                st.session_state["conversation_system_non_folder"] = sql_conn.get_conversation_session_system_non_folder(st.session_state["user_id"])
                st.session_state["conversations_system"].extend([i[0] for i in st.session_state["conversation_system_non_folder"]])

                for folder in st.session_state["folders"]:
                    with st.expander(f"__{folder[1]}__", expanded=True):
                        # Create conversation
                        col_1, col_2 = st.columns([1, 2])
                        with col_1:
                            st.session_state["create_new_conversation"] = True
                            if st.session_state["create_new_conversation"]:
                                conversation_name = "New conversation"
                                if st.button(label="", icon=":material/add_box:",
                                             key="create_conversation_system" + f"{folder[0]}"):
                                    conversation_id = "cv" + datetime.now().strftime("%Y%m%d%H%m") + secrets.token_hex(3)
                                    sql_conn.create_conversation_system(conversation_id, conversation_name, st.session_state["user_id"],
                                                                        folder[0])
                                    # # Lấy danh sách các phiên hội thoại
                                    st.session_state[f"conversations_system_{folder[0]}"] = sql_conn.get_conversation_session_system(st.session_state["user_id"], folder[0])
                                    st.session_state["create_new_conversation"] = False
                                    st.rerun()

                        # All conversations
                        st.session_state[f"conversations_system_{folder[0]}"] = sql_conn.get_conversation_session_system(st.session_state["user_id"], folder[0])
                        # insert all conversation_id in session state
                        st.session_state["conversations_system"].extend([i[0] for i in st.session_state[f"conversations_system_{folder[0]}"]])

                        # Hiển thị conversation của folder đó
                        if f"conversations_system_{folder[0]}" in st.session_state:
                            for conv in st.session_state[f"conversations_system_{folder[0]}"]:
                                conversation_col, option_col = st.columns([5, 1])
                                with conversation_col:
                                    # Duyệt qua toàn bộ danh sách hội thoại với System và hiển thị dưới dạng nút
                                    if st.button(f"{conv[1]}", icon=":material/chat:", key=f"system_{conv[0]}", use_container_width=True):
                                        st.session_state["selected_conversation_id"] = (conv[0], folder[0], folder[1],
                                                                                        folder[4])
                                with option_col:
                                    if st.button(label="", icon=":material/delete:", key="delete" + f'{conv[0]}'):
                                        sql_conn.delete_conversation_system(conv[0])
                                        st.session_state[f"conversations_system_{folder[0]}"] = [c for c in st.session_state[f"conversations_system_{folder[0]}"]
                                                                                                 if c[0] != conv[0]]
                                        st.session_state["conversations_system"].remove(conv[0])
                                        st.rerun()
                st.write("---")
                for conv in st.session_state["conversation_system_non_folder"]:
                    conversation_col, option_col = st.columns([5, 1])
                    with conversation_col:
                        if st.button(f"{conv[1]}", icon=":material/chat:", key=f"system_{conv[0]}", use_container_width=True):
                            st.session_state["selected_conversation_id"] = (conv[0], None, None, None)
                    with option_col:
                        if st.button(label="", icon=":material/delete:", key="delete" + f'{conv[0]}'):
                            sql_conn.delete_conversation_system(conv[0])
                            st.session_state["conversation_system_non_folder"] = [c for c in st.session_state["conversation_system_non_folder"]
                                                                                  if c[0] != conv[0]]
                            st.session_state["conversations_system"].remove(conv[0])
                            st.rerun()

            # Select model
            st.session_state.model = 'gpt-4o-mini'
            model_selection_col, plugin_col, col3 = st.columns([1.5, 1.5, 6.5], vertical_alignment="top")
            with model_selection_col:
                model_selection = st.container()
                with model_selection:
                    option = st.selectbox(
                        label="",
                        options=("gpt-4", "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo",
                                 "gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro", "gemini-1.5-flash-002",
                                 "gemini-1.5-pro-002", "gemini-1.5-flash-8b"),
                        index=None,
                        placeholder="gpt-4o-mini",
                    )
                    if option:
                        st.session_state.model = option
            with plugin_col:
                if "search_tool" not in st.session_state:
                    st.session_state["search_tool"] = None
                if "google_search" not in st.session_state:
                    st.session_state.google_search = False
                if "serper_search" not in st.session_state:
                    st.session_state.serper_search = False
                with st.popover("Plugin", icon=":material/extension:"):
                    def on_google_search_change():
                        if not st.session_state["google_api_key"]:
                            st.session_state.google_search = False

                            @st.dialog("Add your Google search API key")
                            def add_google_key():
                                st.markdown("To get your Google Search API Key and Search Engine ID, [follow the instructions here](https://docs.typingmind.com/plugins/use-web-search-and-image-search)")
                                search_id = st.text_input("Search Engine ID")
                                search_key = st.text_input("Search Engine API Key", type="password")
                                if st.button("", icon=":material/send:", key="add_gg_key_system"):
                                    gg_apikey_data = {
                                        "user_id": st.session_state["user_id"],
                                        "search_id": search_id,
                                        "search_key": search_key
                                    }
                                    response = requests.post(url=os.getenv("SAVE_WEBSEARCH_GOOGLE_API"),
                                                             json=gg_apikey_data)
                                    st.session_state.google_search = True
                                    st.session_state["google_api_key"] = True
                                    st.session_state["search_tool"] = "google_search"
                                    st.session_state.serper_search = False
                                    st.success("Saved")
                                else:
                                    st.session_state["google_api_key"] = False

                            add_google_key()
                        if st.session_state.google_search:
                            st.session_state["search_tool"] = "google_search"
                            st.session_state.serper_search = False

                    def on_serper_search_change():
                        if not st.session_state["serper_api_key"]:
                            st.session_state.serper_search = False

                            @st.dialog("Add your Serper search API key")
                            def add_serper_key():
                                st.markdown("You will receive 2500 free requests from Serper, [register account here](https://serper.dev/)")
                                key = st.text_input("Search API Key", type="password")
                                if st.button("", icon=":material/send:", key="add_serper_key_sytem"):
                                    gg_apikey_data = {
                                        "user_id": st.session_state["user_id"],
                                        "key": key
                                    }
                                    response = requests.post(url=os.getenv("SAVE_WEBSEARCH_SERPER_API"),
                                                             json=gg_apikey_data)
                                    st.session_state.serper_search = True
                                    st.session_state["serper_api_key"] = True
                                    st.session_state["search_tool"] = "serper_search"
                                    st.session_state.google_search = False
                                    st.success("Saved")
                                else:
                                    st.session_state["serper_api_key"] = False

                            add_serper_key()
                        if st.session_state.serper_search:
                            st.session_state["search_tool"] = "serper_search"
                            st.session_state.google_search = False

                    st.toggle(label="🔍Google Web Search", key='google_search', on_change=on_google_search_change,
                              value=st.session_state.google_search)

                    st.toggle(label="🔍Serper Web Search", key="serper_search", on_change=on_serper_search_change,
                              value=st.session_state.serper_search)

                    if not st.session_state.google_search and not st.session_state.serper_search:
                        st.session_state["search_tool"] = ""
                    st.markdown(st.session_state["search_tool"])

            css_plugin_col = float_css_helper(top="27px", z_index="100")
            css_model_selection_col = float_css_helper(top="0px", z_index="100")
            plugin_col.float(css_plugin_col)
            model_selection_col.float(css_model_selection_col)
            with bottom():
                empty_col_1, input_col, empty_col = st.columns([1.25, 8, 1.25], vertical_alignment="top")
                with input_col:
                    chat_input_container = st.container()
                    with chat_input_container:
                        st.session_state["question"] = st.chat_input("What do you want to know?")
                    css_chat_input_container = float_css_helper(bottom="27px", z_index="100")
                    chat_input_container.float(css_chat_input_container)
            # Chat session
            if "selected_conversation_id" in st.session_state and st.session_state["selected_conversation_id"][0] not in st.session_state["conversations_system"]:
                del st.session_state["selected_conversation_id"]
                del st.session_state["messages"]

            # Hiển thị lịch sử hội thoại của phiên đã chọn
            if "messages" not in st.session_state:
                st.session_state.messages = []
            if "selected_conversation_id" in st.session_state:
                chat_history = sql_conn.get_chat_history_system(st.session_state["selected_conversation_id"][0])
                # Cập nhật tin nhắn vào session_state.messages nếu có lịch sử
                st.session_state.messages = [
                    {"role": "user" if sender == "human" else "assistant", "output": message}
                    for sender, message in chat_history
                ] if chat_history else []
                # Nếu không có lịch sử chat thì hiển thị các prompt template của folder đó
                if not chat_history:
                    prompt_template = sql_conn.get_templates_folder(st.session_state["selected_conversation_id"][1])
                    try:
                        pt_container = st.container()
                        with pt_container:
                            cols = st.columns(len(prompt_template))
                            for i in range(len(prompt_template)):
                                with cols[i]:
                                    if st.button(prompt_template[i][1]):
                                        st.session_state["question"] = prompt_template[i][1]
                                        pt_container.empty()
                                        st.rerun()
                            pt_container_css = float_css_helper(bottom="400px")
                            pt_container.float(pt_container_css)
                    except:
                        pass

            # Check web search key
            if st.session_state["question"] and st.session_state["search_tool"] == "google_search" and not st.session_state["google_api_key"]:
                st.error("Please add your Google search API key")
            elif st.session_state["question"] and st.session_state["search_tool"] == "serper_search" and not st.session_state["serper_api_key"]:
                st.error("Please add your Serper search API key")
            # Hiển thị các tin nhắn trong phiên hội thoại đã chọn
            if "messages" in st.session_state:
                for message in st.session_state.messages:
                    with st.chat_message(message["role"]):
                        st.markdown(message["output"])
            # try:
            if "selected_conversation_id" in st.session_state:
                # Gửi tin nhắn mới trong giao diện chat
                if st.session_state["question"]:
                    st.chat_message("user").markdown(st.session_state["question"])
                    st.session_state.messages.append({"role": "user", "output": st.session_state["question"]})
                    with st.chat_message("assistant"):
                        assistant_message = st.empty()

                        prompt = st.session_state["prompt_template"] if st.session_state["selected_conversation_id"][1] else NORMAL_QA_PROMPT

                        response_stream = handler_input_system(
                                       st.session_state["question"], st.session_state["selected_conversation_id"][0],
                                       st.session_state["user_id"], SYSTEM_URL,
                                       st.session_state.model, st.session_state["admin_department"],
                                       st.session_state["selected_conversation_id"][1] or "", prompt,
                                       st.session_state["selected_conversation_id"][3] or "",
                                       st.session_state["search_tool"]
                            )
                        # Stream and display the assistant's response
                        output = ""
                        for token in response_stream:
                            output += token
                            assistant_message.markdown(output)
                            time.sleep(0.01)
                        st.session_state.messages.append({"role": "assistant", "output": output})

                    if output.startswith('Error'):
                        st.warning("Missing API key! Contact your admin to provide API key!")
                    else:
                        sender = ['human', 'ai']
                        sql_conn.insert_chat_system(st.session_state["selected_conversation_id"][0], sender[0], st.session_state["question"])
                        sql_conn.insert_chat_system(st.session_state["selected_conversation_id"][0], sender[1], output)

                        # Đổi tên conversation nêu tên vẫn còn là new conversation
                        conversation_name = sql_conn.get_conversation_name_from_conversationid_system(
                                                                    st.session_state["selected_conversation_id"][0])
                        if conversation_name == "New conversation":
                            rename_conversation_endpoint = os.getenv("RENAME_CONVERSATION")
                            data_for_rename = {
                                "history": f"(human:{st.session_state['question'][:200]}); (ai: {output[:500]})",
                                "admin_department": st.session_state["admin_department"]
                            }
                            new_name = requests.post(rename_conversation_endpoint, json=data_for_rename)
                            sql_conn.change_conversation_name_system(st.session_state["selected_conversation_id"][0],
                                                                     new_name.json().strip('"'))
                            st.rerun()

            else:
                x = len(st.session_state["folders"])
                num_rows = x // 4 if x % 4 == 0 else x // 4 + 1
                for i in range(num_rows):
                    cols = st.columns(4)  # Tạo 3 cột trong mỗi hàng
                    for j in range(4):
                        index = i * 4 + j
                        if index < x:
                            # Hiển thị tên folder vào cột tương ứng
                            with cols[j]:
                                with st.container(border=True):
                                    image_col, detail_col = st.columns([1, 2])
                                    with image_col:
                                        if len(st.session_state["folders"][index][2]) > 0:
                                            image_path = st.session_state["folders"][index][2]
                                        else:
                                            random_image = random.choice(st.session_state["image_files"])
                                            image_path = os.path.join("./logo/images/", random_image)
                                        st.image(image_path, width=50)
                                        if st.button("Start chat", key=f"start_chat_{index}"):
                                            conversation_name = "New conversation"
                                            conversation_id = "cv" + datetime.now().strftime(
                                                "%Y%m%d%H%m") + secrets.token_hex(3)
                                            sql_conn.create_conversation_system(conversation_id, conversation_name,
                                                                                st.session_state["user_id"],
                                                                                st.session_state["folders"][index][0])
                                            # # Lấy danh sách các phiên hội thoại
                                            st.session_state[
                                                f"conversations_system_{folder[0]}"] = sql_conn.get_conversation_session_system(
                                                st.session_state["user_id"], folder[0])
                                            st.session_state["selected_conversation_id"] = (conversation_id,
                                                                                            st.session_state["folders"][
                                                                                                index][0],
                                                                                            st.session_state["folders"][
                                                                                                index][1],
                                                                                            st.session_state["folders"][
                                                                                                index][4])
                                            st.rerun()
                                    with detail_col:
                                        st.markdown(f'<div style="text-align:left;"><strong>{st.session_state["folders"][index][1]}</strong></div>',
                                                    unsafe_allow_html=True)
                                        st.markdown(f'<div style="text-align:left;">{st.session_state["folders"][index][3]}</div>',
                                                    unsafe_allow_html=True)

                if st.session_state["question"]:
                    # create a conversation first
                    conversation_name = "New conversation"
                    conversation_id = "cv" + datetime.now().strftime("%Y%m%d%H%m") + secrets.token_hex(3)
                    sql_conn.create_conversation_system_non_folder(conversation_id, conversation_name,
                                                                   st.session_state["user_id"])
                    st.session_state["selected_conversation_id"] = (conversation_id, None, None, None)
                    st.session_state["conversations_system"].append(conversation_id)

                    st.chat_message("user").markdown(st.session_state["question"])
                    st.session_state.messages.append({"role": "user", "output": st.session_state["question"]})

                    with st.chat_message("assistant"):
                        assistant_message = st.empty()

                        prompt = NORMAL_QA_PROMPT
                        response_stream = handler_input_system(
                            st.session_state["question"], st.session_state["selected_conversation_id"][0],
                            st.session_state["user_id"], SYSTEM_URL,
                            st.session_state.model, st.session_state["admin_department"], "", prompt, "",
                            st.session_state["search_tool"]
                        )
                        # Stream and display the assistant's response
                        output = ""
                        for token in response_stream:
                            output += token
                            assistant_message.markdown(output)
                            time.sleep(0.01)
                        st.session_state.messages.append({"role": "assistant", "output": output})

                    if output.startswith('Error'):
                        st.warning("Missing API key! Contact your admin to provide API key!")
                    else:
                        sender = ['human', 'ai']
                        sql_conn.insert_chat_system(st.session_state["selected_conversation_id"][0], sender[0], st.session_state["question"])
                        sql_conn.insert_chat_system(st.session_state["selected_conversation_id"][0], sender[1], output)

                    # Đổi tên conversation nêu tên vẫn còn là new conversation
                    conversation_name = sql_conn.get_conversation_name_from_conversationid_system(st.session_state["selected_conversation_id"][0])
                    if conversation_name == "New conversation":
                        rename_conversation_endpoint = os.getenv("RENAME_CONVERSATION")
                        data_for_rename = {
                            "history": f"(human:{st.session_state['question'][:200]}); (ai: {output[:500]})",
                            "admin_department": st.session_state["admin_department"]
                        }
                        new_name = requests.post(rename_conversation_endpoint, json=data_for_rename)
                        sql_conn.change_conversation_name_system(st.session_state["selected_conversation_id"][0],
                                                                 new_name.json().strip('"'))
                        st.rerun()

        # Chat with user's files
        def Chat_With_Files():
            # Định nghĩa prompt template
            if "prompt_template_user" not in st.session_state:
                st.session_state["prompt_template_user"] = NORMAL_QA_PROMPT
            if "title_prompt_template_user" not in st.session_state:
                st.session_state["title_prompt_template_user"] = "Normal QA"

            with (st.sidebar):
                st.info(f"Nice to meet you: {st.session_state['user_name']}", icon=":material/sentiment_satisfied:")
                #st.session_state["conversations_user_text"] = sql_conn.get_conversation_session_user_textfile(st.session_state["user_id"])
                st.header("Create Folder Project", divider='orange')

                # Tạo folder của user
                @st.dialog("Create Folder", width="large")
                def create_folder():
                    folder_name = st.text_input("__Name of the folder:__", placeholder="New folder")
                    if len(folder_name) == 0:
                        folder_name = "New folder"
                    # Thêm prompt
                    prompt = st.text_area("""__Project Context & Instructions:__\n
This will be appended to the system instruction for all chats in this project. 
Note that this does not override, but "appended" on top of the global system instruction and agent-specific instructions.""",
                                          max_chars=5000)

                    # Upload file
                    uploaded_file = st.file_uploader("Choose a file", type=["pdf", "docx"], key="user_upload_file")

                    create_folder_button = st.button(key="Create folder user", icon=":material/create_new_folder:", label="")
                    # Kiểm tra nếu người dùng chọn file
                    if uploaded_file:
                        if st.toggle(label="Semantic chunking", key="Semantic_chunking_upload_file"):
                            st.session_state["semantic_chunking"] = True
                            st.info("""Semantic chunking helps the RAG system more accurately understand the context of the file.
However, it could increase the token usage and take longer time.""", icon="ℹ️")
                        upload_file_endpoint = os.getenv("UPLOAD_DATA")
                        if create_folder_button:
                            # Gửi POST request với file trực tiếp từ Streamlit lên FastAPI
                            with st.spinner("Creating..."):
                                try:
                                    folder_id = "fd" + datetime.now().strftime("%Y%m%d%H%m") + secrets.token_hex(3)
                                    sql_conn.add_folder_user(folder_id, folder_name, st.session_state["user_id"],
                                                             prompt=prompt)
                                    # Định nghĩa multipart-form cho file và các thông tin khác
                                    files = {"file": (uploaded_file.name, uploaded_file)}  # , "application/pdf"
                                    data = {
                                            "user_id": st.session_state["user_id"],
                                            "folder_id": folder_id,
                                            "semantic_chunking": st.session_state["semantic_chunking"]
                                            }
                                    # Gửi request lên FastAPI
                                    response = requests.post(upload_file_endpoint, files=files, data=data)

                                    # Hiển thị phản hồi
                                    if response.status_code == 200:
                                        st.success(response.json())
                                    else:
                                        st.error(
                                            f"Failed to upload file. Error {response.status_code}: {response.text}. Please check your API key!")
                                except:
                                    st.warning("Incorrect API key provided, please make sure your API key is correct!")
                            # Update lai retriever
                            st.session_state["update_retriever"] = True
                            if st.session_state["update_retriever"]:
                                retriever_status = get_retriever(st.session_state["user_id"],
                                                                 st.session_state["admin_department"], folder_id)
                            st.session_state["update_retriever"] = False
                            st.session_state["semantic_chunking"] = False

                            st.session_state["add_folder"] = False
                            st.rerun()
                    else:
                        if create_folder_button:
                            folder_id = "fd" + datetime.now().strftime("%Y%m%d%H%m") + secrets.token_hex(3)
                            sql_conn.add_folder_user(folder_id, folder_name, st.session_state["user_id"],
                                                     prompt=prompt)
                            # Update lai retriever
                            st.session_state["update_retriever"] = True
                            if st.session_state["update_retriever"]:
                                retriever_status = get_retriever(st.session_state["user_id"],
                                                                 st.session_state["admin_department"], folder_id)
                            st.session_state["update_retriever"] = False
                            st.session_state["add_folder"] = False
                            st.rerun()

                if st.button(label="Create Folder", icon=":material/create_new_folder:", key="create_folder_user",
                             use_container_width=True):
                    create_folder()

                st.write("---")
                st.session_state["folders_user"] = sql_conn.get_folders_user(st.session_state["user_id"])

                # Lấy ra tất cả conversation id
                st.session_state["conversations_user_text"] = []
                st.session_state["conversation_user_non_folder"] = sql_conn.get_conversation_session_user_textfile_non_folder(st.session_state["user_id"])
                st.session_state["conversations_user_text"].extend([i[0] for i in st.session_state["conversation_user_non_folder"]])

                for folder in st.session_state["folders_user"]:
                    with st.expander(folder[1]):

                        # Create conversation
                        col_1, col_2, col_3 = st.columns([1, 1, 1])
                        with col_1:
                            st.session_state["create_new_conversation"] = True
                            con_type = "text_file"
                            if st.session_state["create_new_conversation"]:
                                conversation_name = "New conversation"
                                if st.button(label="", icon=":material/add_box:",
                                             key="create_conversation_user" + f"{folder[0]}", use_container_width=True):
                                    sql_conn.create_conversation(conversation_name, folder[0], con_type)
                                    # # Lấy danh sách các phiên hội thoại
                                    st.session_state[f"conversations_user_{folder[0]}"] = sql_conn.get_conversation_session_user_textfile(folder[0])

                                    st.session_state["create_new_conversation"] = False
                                    st.rerun()
                        # Cột edit folder
                        with col_2:
                            @st.dialog("Edit your folder", width="large")
                            def edit_user_folder(folder):
                                new_name = st.text_input("Name of the folder:", value=folder[1],
                                                         key="edit" + f"{folder[0]}faku")
                                new_prompt = st.text_area("Project Context & Instructions:",
                                                          key="text_area" + f"{folder[0]}", max_chars=10000,
                                                          value=folder[2])

                                # nếu user không nhập nội dung mới mà lỡ bấm save thì vẫn giữ nguyên nội dung cũ
                                if len(new_name) == 0:
                                    new_name = folder[1]
                                if len(new_prompt) == 0:
                                    new_prompt = folder[2]

                                # Xóa file nếu muốn
                                files = sql_conn.get_folder_files_user(folder[0])
                                i = 0
                                for file_name, size in files:
                                    col1, col2 = st.columns([5, 1])
                                    with col1:
                                        st.markdown(f"📄 {file_name} ({size:.2f} MB)", unsafe_allow_html=True)
                                    with col2:
                                        delete_user_file_endpoint = os.getenv("DELETE_FILE")
                                        if st.button(label="", icon=":material/delete:", key=i + 1,
                                                     use_container_width=True):
                                            delete_data = {
                                                "file_name": file_name,
                                                "user_id": st.session_state["user_id"],
                                                "folder_id": folder[0]
                                            }
                                            response = requests.delete(delete_user_file_endpoint, json=delete_data)
                                            st.success(f"{file_name} deleted successfully!")

                                            # Update lai retriever
                                            st.session_state["update_retriever"] = True
                                            if st.session_state["update_retriever"]:
                                                retriever_status = get_retriever(st.session_state["user_id"],
                                                                                 st.session_state["admin_department"], folder[0])
                                            st.markdown(retriever_status)
                                            st.session_state["update_retriever"] = False
                                            st.rerun()

                                    i += 1
                                # Thêm file nếu muốn
                                uploaded_file = st.file_uploader("Choose a file", type=["pdf", "docx"],
                                                                 key="upuserfile" + folder[0])
                                # Kiểm tra nếu người dùng chọn file
                                if uploaded_file:
                                    if st.toggle(label="Semantic chunking", key="Semantic_chunking_upload_file"):
                                        st.session_state["semantic_chunking"] = True
                                        st.info("""Semantic chunking helps the RAG system more accurately understand the context of the file. 
However, it could increase the token usage and take longer time.""", icon="ℹ️")
                                    upload_file_endpoint = os.getenv("UPLOAD_DATA")

                                    if st.button(label="Add document", icon=":material/upload:",
                                                 key="add_document"+folder[0]):
                                        # Gửi POST request với file trực tiếp từ Streamlit lên FastAPI
                                        with st.spinner("Adding..."):
                                            # Định nghĩa multipart-form cho file và các thông tin khác
                                            files = {"file": (uploaded_file.name, uploaded_file)}  # , "application/pdf"
                                            data = {"user_id": st.session_state["user_id"],
                                                    "folder_id": folder[0],
                                                    "semantic_chunking": st.session_state["semantic_chunking"]
                                                    }

                                            # Gửi request lên FastAPI
                                            response = requests.post(upload_file_endpoint, files=files, data=data)

                                            # Hiển thị phản hồi
                                            if response.status_code == 200:
                                                st.success(response.json())
                                            else:
                                                st.error(
                                                    f"Failed to upload file. Error {response.status_code}: {response.text}")

                                        # Update lai retriever
                                        st.session_state["update_retriever"] = True
                                        if st.session_state["update_retriever"]:
                                            retriever_status = get_retriever(st.session_state["user_id"],
                                                                             st.session_state["admin_department"], folder[0])
                                        st.session_state["update_retriever"] = False
                                        st.session_state["semantic_chunking"] = False
                                        st.rerun()
                                if st.button("Save", key="save folder user" + folder[0]):
                                    sql_conn.update_folder_user(folder[0], new_name,
                                                                prompt=new_prompt)

                            if st.button(label="", icon=":material/edit:", key="edit_user_folder" + f"{folder[0]}",
                                         use_container_width=True):
                                edit_user_folder(folder)
                        with col_3:
                            delete_folder_endpoint = os.getenv("DELETE_FOLDER_USER")

                            @st.dialog("Delete Folder")
                            def delete_folder(folder):
                                st.markdown("Are you sure you want to delete this folder?")
                                if st.button("Yes", icon=":material/folder_delete:",
                                             key="delete this folder" + f"{folder[0]}"):
                                    delete_folder_data = {"folder_id": folder[0],
                                                          "user_id": st.session_state["user_id"]}
                                    response = requests.delete(delete_folder_endpoint, json=delete_folder_data)
                                    st.success(f"Folder {folder[1]} deleted successfully!")

                                    # Update lai retriever
                                    st.session_state["update_retriever"] = True
                                    if st.session_state["update_retriever"]:
                                        retriever_status = get_retriever(st.session_state["user_id"],
                                                                         st.session_state["admin_department"],
                                                                         folder[0])
                                    st.session_state["update_retriever"] = False

                                    st.rerun()
                            if st.button(label="", icon=":material/delete:", key="delete" + f"{folder[0]}",
                                         use_container_width=True):
                                delete_folder(folder)


                        # All conversations
                        st.session_state[f"conversations_user_{folder[0]}"] = sql_conn.get_conversation_session_user_textfile(folder[0])
                        # Correct way to populate the conversation IDs
                        st.session_state["conversations_user_text"].extend([i[0] for i in st.session_state[f"conversations_user_{folder[0]}"]])

                        # Hiển thị conversation của folder đó
                        if f"conversations_user_{folder[0]}" in st.session_state:
                            for conv in st.session_state[f"conversations_user_{folder[0]}"]:
                                conversation_col, option_col = st.columns([5, 1])
                                with conversation_col:
                                    # Duyệt qua toàn bộ danh sách hội thoại và hiển thị dưới dạng nút
                                    if st.button(f"{conv[1]}", icon=":material/chat:", key=f"user_{folder[0]}_{conv[0]}"
                                                 , use_container_width=True):
                                        st.session_state["selected_conversation_id"] = (conv[0], folder[0], folder[1],
                                                                                        folder[2])
                                with option_col:
                                    if st.button(label="", icon=":material/delete:", key="delete" + f'{conv[0]}'):
                                        sql_conn.delete_conversation(conv[0])
                                        st.session_state[f"conversations_user_{folder[0]}"] = [c for c in st.session_state[f"conversations_user_{folder[0]}"]
                                                                                               if c[0] != conv[0]]
                                        st.session_state["conversations_user_text"].remove(conv[0])
                                        st.rerun()

                st.write("---")
                for conv in st.session_state["conversation_user_non_folder"]:
                    conversation_col, option_col = st.columns([5, 1])
                    with conversation_col:
                        if st.button(f"{conv[1]}", icon=":material/chat:", key=f"user_{conv[0]}",
                                     use_container_width=True):
                            st.session_state["selected_conversation_id"] = (conv[0], None, None, None)
                    with option_col:
                        if st.button(label="", icon=":material/delete:", key="delete" + f'{conv[0]}'):
                            sql_conn.delete_conversation(conv[0])
                            st.session_state["conversation_user_non_folder"] = [c for c in st.session_state["conversation_user_non_folder"]
                                                                                if c[0] != conv[0]]
                            st.session_state["conversations_user_text"].remove(conv[0])
                            st.rerun()

            st.session_state.model = 'gpt-4o-mini'
            model_selection_col, plugin_col, col3 = st.columns([1.5, 1.5, 6.5], vertical_alignment="top")
            with model_selection_col:
                model_selection = st.container()
                with model_selection:
                    option = st.selectbox(
                        label="",
                        options=("gpt-4", "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo",
                                 "gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro", "gemini-1.5-flash-002",
                                 "gemini-1.5-pro-002", "gemini-1.5-flash-8b"),
                        index=None,
                        placeholder="gpt-4o-mini",
                    )
                    if option:
                        st.session_state.model = option
            with plugin_col:
                if "search_tool" not in st.session_state:
                    st.session_state["search_tool"] = None
                if "google_search" not in st.session_state:
                    st.session_state.google_search = False
                if "serper_search" not in st.session_state:
                    st.session_state.serper_search = False
                with st.popover("Plugin", icon=":material/extension:"):
                    def on_google_search_change():
                        if not st.session_state["google_api_key"]:
                            st.session_state.google_search = False
                            @st.dialog("Add your Google search API key")
                            def add_google_key():
                                st.markdown("To get your Google Search API Key and Search Engine ID, [follow the instructions here](https://docs.typingmind.com/plugins/use-web-search-and-image-search)")
                                search_id = st.text_input("Search Engine ID")
                                search_key = st.text_input("Search Engine API Key", type="password")
                                if st.button("", icon=":material/send:", key="add_gg_key_user"):
                                    gg_apikey_data = {
                                        "user_id": st.session_state["user_id"],
                                        "search_id": search_id,
                                        "search_key": search_key
                                    }
                                    response = requests.post(url=os.getenv("SAVE_WEBSEARCH_GOOGLE_API"),
                                                             json=gg_apikey_data)
                                    st.session_state.google_search = True
                                    st.session_state["google_api_key"] = True
                                    st.session_state["search_tool"] = "google_search"
                                    st.session_state.serper_search = False
                                    st.success("Saved")
                            add_google_key()
                        if st.session_state.google_search:
                            st.session_state["search_tool"] = "google_search"
                            st.session_state.serper_search = False

                    def on_serper_search_change():
                        if not st.session_state["serper_api_key"]:
                            st.session_state.serper_search = False
                            @st.dialog("Add your Serper search API key")
                            def add_serper_key():
                                st.markdown("You will receive 2500 free requests from Serper, [register account here](https://serper.dev/)")
                                key = st.text_input("Search API Key", type="password")
                                if st.button("", icon=":material/send:", key="add_serper_key_user"):
                                    gg_apikey_data = {
                                        "user_id": st.session_state["user_id"],
                                        "key": key
                                    }
                                    response = requests.post(url=os.getenv("SAVE_WEBSEARCH_SERPER_API"),
                                                             json=gg_apikey_data)
                                    st.session_state.serper_search = True
                                    st.session_state["serper_api_key"] = True
                                    st.session_state["search_tool"] = "serper_search"
                                    st.session_state.google_search = False
                                    st.success("Saved")
                            add_serper_key()
                        if st.session_state.serper_search:
                            st.session_state["search_tool"] = "serper_search"
                            st.session_state.google_search = False

                    st.toggle(label="🔍Google Web Search", key='google_search', on_change=on_google_search_change)

                    st.toggle(label="🔍Serper Web Search", key="serper_search", on_change=on_serper_search_change)

                    if not st.session_state.google_search and not st.session_state.serper_search:
                        st.session_state["search_tool"] = ""
                    st.markdown(st.session_state["search_tool"])

            css_plugin_col = float_css_helper(top="27px", z_index="100")
            css_model_selection_col = float_css_helper(top="0px", z_index="100")
            plugin_col.float(css_plugin_col)
            model_selection_col.float(css_model_selection_col)
            col1, col2 = st.columns([8, 1.5], vertical_alignment="top")
            with col2:
                st.write("---")
                st.markdown(f'Prompt Template is using: {st.session_state["title_prompt_template_user"]}')
                col_1, col_2 = st.columns([3, 1])
                with col_1:
                    if st.session_state["title_prompt_template_user"] == "Normal QA":
                        with st.popover("Normal QA", use_container_width=True):
                            st.markdown(NORMAL_QA_PROMPT)
                    elif st.session_state["title_prompt_template_user"] == "Chat with document":
                        with st.popover("Chat with document", use_container_width=True):
                            st.markdown(f"{PROMPT_TEMPLATE}")
                with col_2:
                    if st.button("", key='switch_prompt_template', icon=":material/change_circle:", use_container_width=True):
                        if st.session_state["title_prompt_template_user"] == "Normal QA":
                            st.session_state["prompt_template_user"] = PROMPT_TEMPLATE
                            st.session_state["title_prompt_template_user"] = "Chat with document"
                        elif st.session_state["title_prompt_template_user"] == "Chat with document":
                            st.session_state["prompt_template_user"] = NORMAL_QA_PROMPT
                            st.session_state["title_prompt_template_user"] = "Normal QA"
                        st.rerun()
            css_col2 = float_css_helper(top="70px")
            col2.float(css_col2)

            with bottom():
                empty_col_1, input_col, empty_col = st.columns([1.25, 8, 1.25], vertical_alignment="top")
                with input_col:
                    chat_input_container = st.container()
                    with chat_input_container:
                        st.session_state["question"] = st.chat_input("What do you want to know?")
                    css_chat_input_container = float_css_helper(bottom="27px", z_index="100")
                    chat_input_container.float(css_chat_input_container)

            with col1:
                if "selected_conversation_id" in st.session_state and st.session_state["selected_conversation_id"][0] not in st.session_state["conversations_user_text"]:
                    del st.session_state["selected_conversation_id"]
                    del st.session_state["messages"]

                # Phần hiển thị chat
                # Hiển thị lịch sử hội thoại của phiên đã chọn
                if "messages" not in st.session_state:
                    st.session_state.messages = []

                if "selected_conversation_id" in st.session_state:
                    chat_history = sql_conn.get_chat_history(st.session_state["selected_conversation_id"][0])
                    st.session_state.messages = []
                    # Cập nhật tin nhắn vào session_state.messages nếu có lịch sử
                    if chat_history:
                        st.session_state.messages = [
                            {"role": "user" if sender == "human" else "assistant", "output": message}
                            for sender, message in chat_history
                        ]

                # Hiển thị các tin nhắn trong phiên hội thoại đã chọn
                if "messages" in st.session_state:
                    for message in st.session_state.messages:
                        with st.chat_message(message["role"]):
                            st.markdown(message["output"])
                # try:
                if "selected_conversation_id" in st.session_state:
                    # Gửi tin nhắn mới trong giao diện chat
                    if st.session_state["question"]:
                        st.chat_message("user").markdown(st.session_state["question"])
                        st.session_state.messages.append({"role": "user", "output": st.session_state["question"]})

                        with st.chat_message("assistant"):
                            assistant_message = st.empty()

                            prompt_template = st.session_state["prompt_template_user"]
                            response_stream = handler_input_user(
                                st.session_state["question"], st.session_state["selected_conversation_id"][0],
                                st.session_state["user_id"], USER_URL, st.session_state.model, prompt_template,
                                st.session_state["admin_department"], st.session_state["selected_conversation_id"][1] or "",
                                st.session_state["selected_conversation_id"][3] or "", st.session_state["search_tool"])

                            # Stream and display the assistant's response
                            output = ""
                            for token in response_stream:
                                output += token
                                assistant_message.markdown(output)
                                time.sleep(0.01)
                            st.session_state.messages.append({"role": "assistant", "output": output})

                        if output.startswith('Error'):
                            st.warning("Missing API key! Contact your admin to provide API key!")
                        else:
                            sql_conn.insert_chat(st.session_state["selected_conversation_id"][0], 'human', st.session_state["question"])
                            sql_conn.insert_chat(st.session_state["selected_conversation_id"][0], 'ai', output)

                            # Đổi tên conversation nêu tên vẫn còn là new conversation
                            conversation_name = sql_conn.get_conversation_name_from_conversationid(st.session_state["selected_conversation_id"][0])
                            if conversation_name == "New conversation":
                                rename_conversation_endpoint = os.getenv("RENAME_CONVERSATION")
                                data_for_rename = {
                                    "history": f"(human:{st.session_state['question'][:200]}); (ai: {output[:500]})",
                                    "admin_department": st.session_state["admin_department"]
                                }
                                new_name = requests.post(rename_conversation_endpoint, json=data_for_rename)
                                sql_conn.change_conversation_name(st.session_state["selected_conversation_id"][0],
                                                                  new_name.json().strip('"'))
                                st.rerun()

                else:
                    if st.session_state["question"]:
                        # create a conversation first
                        conversation_name = "New conversation"
                        conversation_id = "cv" + datetime.now().strftime("%Y%m%d%H%m") + secrets.token_hex(3)
                        sql_conn.create_conversation_user_textfile_non_folder(conversation_id, conversation_name,
                                                                              st.session_state["user_id"])
                        st.session_state["selected_conversation_id"] = (conversation_id, None, None, None)
                        st.session_state["conversations_user_text"].append(conversation_id)

                        st.chat_message("user").markdown(st.session_state["question"])
                        st.session_state.messages.append({"role": "user", "output": st.session_state["question"]})
                        with st.chat_message("assistant"):
                            assistant_message = st.empty()

                            prompt = NORMAL_QA_PROMPT
                            response_stream = handler_input_user(
                                st.session_state["question"], st.session_state["selected_conversation_id"][0],
                                st.session_state["user_id"], USER_URL, st.session_state.model, prompt,
                                st.session_state["admin_department"], "", "", st.session_state["search_tool"]
                            )
                            # Stream and display the assistant's response
                            output = ""
                            for token in response_stream:
                                output += token
                                assistant_message.markdown(output)
                                time.sleep(0.01)
                            st.session_state.messages.append({"role": "assistant", "output": output})

                        if output.startswith('Error'):
                            st.warning("Missing API key! Contact your admin to provide API key!")
                        else:
                            sql_conn.insert_chat(st.session_state["selected_conversation_id"][0], 'human', st.session_state["question"])
                            sql_conn.insert_chat(st.session_state["selected_conversation_id"][0], 'ai', output)

                        # Đổi tên conversation nêu tên vẫn còn là new conversation
                        conversation_name = sql_conn.get_conversation_name_from_conversationid(st.session_state["selected_conversation_id"][0])
                        if conversation_name == "New conversation":
                            rename_conversation_endpoint = os.getenv("RENAME_CONVERSATION")
                            data_for_rename = {
                                "history": f"(human:{st.session_state['question'][:200]}); (ai: {output[:500]})",
                                "admin_department": st.session_state["admin_department"]
                            }
                            new_name = requests.post(rename_conversation_endpoint, json=data_for_rename)
                            sql_conn.change_conversation_name(st.session_state["selected_conversation_id"][0],
                                                              new_name.json().strip('"'))
                            st.rerun()

        def Chat_With_CSVFile():
            with st.sidebar:
                st.session_state["conversations_user_csv"] = sql_conn.get_conversation_session_user_csvfile(st.session_state["user_id"])
                uploaded_file = st.file_uploader("Choose a file", type=["csv", "xls", "xlsx", "xlsm", "xlsb"])

                # Kiểm tra nếu người dùng chọn file
                if uploaded_file is not None:
                    # Xác định URL của endpoint FastAPI và user_id
                    upload_file_endpoint = os.getenv("UPLOAD_CSV_FILE")

                    if st.button(label="Upload File", icon=":material/upload_file:"):
                        # Gửi POST request với file trực tiếp từ Streamlit lên FastAPI
                        with st.spinner("Uploading..."):
                            try:
                                # Định nghĩa multipart-form cho file và các thông tin khác
                                files = {"file": (uploaded_file.name, uploaded_file)}
                                csv_data = {
                                    "user_id": st.session_state["user_id"],
                                    "admin_department": st.session_state["admin_department"]
                                }

                                # Gửi request lên FastAPI
                                response = requests.post(upload_file_endpoint, files=files, data=csv_data)
                                st.session_state["csv_file"] = response.json()
                                # Hiển thị phản hồi
                                if response.status_code == 200:
                                    st.success("Saved dataframe successfully!")

                                else:
                                    st.error(f"Failed to upload file. Error {response.status_code}: {response.text}")
                            except Exception as e:
                                st.error(f"An error occurred: {str(e)}")

                if "csv_file" in st.session_state:
                    i = 0
                    for file in st.session_state["csv_file"]:
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            st.markdown(f"📄 {file}", unsafe_allow_html=True)
                        with col2:
                            delete_file_endpoint = os.getenv("DELETE_CSV_FILE")
                            if st.button(label="", icon=":material/delete:", key="delete"+f"{file}{i}",
                                         use_container_width=True):
                                delete_file_data = {
                                        "file_name": file,
                                        "user_id": st.session_state["user_id"],
                                        "admin_department": st.session_state["admin_department"]
                                    }
                                response = requests.delete(delete_file_endpoint, json=delete_file_data)
                                st.session_state["csv_file"] = response.json()
                                st.success(f"{file} deleted successfully!")
                                st.rerun()
                        i += 1
                # Tạo conversation:
                st.header("Conversations", divider='orange')
                # Thêm tùy chọn để tạo cuộc hội thoại mới
                st.session_state["create_new_conversation"] = True
                if "create_new_conversation" in st.session_state and st.session_state["create_new_conversation"]:
                    conversation_name = "New conversation"
                    if st.button("Create new conversation", icon=":material/add_box:", use_container_width=True):
                        # Tạo một phiên hội thoại mới với loại conversation đã chọn
                        sql_conn.create_conversation_csvfile(conversation_name, st.session_state["user_id"])
                        # # Lấy danh sách các phiên hội thoại
                        st.session_state["conversations_user_csv"] = sql_conn.get_conversation_session_user_csvfile(st.session_state["user_id"])
                        st.session_state["create_new_conversation"] = False
                        st.rerun()
                
                st.write("---")
                # Thêm menu chọn Conversation vào sidebar
                if "conversations_user_csv" in st.session_state:
                    for conv in st.session_state["conversations_user_csv"]:
                        conversation_col, delete_col = st.columns([5, 1])
                        with conversation_col:
                            # Duyệt qua toàn bộ danh sách hội thoại với User Data và hiển thị dưới dạng nút
                            if st.button(f"{conv[1]}", icon=":material/chat:", key=f"user_{conv[0]}", use_container_width=True):
                                st.session_state["selected_conversation_id"] = conv[0]
                        with delete_col:
                            if st.button(label="", icon=":material/delete:", key="delete"+f'{conv[0]}', use_container_width=True):
                                sql_conn.delete_conversation(conv[0])
                                st.session_state["conversations_user_csv"] = sql_conn.get_conversation_session_user_csvfile(st.session_state["user_id"])
                                st.rerun()

                else:
                    st.warning("No user conversation sessions available.")
            
            col_chat, empty_col = st.columns([8, 1.4], vertical_alignment="top")
            st.session_state.model = 'gpt-4o-mini'
            with bottom():
                empty_col_1, input_col, empty_col = st.columns([1.25, 8, 1.25], vertical_alignment="top")
                with input_col:
                    chat_input_container = st.container()
                    with chat_input_container:
                        question = st.chat_input("What do you want to know?")
                    css_chat_input_container = float_css_helper(bottom="27px", z_index="100")
                    chat_input_container.float(css_chat_input_container)

            with col_chat:
                if "selected_conversation_id" in st.session_state and st.session_state["selected_conversation_id"] not in [i[0] for i in st.session_state["conversations_user_csv"]]:
                    del st.session_state["selected_conversation_id"]
                    del st.session_state["messages"]

                # Hiển thị lịch sử hội thoại của phiên đã chọn
                if "messages" not in st.session_state:
                    st.session_state.messages = []

                if "selected_conversation_id" in st.session_state:
                    chat_history = sql_conn.get_chat_history(st.session_state["selected_conversation_id"])
                    st.session_state.messages = []
                    # Cập nhật tin nhắn vào session_state.messages nếu có lịch sử
                    if chat_history:
                        st.session_state.messages = [
                            {"role": "user" if sender == "human" else "assistant", "output": message}
                            for sender, message in chat_history
                        ]

                # Hiển thị các tin nhắn trong phiên hội thoại đã chọn
                if "messages" in st.session_state:
                    for message in st.session_state.messages:
                        with st.chat_message(message["role"]):
                            st.markdown(message["output"])
                # try:
                if "selected_conversation_id" in st.session_state:
                        # Gửi tin nhắn mới trong giao diện chat
                    if question:
                        st.chat_message("user").markdown(question)
                        st.session_state.messages.append({"role": "user", "output": question})

                        with st.chat_message("assistant"):
                            try:
                                assistant_message = st.empty()
                                output = handler_input_csv(question, st.session_state["user_id"], CSV_QA_URL,
                                                           st.session_state.model)
                                assistant_message.markdown(output)
                                st.session_state.messages.append({"role": "assistant", "output": output})

                                sender = ['human', 'ai']
                                sql_conn.insert_chat(st.session_state["selected_conversation_id"], sender[0], question)
                                sql_conn.insert_chat(st.session_state["selected_conversation_id"], sender[1], output)

                            except:
                                output = "Please upload csv file first!"
                                st.warning("Please upload csv file first!")

                        # Đổi tên conversation nêu tên vẫn còn là new conversation
                        conversation_name = sql_conn.get_conversation_name_from_conversationid(
                            st.session_state["selected_conversation_id"])
                        if conversation_name == "New conversation":
                            rename_conversation_endpoint = os.getenv("RENAME_CONVERSATION")
                            data_for_rename = {
                                "history": f"(human:{question[:200]}); (ai: {output[:500]})",
                                "admin_department": st.session_state["admin_department"]
                            }
                            new_name = requests.post(rename_conversation_endpoint, json=data_for_rename)
                            sql_conn.change_conversation_name(st.session_state["selected_conversation_id"],
                                                              new_name.json().strip('"'))
                            st.rerun()
                else:
                    st.warning("Please select a conversation first!")

        pg = st.navigation({"System": [st.Page(Chat_Session)], "User": [st.Page(Chat_With_Files),
                            st.Page(Chat_With_CSVFile, title="Chat With CSVFile (Beta)")]})
        pg.run()
    
    elif st.session_state["Admin_login"] == True and st.session_state["User_login"] == False:
        st.title("Hello admin!")
        with st.sidebar:
            st.info(f"Nice to meet you: {st.session_state['admin_department']}", icon=":material/sentiment_satisfied:")

        def API_Key():
            st.subheader("API Keys")
            lst = [["./logo/gpt-4.webp", "openaikey"], ["./logo/gemini.png", "geminikey"]]
            test_key_endpoint = os.getenv("TEST_KEY")
            col1, col2 = st.columns([6, 3])
            with col1:
                for logo, name in lst:
                    col1, col2, col3 = st.columns([0.7, 10, 2.5])
                    with col1:
                        st.image(logo)
                    with col2:
                        if name == "openaikey":
                            st.session_state["openaikey"] = st.text_input(label="OpenAI API Key:", type="password",
                                                                          placeholder="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx")
                        else:
                            st.session_state["geminikey"] = st.text_input(label="Google Gemini API Key:", type="password",
                                                                          placeholder="AIxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
                    with col3:
                        if st.button(label="", icon=":material/send:", key="key"+name):
                            st.session_state["save_apikey"] = True
                        #if "save_apikey" in st.session_state and st.session_state["save_apikey"]:
                            if len(st.session_state[f"{name}"]) > 0:
                                data = {
                                    "apikey": st.session_state[f"{name}"],
                                    "type": name
                                }
                                response = requests.post(test_key_endpoint, json=data)
                                if response.json() == 1:
                                    try:
                                        sql_conn.add_api_key(st.session_state["admin_department"], name,
                                                             st.session_state[f"{name}"])
                                        st.session_state["get_apikey"] = True
                                        if st.session_state["get_apikey"]:
                                            apikey = get_apikey_for_admin(st.session_state["admin_department"])
                                        st.session_state["get_apikey"] = False
                                        st.success("Saved API key!")
                                        time.sleep(1)

                                    except:
                                        sql_conn.change_api_key(st.session_state["admin_department"], name,
                                                                st.session_state[f"{name}"])
                                        st.session_state["get_apikey"] = True
                                        if st.session_state["get_apikey"]:
                                            apikey = get_apikey_for_admin(st.session_state["admin_department"])
                                        st.session_state["get_apikey"] = False
                                        st.success("Changed API key!")
                                        time.sleep(1)

                                    st.session_state["save_apikey"] = False
                                else:
                                    st.warning("Incorrect API key provided, please make sure your API key is correct!")
                            else:
                                st.session_state["save_apikey"] = False
                                st.warning("API must not be empty!")
                            del st.session_state[f"{name}"]
            
            st.markdown("OpenAI Embedding APIKEY (Used for embedding documents and reformulating question)")
            col1, col2 = st.columns([6, 3])
            with col1:
                col1, col2, col3 = st.columns([0.7, 10, 2.5])
                with col1:
                    st.image("./logo/gpt-4.webp")
                with col2:
                    st.session_state["openai_embedding_key"] = st.text_input(label="OpenAI API Embedding Key:", type="password",
                                                                             placeholder="sk-xxxxxxxxxxxxxxxxxxxxxxxxx")
                with col3:
                    if st.button(label="", icon=":material/send:", key="send_openai_embedding_key"):
                        if len(st.session_state["openai_embedding_key"]) > 0:
                            data = {
                                "apikey": st.session_state["openai_embedding_key"],
                                "type": "openai_embedding_key"
                            }
                            response = requests.post(test_key_endpoint, json=data)
                            if response.json() == 1:
                                try:
                                    sql_conn.add_embedding_key(st.session_state["admin_department"],
                                                               st.session_state["openai_embedding_key"])
                                    st.session_state["get_apikey"] = True
                                    if st.session_state["get_apikey"]:
                                        apikey = get_apikey_for_admin(st.session_state["admin_department"])
                                    st.session_state["get_apikey"] = False
                                    st.success("Saved API key!")
                                    time.sleep(1)

                                except:
                                    sql_conn.change_api_key(st.session_state["admin_department"], 'openai-embedding',
                                                            st.session_state["openai_embedding_key"])
                                    st.session_state["get_apikey"] = True
                                    if st.session_state["get_apikey"]:
                                        apikey = get_apikey_for_admin(st.session_state["admin_department"])
                                    st.session_state["get_apikey"] = False
                                    st.success("Changed API key!")
                                    time.sleep(1)
                            else:
                                st.warning("Incorrect API key provided, please make sure your API key is correct!")
                        else:
                            st.warning("API must not be empty!")
                        del st.session_state["openai_embedding_key"]

        def Project_Folder():
            st.subheader("Create your project folder here")
            if st.button(label="Add folder", icon=":material/add:"):
                st.session_state["add_folder"] = True
            if "add_folder" in st.session_state and st.session_state["add_folder"]:
                folder_name = st.text_input("Name of the folder:", placeholder="New folder")
                if len(folder_name) == 0:
                    folder_name = "New folder"
                image_url = st.text_input("Folder Picture", placeholder="https://...")
                description = st.text_area("Description", max_chars=200,
                                           placeholder="E.g., A life coach who can help you set and achieve personal and professional goals.")
                # Thêm prompt
                prompt = st.text_area("Project Context & Instructions:", max_chars=10000)

                # Upload file
                uploaded_file = st.file_uploader("Choose a file", type=["pdf", "docx"], key="admin_upload_file")

                create_folder_button = st.button(label="Create folder", icon=":material/create_new_folder:")
                # Kiểm tra nếu người dùng chọn file
                if uploaded_file:
                    if st.toggle(label="Semantic chunking", key="Semantic_chunking_upload_file"):
                        st.session_state["semantic_chunking"] = True
                        st.info("""Semantic chunking helps the RAG system more accurately understand the context of the file.
However, it could increase the token usage and take longer time.""", icon="ℹ️")
                    upload_file_endpoint = os.getenv("UPLOAD_DATA_ADMIN")
                    if create_folder_button:
                        # Gửi POST request với file trực tiếp từ Streamlit lên FastAPI
                        with st.spinner("Creating..."):
                            try:
                                folder_id = "fd" + datetime.now().strftime("%Y%m%d%H%m") + secrets.token_hex(3)
                                sql_conn.add_folder(folder_id, folder_name, st.session_state["admin_department"],
                                                    image_url, description, prompt=prompt)
                                # Định nghĩa multipart-form cho file và các thông tin khác
                                files = {"file": (uploaded_file.name, uploaded_file)} #, "application/pdf"
                                data = {"admin_department": st.session_state["admin_department"],
                                        "folder_id": folder_id,
                                        "semantic_chunking": st.session_state["semantic_chunking"]
                                        }

                                # Gửi request lên FastAPI
                                response = requests.post(upload_file_endpoint, files=files, data=data)

                                # Hiển thị phản hồi
                                if response.status_code == 200:
                                    st.success(response.json())
                                else:
                                    st.error(f"Failed to upload file. Error {response.status_code}: {response.text}. Please check your API key!")
                            except:
                                st.warning("Incorrect API key provided, please make sure your API key is correct!")
                        # Update lai retriever
                        st.session_state["update_retriever"] = True
                        if st.session_state["update_retriever"]:
                            retriever_status = get_retriever_admin(st.session_state["admin_department"], folder_id)
                        st.session_state["update_retriever"] = False
                        st.session_state["semantic_chunking"] = False
                        st.session_state["add_folder"] = False
                        st.rerun()
                else:
                    if create_folder_button:
                        folder_id = "fd" + datetime.now().strftime("%Y%m%d%H%m") + secrets.token_hex(3)
                        sql_conn.add_folder(folder_id, folder_name, st.session_state["admin_department"],
                                            image_url, description, prompt=prompt)
                        # Update lai retriever
                        st.session_state["update_retriever"] = True
                        if st.session_state["update_retriever"]:
                            retriever_status = get_retriever_admin(st.session_state["admin_department"], folder_id)
                        st.session_state["update_retriever"] = False
                        st.session_state["add_folder"] = False
                        st.rerun()
            st.write("---")
            st.subheader("All folder")
            st.session_state["all_folder"] = sql_conn.get_folders(st.session_state["admin_department"])
            if "all_folder" in st.session_state:
                for folder in st.session_state["all_folder"]:
                    files = sql_conn.get_folder_files(folder[0])
                    image_col, col1, col2, col3 = st.columns([0.4, 7, 1, 1])
                    with image_col:
                        if len(folder[2]) > 0:
                            st.image(folder[2], width=40)
                        else:
                            random_image = random.choice(st.session_state["image_files"])
                            random_image_path = os.path.join("./logo/images/", random_image)
                            st.image(random_image_path, width=40)
                    with col1:
                        with st.expander(f"__{folder[1]}__"):
                            st.markdown("__Description:__\n"+folder[3])
                            st.markdown("__Instruction:__\n"+folder[4])
                            for file_name, size in files:
                                st.markdown(f"📄 {file_name} ({size:.2f} MB)", unsafe_allow_html=True)
                            st.write("---")
                            if st.button(label="Add prompt template", icon=":material/add_notes:",
                                         key=f"add_template_{folder[0]}"):
                                st.session_state[f"add_template_folder"] = True
                            if "add_template_folder" in st.session_state and st.session_state[f"add_template_folder"]:
                                template_input_column, save_column = st.columns([5, 1])
                                with template_input_column:
                                    st.session_state[f"added_template_text_{folder[0]}"] = st.text_area(
                                                                label="Prompt template:",
                                                                key=f"add_prompt_template_{folder[0]}", max_chars=2000)
                                with save_column:
                                    if st.button("", icon=":material/add:", key=f"save_prompt_template_{folder[0]}"):
                                        if st.session_state[f"added_template_text_{folder[0]}"] != "":
                                            sql_conn.add_template_folder(folder[0], st.session_state[f"added_template_text_{folder[0]}"])
                                        else:
                                            st.warning("Empty prompt template won't be saved!")
                                        st.session_state[f"add_template_folder"] = False
                                        st.rerun()

                            templates_folder = sql_conn.get_templates_folder(folder[0])
                            for template in templates_folder:
                                template_col, delete_template_col = st.columns([6, 1])
                                with template_col:
                                    st.markdown(template[1])
                                with delete_template_col:
                                    if st.button(label="", icon=":material/delete:", key=f"delete_template_{folder[0]}_{template[0]}"):
                                        sql_conn.delete_template_folder(template[0], folder[0])
                                        st.rerun()
                    with col2:
                        @st.dialog("Edit your folder", width="large")
                        def edit(folder):
                            new_name = st.text_input("Name of the folder:", value=folder[1],
                                                     key="edit"+f"{folder[0]}faku")
                            image_url = st.text_input("Folder Picture", value=folder[2])
                            description = st.text_area("Description", max_chars=200,
                                                       value=folder[3])
                            new_prompt = st.text_area("Project Context & Instructions:", value=folder[4],
                                                      key="text_area"+f"{folder[0]}", max_chars=10000)
                            
                            # nếu user không nhập nội dung mới mà lỡ bấm save thì vẫn giữ nguyên nội dung cũ
                            if len(new_name) == 0:
                                new_name = folder[1]

                            if len(description) == 0:
                                description = folder[3]
                            if len(image_url) == 0:
                                image_url = folder[2]
                            if len(new_prompt) == 0:
                                new_prompt = folder[2]

                            # Xóa file nếu muốn
                            files = sql_conn.get_folder_files(folder[0])
                            i = 0
                            for file_name, size in files:
                                col1, col2 = st.columns([5, 1])
                                with col1:
                                    st.markdown(f"📄 {file_name} ({size:.2f} MB)", unsafe_allow_html=True)
                                with col2:
                                    delete_file_endpoint = os.getenv("DELETE_FILE_ADMIN")
                                    if st.button(label="", icon=":material/delete:", key=i + 1, use_container_width=True):
                                        data = {
                                            "file_name": file_name,
                                            "admin_department": st.session_state["admin_department"],
                                            "folder_id": folder[0]
                                            }
                                        response = requests.delete(delete_file_endpoint, json=data)
                                        st.success(f"{file_name} deleted successfully!")

                                        # Update lai retriever
                                        st.session_state["update_retriever"] = True
                                        if st.session_state["update_retriever"]:
                                            retriever_status = get_retriever_admin(st.session_state["admin_department"], folder[0])
                                        st.markdown(retriever_status)
                                        st.session_state["update_retriever"] = False

                                        st.rerun()
                                i += 1
                            # Thêm file nếu muốn
                            uploaded_file = st.file_uploader("Choose a file", type=["pdf", "docx"], key="upfile"+folder[0])
                            # Kiểm tra nếu người dùng chọn file
                            if uploaded_file:
                                if st.toggle(label="Semantic chunking", key="Semantic_chunking_upload_file"):
                                    st.session_state["semantic_chunking"] = True
                                    st.info("""Semantic chunking helps the RAG system more accurately understand the context of the file.
However, it could increase the token usage and take longer time.""", icon="ℹ️")
                                upload_file_endpoint = os.getenv("UPLOAD_DATA_ADMIN")

                                if st.button(label="Add document", icon=":material/upload:"):
                                    # Gửi POST request với file trực tiếp từ Streamlit lên FastAPI
                                    with st.spinner("Adding..."):
                                        # Định nghĩa multipart-form cho file và các thông tin khác
                                        files = {"file": (uploaded_file.name, uploaded_file)} #, "application/pdf"
                                        data = {"admin_department": st.session_state["admin_department"],
                                                "folder_id": folder[0],
                                                "semantic_chunking": st.session_state["semantic_chunking"]
                                                }

                                        # Gửi request lên FastAPI
                                        response = requests.post(upload_file_endpoint, files=files, data=data)

                                        # Hiển thị phản hồi
                                        if response.status_code == 200:
                                            st.success(response.json())
                                        else:
                                            st.error(f"Failed to upload file. Error {response.status_code}: {response.text}")

                                    # Update lai retriever
                                    st.session_state["update_retriever"] = True
                                    if st.session_state["update_retriever"]:
                                        retriever_status = get_retriever_admin(st.session_state["admin_department"], folder[0])
                                    st.session_state["update_retriever"] = False
                                    st.session_state["semantic_chunking"] = False
                                    time.sleep(2)
                                    st.rerun()
                            if st.button("Save", key="save folder"+folder[0]):
                                sql_conn.update_folder(folder[0], new_name, image_url, description, new_prompt)
                                st.rerun()

                        if st.button(label="", icon=":material/edit:", key="edit"+f"{folder[0]}",  use_container_width=True):
                            edit(folder)

                    with col3:
                        delete_file_endpoint = os.getenv("DELETE_FOLDER_ADMIN")
                        if st.button(label="", icon=":material/delete:", key="delete"+f"{folder[0]}", use_container_width=True):
                            data = {"folder_id": folder[0], "admin_department": st.session_state["admin_department"]}
                            response = requests.delete(delete_file_endpoint, json=data)
                            st.success(f"Folder {folder[1]} deleted successfully!")

                            # Update lai retriever
                            st.session_state["update_retriever"] = True
                            if st.session_state["update_retriever"]:
                                retriever_status = get_retriever_admin(st.session_state["admin_department"], folder[0])
                            st.markdown(retriever_status)
                            st.session_state["update_retriever"] = False

                            st.rerun()

        pg = st.navigation([st.Page(API_Key), st.Page(Project_Folder)])
        pg.run()
