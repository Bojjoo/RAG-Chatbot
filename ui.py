import os
import requests
import streamlit as st
import time
from api.database.database import SQLDatabase
from streamlit_float import *
from api.config import *
import time
from dotenv import load_dotenv, find_dotenv
from datetime import datetime
import secrets


st.set_page_config(layout="wide")


float_init()

sql_conn = SQLDatabase()

load_dotenv()
USER_URL = os.getenv("USER_URL")
SYSTEM_URL = os.getenv("SYSTEM_URL")
USER_RETRIEVER = os.getenv("USER_RETRIEVER")
CSV_QA_URL = os.getenv("CSV_QA_URL")
SYSTEM_RETRIEVER = os.getenv("SYSTEM_RETRIEVER")


def handler_input(question: str, conversation_id: str, user_id: str, url, model, prompt_template, admin_department):
    data = {
        "question": question,
        "conversation_id": conversation_id,
        "prompt_template": prompt_template,
        "user_id": user_id,
        "model": model,
        "admin_department": admin_department
    }
    response = requests.post(url=url, json=data, stream=True)

    if response.status_code == 200:
        for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
            # if chunk:
            yield chunk
    else:
        yield f"Error: {response.status_code} - {response.reason}"


def handler_input_system(question: str, conversation_id: str, user_id: str, url, model, admin_department, folder_id, prompt):
    data = {
        "question": question,
        "conversation_id": conversation_id,
        "user_id": user_id,
        "model": model,
        "admin_department": admin_department,
        "folder_id": folder_id,
        "prompt": prompt
    }
    response = requests.post(url=url, json=data, stream=True)

    if response.status_code == 200:
        for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
            # if chunk:
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

