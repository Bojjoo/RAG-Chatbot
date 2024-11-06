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


st.set_page_config(layout="wide")


float_init()

sql_conn = SQLDatabase()

load_dotenv()
USER_URL = os.getenv("USER_URL")
SYSTEM_URL = os.getenv("SYSTEM_URL")
USER_RETRIEVER = os.getenv("USER_RETRIEVER")
CSV_QA_URL = os.getenv("CSV_QA_URL")
SYSTEM_RETRIEVER = os.getenv("SYSTEM_RETRIEVER")


def handler_input_user(question, conversation_id, user_id, url, model, prompt_template,
                       admin_department, folder_id, prompt_folder):
    question_data = {
        "question": question,
        "conversation_id": conversation_id,
        "prompt_template": prompt_template,
        "user_id": user_id,
        "model": model,
        "admin_department": admin_department,
        "folder_id": folder_id,
        "prompt_folder": prompt_folder
    }
    response = requests.post(url=url, json=question_data, stream=True)

    if response.status_code == 200:
        for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
            # if chunk:
            yield chunk
    else:
        yield f"Error: {response.status_code} - {response.reason}"


def handler_input_system(question, conversation_id, user_id, url, model,
                         admin_department, folder_id, prompt_template, prompt_folder):
    question_data = {
        "question": question,
        "conversation_id": conversation_id,
        "prompt_template": prompt_template,
        "user_id": user_id,
        "model": model,
        "admin_department": admin_department,
        "folder_id": folder_id,
        "prompt_folder": prompt_folder
    }
    response = requests.post(url=url, json=question_data, stream=True)

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
                    folders = sql_conn.get_folders_user(st.session_state["user_id"])
                    if st.session_state["update_retriever"]:
                        for i in folders:
                            user_retriever = get_retriever(st.session_state["user_id"],
                                                           st.session_state["admin_department"], i[0])
                    st.session_state["update_retriever"] = False

                    # Lấy danh sách các phiên hội thoại
                    # st.session_state["conversations_id_user_text"] = sql_conn.get_conversationid_user_textfile(st.session_state["user_id"])
                    # st.session_state["conversations_id_user_csv"] = sql_conn.get_conversationid_user_csvfile(st.session_state["user_id"])
                    # st.session_state["conversations_id_system"] = sql_conn.get_conversationid_system(st.session_state["user_id"])

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

                # Lấy ra tất cả system conversation id
                st.session_state["conversations_system"] = []
                for folder in st.session_state["folders"]:
                    with st.expander(folder[1]):

                        # Create conversation
                        col_1, col_2 = st.columns([1, 2])
                        with col_1:
                            st.session_state["create_new_conversation"] = True
                            if st.session_state["create_new_conversation"]:
                                conversation_name = "New conversation"
                                if st.button(label="", icon=":material/add_box:",
                                             key="create_conversation_system" + f"{folder[0]}"):
                                    sql_conn.create_conversation_system(conversation_name, st.session_state["user_id"],
                                                                        folder[0])
                                    # # Lấy danh sách các phiên hội thoại
                                    st.session_state[
                                        f"conversations_system_{folder[0]}"] = sql_conn.get_conversation_session_system(
                                        st.session_state["user_id"], folder[0])

                                    st.session_state["create_new_conversation"] = False
                                    st.rerun()

                        # All conversations
                        st.session_state[f"conversations_system_{folder[0]}"] = sql_conn.get_conversation_session_system(
                                                                                st.session_state["user_id"], folder[0])
                        # Correct way to populate the conversation IDs
                        st.session_state["conversations_system"].extend([i[0] for i in st.session_state[f"conversations_system_{folder[0]}"]])

                        # Hiển thị conversation của folder đó
                        if f"conversations_system_{folder[0]}" in st.session_state:
                            for conv in st.session_state[f"conversations_system_{folder[0]}"]:
                                conversation_col, option_col = st.columns([5, 1])
                                with conversation_col:
                                    # Duyệt qua toàn bộ danh sách hội thoại với System và hiển thị dưới dạng nút
                                    if st.button(f"{conv[1]}", icon=":material/chat:", key=f"system_{conv[0]}", use_container_width=True):
                                        st.session_state["selected_conversation_id"] = (conv[0], folder[0], folder[1],
                                                                                        folder[2])
                                with option_col:
                                    if st.button(label="", icon=":material/delete:", key="delete" + f'{conv[0]}'):
                                        sql_conn.delete_conversation_system(conv[0])
                                        st.session_state[f"conversations_system_{folder[0]}"] = sql_conn.get_conversation_session_system(st.session_state["user_id"], folder[0])
                                        st.session_state["conversations_system"].remove(conv[0])
                                        st.rerun()
                        else:
                            st.warning("No system conversation sessions available.")
                            # Cần check lại cái này vì nó sẽ lưu prompt và title của folder cuối cùng
                        if "prompt_template" not in st.session_state:
                            st.session_state[f"prompt_template_{folder[0]}"] = folder[2]
                        if "title_prompt_template" not in st.session_state:
                            st.session_state[f"title_prompt_template_{folder[0]}"] = "Instruction of folder " + f"{folder[1]}"

            # Select model
            st.session_state.model = 'gpt-4o-mini'
            col1, col2, col3 = st.columns([1.4, 6, 2], vertical_alignment="top")

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
            css_col1 = float_css_helper(top="70px")
            col1.float(css_col1)

            # Chat session
            with col2:
                if "selected_conversation_id" in st.session_state and st.session_state["selected_conversation_id"][0] not in st.session_state["conversations_system"]:
                        del st.session_state["selected_conversation_id"]
                        del st.session_state["messages"]
                chat_input_container = st.container()
                with chat_input_container:
                    question = st.chat_input("What do you want to know?")
                css_chat_input_container = float_css_helper(bottom="35px")
                chat_input_container.float(css_chat_input_container)
                
                # Hiển thị lịch sử hội thoại của phiên đã chọn

                messages_container = st.container(border=False) #height=800,
                with messages_container:
                    if "messages" not in st.session_state:
                        st.session_state.messages = []

                    if "selected_conversation_id" in st.session_state:
                        chat_history = sql_conn.get_chat_history_system(st.session_state["selected_conversation_id"][0])
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

                                response_stream = handler_input_system(
                                               question, st.session_state["selected_conversation_id"][0],
                                               st.session_state["user_id"], SYSTEM_URL,
                                               st.session_state.model, st.session_state["admin_department"],
                                               st.session_state["selected_conversation_id"][1], prompt,
                                               st.session_state["selected_conversation_id"][3]
                                    )
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
                                sql_conn.insert_chat_system(st.session_state["selected_conversation_id"][0], sender[0], question)
                                sql_conn.insert_chat_system(st.session_state["selected_conversation_id"][0], sender[1], output)
                            # Đổi tên conversation nêu tên vẫn còn là new conversation
                            conversation_name = sql_conn.get_conversation_name_from_conversationid_system(
                                                                        st.session_state["selected_conversation_id"][0])
                            if conversation_name == "New conversation":
                                rename_conversation_endpoint = os.getenv("RENAME_CONVERSATION")
                                data_for_rename = {
                                    "history": f"(human:{question[:200]}); (ai: {output[:500]})",
                                    "admin_department": st.session_state["admin_department"]
                                }
                                new_name = requests.post(rename_conversation_endpoint, json=data_for_rename)
                                sql_conn.change_conversation_name_system(st.session_state["selected_conversation_id"][0],
                                                                         new_name.json().strip('"'))
                                st.session_state["conversations_system"] = sql_conn.get_conversation_session_system(
                                                                                st.session_state["user_id"],
                                                                                st.session_state["selected_conversation_id"][1])
                                st.rerun()
                    else:
                        st.warning("Please select a conversation first!")
                    css_chat_message_container = float_css_helper(bottom="80px", top="70px", overflow_y="auto")
                    messages_container.float(css_chat_message_container)

            with col3:
                st.markdown(f'Prompt Template is using: {st.session_state["title_prompt_template"]}')
                col_1, col_2 = st.columns([3, 1.5])
                with col_1:
                    try:
                        if st.session_state["title_prompt_template"] == "Normal QA":
                            with st.popover("Normal QA", use_container_width=True):
                                st.markdown(" ")
                        elif st.session_state["title_prompt_template"] == "Chat with document":
                            with st.popover("Chat with document", use_container_width=True):
                                st.markdown(f"{PROMPT_TEMPLATE}")
                    except:
                        st.warning("Choose a conversation first!")

                with col_2:
                    if st.button("Switch", key='switch_prompt_template_system'):
                        if st.session_state["title_prompt_template"] == "Normal QA":
                            st.session_state["prompt_template"] = PROMPT_TEMPLATE
                            st.session_state["title_prompt_template"] = "Chat with document"
                        elif st.session_state["title_prompt_template"] == "Chat with document":
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
                #st.session_state["conversations_user_text"] = sql_conn.get_conversation_session_user_textfile(st.session_state["user_id"])
                st.header("Create Folder Project", divider='orange')

                # Tạo folder của user
                @st.dialog("Create Folder", width="large")
                def create_folder():
                    folder_name = st.text_input("Name of the folder:", placeholder="New folder")
                    if len(folder_name) == 0:
                        folder_name = "New folder"
                    # Thêm prompt
                    prompt = st.text_area("""Project Context & Instructions:\n
This will be appended to the system instruction for all chats in this project. 
Note that this does not override, but "appended" on top of the global system instruction and agent-specific instructions.""",
                                          max_chars=5000)

                    # Upload file
                    uploaded_file = st.file_uploader("Choose a file", type=["pdf", "docx"], key="user_upload_file")

                    create_folder_button = st.button(key="Create folder user", icon=":material/create_new_folder:", label="")
                    # Kiểm tra nếu người dùng chọn file
                    if uploaded_file is not None:
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
                                            "folder_id": folder_id
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

                            time.sleep(2)
                            st.session_state["add_folder"] = False
                            st.rerun()
                    else:
                        if create_folder_button:
                            folder_id = "fd" + datetime.now().strftime("%Y%m%d%H%m") + secrets.token_hex(3)
                            sql_conn.add_folder_user(folder_id, folder_name, st.session_state["user_id"],
                                                     prompt=prompt)
                            st.session_state["add_folder"] = False
                            st.rerun()

                if st.button(label="Create Folder", icon=":material/create_new_folder:", key="create_folder_user",
                             use_container_width=True):
                    create_folder()

                st.write("---")
                st.session_state["folders_user"] = sql_conn.get_folders_user(st.session_state["user_id"])

                # Lấy ra tất cả conversation id
                st.session_state["conversations_user_text"] = []
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
                                new_name = st.text_input("Name of the folder:", placeholder=folder[1],
                                                         key="edit" + f"{folder[0]}faku")
                                new_prompt = st.text_area("Project Context & Instructions:",
                                                          key="text_area" + f"{folder[0]}", max_chars=10000,
                                                          placeholder=folder[2])

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
                                if uploaded_file is not None:
                                    upload_file_endpoint = os.getenv("UPLOAD_DATA")

                                    if st.button(label="Add document", icon=":material/upload:",
                                                 key="add_document"+folder[0]):
                                        # Gửi POST request với file trực tiếp từ Streamlit lên FastAPI
                                        with st.spinner("Adding..."):
                                            # Định nghĩa multipart-form cho file và các thông tin khác
                                            files = {"file": (uploaded_file.name, uploaded_file)}  # , "application/pdf"
                                            data = {"user_id": st.session_state["user_id"],
                                                    "folder_id": folder[0]
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
                                        time.sleep(1)
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
                            def delete_folder():
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
                                delete_folder()


                        # All conversations
                        st.session_state[f"conversations_user_{folder[0]}"] = sql_conn.get_conversation_session_user_textfile(folder[0])
                        # Correct way to populate the conversation IDs
                        st.session_state["conversations_user_text"].extend([i[0] for i in st.session_state[f"conversations_user_{folder[0]}"]])

                        # Hiển thị conversation của folder đó
                        if f"conversations_user_{folder[0]}" in st.session_state:
                            for conv in st.session_state[f"conversations_user_{folder[0]}"]:
                                conversation_col, option_col = st.columns([5, 1])
                                with conversation_col:
                                    # Duyệt qua toàn bộ danh sách hội thoại với System và hiển thị dưới dạng nút
                                    if st.button(f"{conv[1]}", icon=":material/chat:", key=f"user_{folder[0]}_{conv[0]}"
                                                 , use_container_width=True):
                                        st.session_state["selected_conversation_id"] = (conv[0], folder[0], folder[1],
                                                                                        folder[2])
                                with option_col:
                                    if st.button(label="", icon=":material/delete:", key="delete" + f'{conv[0]}'):
                                        sql_conn.delete_conversation(conv[0])
                                        st.session_state[f"conversations_user_{folder[0]}"] = sql_conn.get_conversation_session_user_textfile(folder[0])
                                        st.session_state["conversations_user_text"].remove(conv[0])
                                        st.rerun()
                        else:
                            st.warning("No system conversation sessions available.")
                            # Cần check lại cái này vì nó sẽ lưu prompt và title của folder cuối cùng
                        if "prompt_template" not in st.session_state:
                            st.session_state[f"prompt_template_{folder[0]}"] = folder[2]
                        if "title_prompt_template" not in st.session_state:
                            st.session_state[f"title_prompt_template_{folder[0]}"] = "Instruction of folder " + f"{folder[1]}"

            st.session_state.model = 'gpt-4o-mini'
            col1, col2, col3 = st.columns([1.15, 5, 2], vertical_alignment="top")

            with col1:
                option = st.selectbox(
                    label="Model:",
                    options=("gpt-4", "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo",
                             "gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro", "gemini-1.5-flash-002",
                             "gemini-1.5-pro-002", "gemini-1.5-flash-8b"),
                    index=None,
                    placeholder="gpt-4o-mini",
                )
                if option:
                    st.session_state.model = option
            css_col1 = float_css_helper(top="70px")
            col1.float(css_col1)

            with col2:
                if "selected_conversation_id" in st.session_state and st.session_state["selected_conversation_id"][0] not in st.session_state["conversations_user_text"]:
                        del st.session_state["selected_conversation_id"]
                        del st.session_state["messages"]
                chat_input_container = st.container()
                with chat_input_container:
                    question = st.chat_input("What do you want to know?")
                css = float_css_helper(bottom="35px")
                chat_input_container.float(css)

                # Phần hiển thị chat
                messages_container = st.container(border=False)
                with messages_container:
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
                        if question:
                            st.chat_message("user").markdown(question)
                            st.session_state.messages.append({"role": "user", "output": question})

                            with st.chat_message("assistant"):
                                assistant_message = st.empty()

                                prompt_template = st.session_state["prompt_template_user"]
                                response_stream = handler_input_user(
                                    question, st.session_state["selected_conversation_id"][0],
                                    st.session_state["user_id"], USER_URL, st.session_state.model, prompt_template,
                                    st.session_state["admin_department"], st.session_state["selected_conversation_id"][1],
                                    st.session_state["selected_conversation_id"][3])

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
                                sql_conn.insert_chat(st.session_state["selected_conversation_id"][0], sender[0], question)
                                sql_conn.insert_chat(st.session_state["selected_conversation_id"][0], sender[1], output)
                            
                            # Đổi tên conversation nêu tên vẫn còn là new conversation
                            conversation_name = sql_conn.get_conversation_name_from_conversationid(st.session_state["selected_conversation_id"][0])
                            if conversation_name == "New conversation":
                                rename_conversation_endpoint = os.getenv("RENAME_CONVERSATION")
                                data_for_rename = {
                                    "history": f"(human:{question[:200]}); (ai: {output[:500]})",
                                    "admin_department": st.session_state["admin_department"]
                                }
                                new_name = requests.post(rename_conversation_endpoint, json=data_for_rename)
                                sql_conn.change_conversation_name(st.session_state["selected_conversation_id"][0],
                                                                  new_name.json().strip('"'))
                                st.session_state["conversations_user_text"] = sql_conn.get_conversation_session_user_textfile(st.session_state["selected_conversation_id"][1])
                                st.rerun()
                    else:
                        st.warning("Please select a conversation first!")
                css_chat_message_container = float_css_helper(bottom="80px", top="70px", overflow_y="auto")
                messages_container.float(css_chat_message_container)

            with col3:
                st.markdown(f'Prompt Template is using: {st.session_state["title_prompt_template_user"]}')
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
                        st.rerun()
            col3.float()

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
                                sql_conn.change_conversation_name(
                                    st.session_state["selected_conversation_id"], new_name.json().strip('"'))

                                st.session_state[
                                    "conversations_user_text"] = sql_conn.get_conversation_session_user_csvfile(
                                    st.session_state["user_id"])
                                st.rerun()
                    else:
                        st.warning("Please select a conversation first!")
                css_chat_message_container = float_css_helper(bottom="80px", top="70px", overflow_y="auto")
                messages_container.float(css_chat_message_container)

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
                            st.session_state["openaikey"] = st.text_input(label="OpenAI API Key:",
                                                                          placeholder="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx")
                        else:
                            st.session_state["geminikey"] = st.text_input(label="Google Gemini API Key:",
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
            
            st.markdown("OpenAI Embedding APIKEY (Used for embedding documents and reformulating question)")
            col1, col2 = st.columns([6, 3])
            with col1:
                col1, col2, col3 = st.columns([0.7, 10, 2.5])
                with col1:
                    st.image("./logo/gpt-4.webp")
                with col2:
                    st.session_state["openai_embedding_key"] = st.text_input(label="OpenAI API Embedding Key:",
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

                create_folder_button = st.button(label="Create folder", icon=":material/create_new_folder:")
                # Kiểm tra nếu người dùng chọn file
                if uploaded_file is not None:
                    upload_file_endpoint = os.getenv("UPLOAD_DATA_ADMIN")
                    if create_folder_button:
                        # Gửi POST request với file trực tiếp từ Streamlit lên FastAPI
                        with st.spinner("Creating..."):
                            try:
                                folder_id = "fd" + datetime.now().strftime("%Y%m%d%H%m") + secrets.token_hex(3)
                                sql_conn.add_folder(folder_id, folder_name, st.session_state["admin_department"],
                                                    prompt=prompt)
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
                else:
                    if create_folder_button:
                        folder_id = "fd" + datetime.now().strftime("%Y%m%d%H%m") + secrets.token_hex(3)
                        sql_conn.add_folder(folder_id, folder_name, st.session_state["admin_department"],
                                            prompt=prompt)
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
                            new_name = st.text_input("Name of the folder:", placeholder="New folder",
                                                     key="edit"+f"{folder[0]}faku")
                            new_prompt = st.text_area("Project Context & Instructions:", key="text_area"+f"{folder[0]}",
                                                      max_chars=10000)
                            
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

                                if st.button(label="Add document", icon=":material/upload:"):
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
                                sql_conn.update_folder(folder[0], new_name, prompt=new_prompt)
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