def get_retriever(user_id: str, admin_department: str):
    data = {
        "user_id": user_id,
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



# Màn hình đăng nhập
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    User_tab, Admin_tab = st.tabs(["User", "Admin"])
    st.session_state["User_login"] = False
    st.session_state["Admin_login"] = False

    with User_tab:
        st.title("Login to access the chat")
        tab_login, tab_register = st.tabs(["Login", "Register"])

        with tab_register:
            new_username = st.text_input("New Username")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            department = st.radio("What is your department?", ["DG1","DN1"])

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
                            st.success("Account registered successfully! You can now log in.")
                        else:
                            st.warning(f"The user name {new_username} is existed, please choose another user name!")
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")

        with tab_login:
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
                    if st.session_state["update_retriever"]:
                        user_retriever = get_retriever(st.session_state["user_id"], st.session_state["admin_department"])
                        if user_retriever == "None":
                            st.warning("Look like you have not uploaded any documents yet! Please upload your documents first!")
                    st.session_state["update_retriever"] = False

                    # Lấy danh sách các phiên hội thoại
                    st.session_state["conversations_id_user_text"] = sql_conn.get_conversationid_user_textfile(st.session_state["user_id"])
                    st.session_state["conversations_id_user_csv"] = sql_conn.get_conversationid_user_csvfile(st.session_state["user_id"])
                    st.session_state["conversations_id_system"] = sql_conn.get_conversationid_system(st.session_state["user_id"])

                    st.session_state["User_login"] = True

                    st.rerun()

                # Nếu mk sai
                else:
                    st.warning("Invalid username or password. Please try again.")
    
    with Admin_tab:
        admin_username = st.text_input("admin_username")
        password = st.text_input("Admin_Password", type="password")

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


# Nếu người dùng đã đăng nhập thành công, hiển thị giao diện chat
if st.session_state["authenticated"]:
    if st.session_state["User_login"] == True and st.session_state["Admin_login"] == False:
        # Chat with admin's files
        def Chat_Session():
            # Định nghĩa prompt template
            if "prompt_template" not in st.session_state:
                st.session_state["prompt_template"] = " "
            if "title_prompt_template" not in st.session_state:
                st.session_state["title_prompt_template"] = "Normal QA"
            with st.sidebar:
                st.info(f"Nice to meet you: {st.session_state['user_name']}", icon=":material/sentiment_satisfied:")
                st.session_state["folders"] = sql_conn.get_folders(st.session_state["admin_department"])
                st.session_state["selected_folder"] = st.selectbox(label="Select project folder",
                                                                   options=st.session_state["folders"],
                                                                   index=0,
                                                                   format_func=lambda x: x[1])

                if st.session_state["selected_folder"]:
                    st.session_state["conversations_system"] = sql_conn.get_conversation_session_system(st.session_state["user_id"], st.session_state["selected_folder"][0])
                    if "prompt_template" not in st.session_state:
                        st.session_state["prompt_template"] = st.session_state["selected_folder"][2]
                    if "title_prompt_template" not in st.session_state:
                        st.session_state["title_prompt_template"] = "Instruction of folder " + f"{st.session_state['selected_folder'][1]}"

                    st.header("Conversations", divider='orange')
                    # Create conversation
                    st.session_state["create_new_conversation"] = True
                    if "create_new_conversation" in st.session_state and st.session_state["create_new_conversation"]:
                        conversation_name = "New conversation"
                        if st.button("Create new conversation", icon=":material/add_box:", use_container_width=True):
                            sql_conn.create_conversation_system(conversation_name, st.session_state["user_id"], st.session_state["selected_folder"][0])
                            # # Lấy danh sách các phiên hội thoại
                            st.session_state["conversations_system"] = sql_conn.get_conversation_session_system(st.session_state["user_id"], st.session_state["selected_folder"][0])

                            st.session_state["create_new_conversation"] = False
                            st.rerun()
                st.write("---")
                # Hiển thị các conversations
                if "conversations_system" in st.session_state:
                    for conv in st.session_state["conversations_system"]:
                        conversation_col, option_col = st.columns([5, 1])
                        with conversation_col:
                            # Duyệt qua toàn bộ danh sách hội thoại với System và hiển thị dưới dạng nút
                            if st.button(f"{conv[1]}", icon=":material/chat:", key=f"system_{conv[0]}",
                                         use_container_width=True):
                                st.session_state["selected_conversation_id"] = conv[0]
                        with option_col:
                            if st.button(label="", icon=":material/delete:", key="delete" + f'{conv[0]}'):
                                sql_conn.delete_conversation_system(conv[0])
                                st.session_state["conversations_system"] = sql_conn.get_conversation_session_system(st.session_state["user_id"], st.session_state["selected_folder"][0])
                                st.rerun()

                else:
                    st.warning("No system conversation sessions available.")

            # Select model
            st.session_state.model = 'gpt-4o-mini'
            col1, col2, col3 = st.columns([1.15, 5, 2], vertical_alignment="top")

            with col1:
                option = st.selectbox(
                    label="Model:",
                    options=("gpt-4", "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"
                             , "gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro", "gemini-1.5-flash-002"
                             , "gemini-1.5-pro-002", "gemini-1.5-flash-8b"),
                    index=None,
                    placeholder="gpt-4o-mini",
                )
                if option:
                    st.session_state.model = option
            col1.float()

            # Chat session
            with col2:
                if "selected_conversation_id" in st.session_state and st.session_state["selected_conversation_id"] not in [i[0] for i in st.session_state["conversations_system"]]:
                        del st.session_state["selected_conversation_id"]
                        del st.session_state["messages"]
                chat_input_container = st.container()
                with chat_input_container:
                    question = st.chat_input("What do you want to know?")
                css_chat_input_container = float_css_helper(bottom="35px")
                chat_input_container.float(css_chat_input_container)
                
                # Hiển thị lịch sử hội thoại của phiên đã chọn
                messages_container = st.container(height=800, border=False)
                with messages_container:
                    if "messages" not in st.session_state:
                        st.session_state.messages = []

                    if "selected_conversation_id" in st.session_state:
                        chat_history = sql_conn.get_chat_history_system(st.session_state["selected_conversation_id"])
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
                                assistant_message = st.empty()

                                prompt = st.session_state["prompt_template"]

                                response_stream = handler_input_system(question, st.session_state["selected_conversation_id"],
                                                    st.session_state["user_id"], SYSTEM_URL,
                                                    st.session_state.model, st.session_state["admin_department"],
                                                    st.session_state["selected_folder"][0], prompt)
                                # Stream and display the assistant's response
                                output = ""
                                for token in response_stream:
                                    output += token
                                    assistant_message.markdown(output)
                                    time.sleep(0.01)
                                st.session_state.messages.append({"role": "assistant", "output": output})

                            if output.startswith('["Error"]'):
                                st.warning("Please provide your api key first!")
                            else:
                                sender = ['human', 'ai']
                                sql_conn.insert_chat_system(st.session_state["selected_conversation_id"], sender[0], question)
                                sql_conn.insert_chat_system(st.session_state["selected_conversation_id"], sender[1], output)
                            # Đổi tên conversation nêu tên vẫn còn là new conversation
                            conversation_name = sql_conn.get_conversation_name_from_conversationid_system(st.session_state["selected_conversation_id"])
                            if conversation_name == "New conversation":
                                if len(question) <= 20:
                                    sql_conn.change_conversation_name_system(st.session_state["selected_conversation_id"], question)
                                else:
                                    sql_conn.change_conversation_name_system(st.session_state["selected_conversation_id"], question[:18]+"...")
                                st.session_state["conversations_system"] = sql_conn.get_conversation_session_system(st.session_state["user_id"], st.session_state["selected_folder"][0])
                                st.rerun()
                    else:
                        st.warning("Please select a conversation first!")

            with col3:
                st.markdown(f'Prompt Template is using: {st.session_state["title_prompt_template"]}')
                col_1, col_2 = st.columns([3, 1.5])
                with col_1:
                    if st.session_state["title_prompt_template"] == "Normal QA":
                        with st.popover("Chat with document", use_container_width=True):
                            st.markdown(f"{PROMPT_TEMPLATE}")
                    elif st.session_state["title_prompt_template"] == "Chat with document":
                        with st.popover("Instruction of folder " + f"{st.session_state['selected_folder'][1]}", use_container_width=True):
                            st.markdown(st.session_state['selected_folder'][2])
                    elif st.session_state["title_prompt_template"] == "Instruction of folder":
                        with st.popover("Normal QA", use_container_width=True):
                            st.markdown(" ")

                with col_2:
                    if st.button("Switch", key='switch_prompt_template'):
                        if st.session_state["title_prompt_template"] == "Normal QA":
                            st.session_state["prompt_template"] = PROMPT_TEMPLATE
                            st.session_state["title_prompt_template"] = "Chat with document"

                        elif st.session_state["title_prompt_template"] == "Chat with document":
                            st.session_state["prompt_template"] = st.session_state['selected_folder'][2]
                            st.session_state["title_prompt_template"] = "Instruction of folder"

                        elif st.session_state["title_prompt_template"] == "Instruction of folder":
                            st.session_state["prompt_template"] = " "
                            st.session_state["title_prompt_template"] = "Normal QA"

                        st.rerun()
            col3.float()

        # Chat with user's files
        def Chat_With_Files():
            # Định nghĩa prompt template
            if "prompt_template_user" not in st.session_state:
                st.session_state["prompt_template_user"] = " "
            if "title_prompt_template_user" not in st.session_state:
                st.session_state["title_prompt_template_user"] = "Normal QA"

            with st.sidebar:
                st.info(f"Nice to meet you: {st.session_state['user_name']}", icon=":material/sentiment_satisfied:")
                st.session_state["conversations_user_text"] = sql_conn.get_conversation_session_user_textfile(st.session_state["user_id"])
                st.header("UpLoad Your Documents", divider='orange')
                uploaded_file = st.file_uploader("Choose a file", type=["pdf", "docx"])

                # Kiểm tra nếu người dùng chọn file
                if uploaded_file is not None:
                    # Xác định URL của endpoint FastAPI và user_id
                    upload_file_endpoint = os.getenv("UPLOAD_DATA")

                    if st.button(label="Upload File", icon=":material/upload_file:"):
                        # Gửi POST request với file trực tiếp từ Streamlit lên FastAPI
                        with st.spinner("Uploading..."):
                            try:
                                # Định nghĩa multipart-form cho file và các thông tin khác
                                files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
                                data = {"user_id": st.session_state["user_id"]}

                                # Gửi request lên FastAPI
                                response = requests.post(upload_file_endpoint, files=files, data=data)

                                # Hiển thị phản hồi
                                if response.status_code == 200:
                                    st.success(response.json())
                                else:
                                    st.error(f"Failed to upload file. Error {response.status_code}: {response.text}")
                            except:
                                st.warning("Incorrect API key provided, please make sure your API key is correct!")
                        # Update lai retriever
                        st.session_state["update_retriever"] = True
                        if st.session_state["update_retriever"]:
                            retriever_status = get_retriever(st.session_state["user_id"], st.session_state["admin_department"])
                        st.markdown(retriever_status)
                        st.session_state["update_retriever"] = False

                # Hiển thị danh sách các file đã upload
                st.markdown("Uploaded Documents:")
                files = sql_conn.get_files_textfile(st.session_state["user_id"])

                if files:
                    i = 0
                    for file_name, size in files:
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            st.markdown(f"📄 {file_name} ({size:.2f} MB)", unsafe_allow_html=True)
                        with col2:
                            delete_file_endpoint = os.getenv("DELETE_FILE")
                            if st.button(label="", icon=":material/delete:", key=i+1, use_container_width=True):
                                data = {"file_name": file_name, "user_id": st.session_state["user_id"]}
                                response = requests.delete(delete_file_endpoint, json=data)
                                st.success(f"{file_name} deleted successfully!")

                                # Update lai retriever
                                st.session_state["update_retriever"] = True
                                if st.session_state["update_retriever"]:
                                    retriever_status = get_retriever(st.session_state["user_id"], st.session_state["admin_department"])
                                st.markdown(retriever_status)
                                st.session_state["update_retriever"] = False

                                st.rerun()
                        i = i + 1
                else:
                    st.write("No files uploaded yet.")

                st.header("Conversations", divider='orange')
                # Thêm tùy chọn để tạo cuộc hội thoại mới
                st.session_state["create_new_conversation"] = True
                if "create_new_conversation" in st.session_state and st.session_state["create_new_conversation"]:
                    conversation_name = "New conversation"
                    type="text_file"
                    if st.button("Create new conversation", icon=":material/add_box:", use_container_width=True):
                        # Tạo một phiên hội thoại mới với loại conversation đã chọn
                        sql_conn.create_conversation(conversation_name, st.session_state["user_id"], type)
                        # # Lấy danh sách các phiên hội thoại
                        st.session_state["conversations_user_text"] = sql_conn.get_conversation_session_user_textfile(st.session_state["user_id"])
                        st.session_state["create_new_conversation"] = False
                        st.rerun()
                
                st.write("---")
                # Thêm menu chọn Conversation vào sidebar
                if "conversations_user_text" in st.session_state:
                    for conv in st.session_state["conversations_user_text"]:
                        conversation_col, delete_col = st.columns([5, 1])
                        with conversation_col:
                            # Duyệt qua toàn bộ danh sách hội thoại với User Data và hiển thị dưới dạng nút
                            if st.button(f"{conv[1]}", icon=":material/chat:", key=f"user_{conv[0]}", use_container_width=True):
                                st.session_state["selected_conversation_id"] = conv[0]
                        with delete_col:
                            if st.button(label="", icon=":material/delete:", key="delete"+f'{conv[0]}', use_container_width=True):
                                sql_conn.delete_conversation(conv[0])
                                st.session_state["conversations_user_text"] = sql_conn.get_conversation_session_user_textfile(st.session_state["user_id"])
                                st.rerun()

                else:
                    st.warning("No user conversation sessions available.")

            st.session_state.model = 'gpt-4o-mini'
            col1, col2, col3 = st.columns([1.15, 5, 2], vertical_alignment="top")

            with col1:
                option = st.selectbox(
                    label="Model:",
                    options=("gpt-4", "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"
                            , "gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro", "gemini-1.5-flash-002"
                            , "gemini-1.5-pro-002", "gemini-1.5-flash-8b"),
                    index=None,
                    placeholder="gpt-4o-mini",
                )
                if option:
                    st.session_state.model = option
            col1.float()

            # question = st.chat_input("What do you want to know?")
            with col2:
                if "selected_conversation_id" in st.session_state and st.session_state["selected_conversation_id"] not in [i[0] for i in st.session_state["conversations_user_text"]]:
                        del st.session_state["selected_conversation_id"]
                        del st.session_state["messages"]
                chat_input_container = st.container()
                with chat_input_container:
                    question = st.chat_input("What do you want to know?")
                css = float_css_helper(bottom="35px")
                chat_input_container.float(css)

                messages_container = st.container(height=800, border=False)
                with messages_container:
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
                                assistant_message = st.empty()

                                prompt_template = st.session_state["prompt_template_user"]
                                response_stream = handler_input(
                                    question, st.session_state["selected_conversation_id"], st.session_state["user_id"],
                                    USER_URL, st.session_state.model, prompt_template, st.session_state["admin_department"])

                                # Stream and display the assistant's response
                                output = ""
                                for token in response_stream:
                                    output += token
                                    assistant_message.markdown(output)
                                    time.sleep(0.01)
                                st.session_state.messages.append({"role": "assistant", "output": output})

                            if output.startswith('["Error"]'):
                                st.warning("Please provide your api key first!")
                            else:
                                sender = ['human', 'ai']
                                sql_conn.insert_chat(st.session_state["selected_conversation_id"], sender[0], question)
                                sql_conn.insert_chat(st.session_state["selected_conversation_id"], sender[1], output)
                            
                            # Đổi tên conversation nêu tên vẫn còn là new conversation
                            conversation_name = sql_conn.get_conversation_name_from_conversationid(st.session_state["selected_conversation_id"])
                            if conversation_name == "New conversation":
                                if len(question) <= 20:
                                    sql_conn.change_conversation_name(st.session_state["selected_conversation_id"], question)
                                else:
                                    sql_conn.change_conversation_name(st.session_state["selected_conversation_id"], question[:18]+"...")
                                st.session_state["conversations_user_text"] = sql_conn.get_conversation_session_user_textfile(st.session_state["user_id"])
                                st.rerun()
                    else:
                        st.warning("Please select a conversation first!")

            with col3:
                st.markdown(f'Prompt Template is using: {st.session_state["title_prompt_template_user"]}')
                #st.markdown("System Prompt Template:")
                col_1, col_2 = st.columns([3, 1.5])
                with col_1:
                    if st.session_state["title_prompt_template_user"] == "Normal QA":
                        with st.popover("Chat with document", use_container_width=True):
                            st.markdown(f"{PROMPT_TEMPLATE}")
                    elif st.session_state["title_prompt_template_user"] == "Chat with document":
                        with st.popover("Normal QA", use_container_width=True):
                            st.markdown(f" ")
                    # with st.popover("Normal Question Answer", use_container_width=True):
                    #     st.markdown(" ")
                with col_2:
                    if st.button("Switch", key='switch_prompt_template'):
                        if st.session_state["title_prompt_template_user"] == "Normal QA":
                            st.session_state["prompt_template_user"] = PROMPT_TEMPLATE
                            st.session_state["title_prompt_template_user"] = "Chat with document"
                        elif st.session_state["title_prompt_template_user"] == "Chat with document":
                            st.session_state["prompt_template_user"] = " "
                            st.session_state["title_prompt_template_user"] = "Normal QA"
                    # if st.button("Use prompt", key='use_Normal_Question_Answer'):
                    #     st.session_state["prompt_template_user"] = " "
                    #     st.session_state["title_prompt_template_user"] = "Normal QA"
                        st.rerun()
                # st.markdown("Your Prompt Template:")
                # with st.container(height=430, border=True):
                #     prompts = sql_conn.get_prompt_template(st.session_state["user_id"])
                #     for prompt_id, title, prompt_text in prompts:
                #         col_a, col_b, col_c = st.columns([5, 2.5, 1])
                #         with col_a:
                #             with st.popover(f"{title}", use_container_width=True):
                #                 st.markdown(f"{prompt_text}")
                #         with col_b:
                #             if st.button("Use prompt", key='use'+prompt_id):
                #                 st.session_state["prompt_template_user"] = prompt_text
                #                 st.session_state["title_prompt_template_user"] = title
                #                 st.rerun()
                #         with col_c:
                #             if st.button(label="", icon=":material/delete:", key=prompt_id, use_container_width=True):
                #                 sql_conn.delete_prompt_template(prompt_id)
                #                 st.rerun()
            col3.float()

        # def Prompt_Session():
        #     st.markdown("Hello this is where you create your prompt template")
        #     if st.button(label="Add Prompt", icon=":material/add:"):
        #         st.session_state["add_prompt"] = True

        #     # Nếu nhấn nút "Create New Conversation", hiển thị hộp nhập để người dùng nhập tên hội thoại
        #     if "add_prompt" in st.session_state and st.session_state["add_prompt"]:
        #         title = st.text_input("Prompt Title:")
        #         prompt = st.text_area("Prompt:")
        #         if st.button(label="Add", icon=":material/add:"):
        #             if len(title) == 0:
        #                 st.warning("Title must not be empty!")
        #             elif len(prompt) == 0:
        #                 st.warning("Prompt message must not be empty!")
        #             else:
        #                 add_prompt_endpoint = os.getenv("ADD_PROMPT_TEMPLATE")
        #                 data = {"title": title, "prompt_text": prompt, "user_id": st.session_state["user_id"]}
        #                 response = requests.post(add_prompt_endpoint, json=data)
        #                 if response.status_code == 200:
        #                     st.success("Add prompt successfully!")
        #                     st.session_state["add_prompt"] = False
        #                 else:
        #                     st.error(f"Failed to add prompt. Error {response.status_code}: {response.text}")

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
                                data = {
                                    "user_id": st.session_state["user_id"],
                                    "admin_department": st.session_state["admin_department"]
                                }

                                # Gửi request lên FastAPI
                                response = requests.post(upload_file_endpoint, files=files, data=data)
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
                            if st.button(label="", icon=":material/delete:", key="delete"+f"{file}{i}", use_container_width=True):
                                data = {"file_name": file,
                                        "user_id": st.session_state["user_id"],
                                        "admin_department": st.session_state["admin_department"]
                                        }
                                response = requests.delete(delete_file_endpoint, json=data)
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
                    type="csv_file"
                    if st.button("Create new conversation", icon=":material/add_box:", use_container_width=True):
                        # Tạo một phiên hội thoại mới với loại conversation đã chọn
                        sql_conn.create_conversation(conversation_name, st.session_state["user_id"], type)
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
            
            col_1, col_chat, col3 = st.columns([1.15, 5, 2], vertical_alignment="top")
            st.session_state.model = 'gpt-4o-mini'
            with col_chat:
                if "selected_conversation_id" in st.session_state and st.session_state["selected_conversation_id"] not in [i[0] for i in st.session_state["conversations_user_csv"]]:
                    del st.session_state["selected_conversation_id"]
                    del st.session_state["messages"]
                chat_input_container = st.container()
                with chat_input_container:
                    question = st.chat_input("What do you want to know?")
                css = float_css_helper(bottom="35px")
                chat_input_container.float(css)

                messages_container = st.container(height=800, border=False)
                with messages_container:
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
                        # try:
                            # Gửi tin nhắn mới trong giao diện chat
                            if question:
                                st.chat_message("user").markdown(question)
                                st.session_state.messages.append({"role": "user", "output": question})

                                with st.chat_message("assistant"):
                                    assistant_message = st.empty()
                                    response = handler_input_csv(question, st.session_state["user_id"], CSV_QA_URL, st.session_state.model)
                                    assistant_message.markdown(response)
                                    st.session_state.messages.append({"role": "assistant", "output": response})

                                    sender = ['human', 'ai']
                                    sql_conn.insert_chat(st.session_state["selected_conversation_id"], sender[0], question)
                                    sql_conn.insert_chat(st.session_state["selected_conversation_id"], sender[1], response)

                                # Đổi tên conversation nêu tên vẫn còn là new conversation
                                conversation_name = sql_conn.get_conversation_name_from_conversationid(
                                    st.session_state["selected_conversation_id"])
                                if conversation_name == "New conversation":
                                    if len(question) <= 20:
                                        sql_conn.change_conversation_name(st.session_state["selected_conversation_id"],
                                                                          question)
                                    else:
                                        sql_conn.change_conversation_name(st.session_state["selected_conversation_id"],
                                                                          question[:18] + "...")
                                    st.session_state[
                                        "conversations_user_text"] = sql_conn.get_conversation_session_user_csvfile(
                                        st.session_state["user_id"])
                                    st.rerun()
                        # except:
                        #     st.warning("Please upload csv file first!")
                    else:
                        st.warning("Please select a conversation first!")

        pg = st.navigation({"System": [st.Page(Chat_Session)], "User": [st.Page(Chat_With_Files), st.Page(Chat_With_CSVFile, title="Chat With CSVFile (Beta)")]})
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
                            st.session_state["openaikey"] = st.text_input(label="OpenAI API Key:", placeholder="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
                        else:
                            st.session_state["geminikey"] = st.text_input(label="Google Gemini API Key:", placeholder="AIxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
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
                                        sql_conn.add_api_key(st.session_state["admin_department"], name, st.session_state[f"{name}"])
                                        st.session_state["get_apikey"] = True
                                        if st.session_state["get_apikey"]:
                                            apikey = get_apikey_for_admin(st.session_state["admin_department"])
                                        st.session_state["get_apikey"] = False
                                        st.success("Saved API key!")
                                        time.sleep(1)

                                    except:
                                        sql_conn.change_api_key(st.session_state["admin_department"], name, st.session_state[f"{name}"])
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
            
            st.markdown("OpenAI Embedding APIKEY (Used for embedding documents and reformulating question)")
            col1, col2 = st.columns([6, 3])
            with col1:
                col1, col2, col3 = st.columns([0.7, 10, 2.5])
                with col1:
                    st.image("./logo/gpt-4.webp")
                with col2:
                    st.session_state["openai_embedding_key"] = st.text_input(label="OpenAI API Embedding Key:", placeholder="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
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
                                    sql_conn.add_embedding_key(st.session_state["admin_department"], st.session_state["openai_embedding_key"])
                                    st.session_state["get_apikey"] = True
                                    if st.session_state["get_apikey"]:
                                        apikey = get_apikey_for_admin(st.session_state["admin_department"])
                                    st.session_state["get_apikey"] = False
                                    st.success("Saved API key!")
                                    time.sleep(1)

                                except:
                                    sql_conn.change_api_key(st.session_state["admin_department"], 'openai-embedding', st.session_state["openai_embedding_key"])
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

        def Project_Folder():
            st.subheader("Create your project folder here")
            if st.button(label="Add folder", icon=":material/add:"):
                st.session_state["add_folder"] = True
            if "add_folder" in st.session_state and st.session_state["add_folder"]:
                folder_name = st.text_input("Name of the folder:", placeholder="New folder")
                if len(folder_name) == 0:
                    folder_name = "New folder"
                # Thêm prompt
                prompt = st.text_area("Project Context & Instructions:", max_chars=10000)

                # Upload file
                uploaded_file = st.file_uploader("Choose a file", type=["pdf", "docx"], key="admin_upload_file")

                # Kiểm tra nếu người dùng chọn file
                if uploaded_file is not None:
                    upload_file_endpoint = os.getenv("UPLOAD_DATA_ADMIN")
                    if st.button(label="Create folder", icon=":material/create_new_folder:"):
                        # Gửi POST request với file trực tiếp từ Streamlit lên FastAPI
                        with st.spinner("Creating..."):
                            try:
                                folder_id = "fd" + datetime.now().strftime("%Y%m%d%H%m") + secrets.token_hex(3)
                                sql_conn.add_folder(folder_id, folder_name, st.session_state["admin_department"], prompt="__Instruction__: "+prompt)
                                # Định nghĩa multipart-form cho file và các thông tin khác
                                files = {"file": (uploaded_file.name, uploaded_file)} #, "application/pdf"
                                data = {"admin_department": st.session_state["admin_department"],
                                        "folder_id": folder_id
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
                        time.sleep(2)
                        st.session_state["add_folder"] = False
                        st.rerun()
            st.write("---")
            st.subheader("All folder")
            st.session_state["all_folder"] = sql_conn.get_folders(st.session_state["admin_department"])
            if "all_folder" in st.session_state:
                for folder in st.session_state["all_folder"]:
                    files = sql_conn.get_folder_files(folder[0])
                    col1, col2, col3 = st.columns([7, 1, 1])
                    with col1:
                        with st.expander(folder[1]):
                            st.markdown(folder[2])
                            for file_name, size in files:
                                st.markdown(f"📄 {file_name} ({size:.2f} MB)", unsafe_allow_html=True)

                    with col2:
                        @st.dialog("Edit your folder", width="large")
                        def edit(folder):
                            new_name = st.text_input("Name of the folder:", placeholder="New folder", key="edit"+f"{folder[0]}faku")
                            new_prompt = st.text_area("Project Context & Instructions:", key="text_area"+f"{folder[0]}", max_chars=10000)
                            
                            #nếu user không nhập nội dung mới mà lỡ bấm save thì vẫn giữ nguyên nội dung cũ
                            if len(new_name) == 0:
                                new_name = folder[1]
                            if len(new_prompt) == 0:
                                new_prompt = folder[2]

                            # Xóa file nếu muốn
                            files = sql_conn.get_folder_files(folder[0])
                            i = 0
                            for file_name, size in files:
                                col1, col2 = st.columns([5,1])
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
                            if uploaded_file is not None:
                                upload_file_endpoint = os.getenv("UPLOAD_DATA_ADMIN")

                                if st.button(label="Add document", icon=":material/create_new_folder:"):
                                    # Gửi POST request với file trực tiếp từ Streamlit lên FastAPI
                                    with st.spinner("Adding..."):
                                        # Định nghĩa multipart-form cho file và các thông tin khác
                                        files = {"file": (uploaded_file.name, uploaded_file)} #, "application/pdf"
                                        data = {"admin_department": st.session_state["admin_department"],
                                                "folder_id": folder[0]
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
                                    time.sleep(2)
                                    st.rerun()
                            if st.button("Save", key="save folder"+folder[0]):
                                sql_conn.update_folder(folder[0], new_name, prompt="__Instruction__: "+new_prompt)
                                st.rerun()

                        if st.button(label="", icon=":material/edit:", key="edit"+f"{folder[0]}",  use_container_width=True):
                            edit(folder)

                    with col3:
                        delete_file_endpoint = os.getenv("DELETE_FOLDER")
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
