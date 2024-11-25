import psycopg2
from api.config import *
from datetime import datetime
import secrets


class SQLDatabase:
    def __init__(self):
        conn = psycopg2.connect(database=DATABASE, host=HOST, port=PORT, user=USER, password=PASSWORD)
        self.cur = conn.cursor()
        conn.set_session(autocommit=True)

    # Thêm tin nhắn sau mỗi câu hỏi và câu trả lời
    def insert_chat(self, conversation_id, sender, message_text):
        query = "INSERT INTO messages_user (conversation_id, sender, message_text) VALUES (%s, %s, %s)"
        self.cur.execute(query, (conversation_id, sender, message_text))

    def insert_chat_system(self, conversation_id, sender, message_text):
        query = "INSERT INTO messages_system (conversation_id, sender, message_text) VALUES (%s, %s, %s)"
        self.cur.execute(query, (conversation_id, sender, message_text))

    # Lấy ra user_id từ username (unique)
    def get_userid_from_username(self, username):
        self.cur.execute(f"select user_id from users where username='{username}'")
        return self.cur.fetchall()[0][0]
    
    # Lấy ra các conversation session của userid
    def get_conversation_session_user_textfile(self, folder_id):
        self.cur.execute(f"select conversation_id, conversation_name from conversations_user where folder_id='{folder_id}' and type='text_file' order by start_time")
        a = self.cur.fetchall()
        return a

    def get_conversation_session_user_textfile_non_folder(self, user_id):
        self.cur.execute(f"""select conversation_id, conversation_name 
from conversations_user cu join folders_user fu
on cu.folder_id = fu.folder_id
where user_id='{user_id}' and type='text_file' and fu.folder_id like 'u_non_folder%' order by start_time""")
        a = self.cur.fetchall()
        return a
    
    def get_conversation_session_user_csvfile(self, user_id):
        self.cur.execute(f"""
select conversation_id, conversation_name 
from conversations_user cu join folders_user fu
on cu.folder_id = fu.folder_id
where fu.folder_id like 'u_csv_folder%' and user_id='{user_id}' and type='csv_file' order by start_time;""")
        a = self.cur.fetchall()
        return a
    
    def get_conversation_session_system(self, user_id, folder_id):
        self.cur.execute(f"select conversation_id, conversation_name from conversations_system where user_id='{user_id}' and folder_id='{folder_id}' order by start_time")
        a = self.cur.fetchall()
        return a

    def get_conversation_session_system_non_folder(self, user_id):
        self.cur.execute(f"select conversation_id, conversation_name from conversations_system where user_id='{user_id}' and folder_id is Null order by start_time")
        a = self.cur.fetchall()
        return a

    # Lấy conversation name dựa vào conversation id
    def get_conversation_name_from_conversationid(self, conversation_id):
        self.cur.execute(f"select conversation_name from conversations_user where conversation_id = '{conversation_id}'")
        a = self.cur.fetchall()[0][0]
        return a

    def get_conversation_name_from_conversationid_system(self, conversation_id):
        self.cur.execute(f"select conversation_name from conversations_system where conversation_id = '{conversation_id}'")
        a = self.cur.fetchall()[0][0]
        return a
    
    # tạo ra một conversation mới
    def create_conversation(self, conversation_name, folder_id, type):
        conversation_id = "cv" + datetime.now().strftime("%Y%m%d%H%m") + secrets.token_hex(3)
        self.cur.execute(
            f"""INSERT INTO conversations_user(conversation_id, conversation_name, folder_id, type)
            VALUES ('{conversation_id}', '{conversation_name}', '{folder_id}', '{type}')""")

    def create_conversation_user_textfile_non_folder(self, conversation_id, conversation_name, user_id):
        type = "text_file"
        self.cur.execute(f"""insert into conversations_user(conversation_id, conversation_name, folder_id, type)
VALUES ('{conversation_id}', '{conversation_name}', (select folder_id from folders_user where user_id='{user_id}' and folder_id like 'u_non_folder%'), '{type}')""")

    def create_conversation_csvfile(self, conversation_name, user_id):
        type = "csv_file"
        conversation_id = "cv" + datetime.now().strftime("%Y%m%d%H%m") + secrets.token_hex(3)
        self.cur.execute(f"""insert into conversations_user(conversation_id, conversation_name, folder_id, type)
VALUES ('{conversation_id}', '{conversation_name}', (select folder_id from folders_user where user_id='{user_id}' and folder_id like 'u_csv_folder%'), '{type}')""")
    
    def create_conversation_system(self, conversation_id, conversation_name, user_id, folder_id):

        self.cur.execute(
            f"""INSERT INTO conversations_system(conversation_id, conversation_name, user_id, folder_id)
            VALUES ('{conversation_id}', '{conversation_name}', '{user_id}', '{folder_id}')""")

    def create_conversation_system_non_folder(self, conversation_id, conversation_name, user_id):
        self.cur.execute(
            f"""INSERT INTO conversations_system(conversation_id, conversation_name, user_id)
            VALUES ('{conversation_id}', '{conversation_name}', '{user_id}')""")

    # Đổi tên conversation
    def change_conversation_name(self, conversation_id, new_name):
        query = "update conversations_user set conversation_name = %s where conversation_id = %s;"
        self.cur.execute(query, (new_name, conversation_id))

    def change_conversation_name_system(self, conversation_id, new_name):
        query = "update conversations_system set conversation_name = %s where conversation_id = %s;"
        self.cur.execute(query, (new_name, conversation_id))

    # Lấy ra history chat từ mỗi conversation_id: 8 lịch sử chat = 4 cuộc hội thoại
    def get_chat_history(self, conversation_id):
        self.cur.execute(f"select sender, message_text from messages_user where conversation_id='{conversation_id}' order by message_id")
        return self.cur.fetchall()

    def get_chat_history_system(self, conversation_id):
        self.cur.execute(f"select sender, message_text from messages_system where conversation_id='{conversation_id}' order by message_id")
        return self.cur.fetchall()
    
    # Lấy ra mk của user để đăng nhập
    def get_password_of_user(self, name):
        self.cur.execute(f"select password from users where username='{name}'")
        return self.cur.fetchall()[0][0]

    # Đăng kí tài khoản
    def register_account(self, user_name, password, admin_department):
        user_id = "ur" + datetime.now().strftime("%Y%m%d%H%m") + secrets.token_hex(3)
        try:
            self.cur.execute(f"insert into users(user_id, username, password, admin_department) VALUES('{user_id}','{user_name}','{password}','{admin_department}')")
            return 1
        except:
            return 0

    # Quản lý folder của users
    def add_folder_user(self, folder_id, folder_name, user_id, prompt):
        query = "insert into folders_user(folder_id, folder_name, user_id, prompt) values(%s, %s, %s, %s)"
        self.cur.execute(query, (folder_id, folder_name, user_id, prompt))

    def add_folder_user_textfile_non_folder(self, user_id):
        folder_id = "u_non_folder" + secrets.token_hex(4)
        folder_name = f"{user_id} non_folder"
        prompt = ""
        query = "insert into folders_user(folder_id, folder_name, user_id, prompt) values(%s, %s, %s, %s)"
        self.cur.execute(query, (folder_id, folder_name, user_id, prompt))

    def add_folder_user_csvfile(self, user_id):
        folder_id = "u_csv_folder" + secrets.token_hex(4)
        folder_name = f"{user_id} csv folder"
        prompt = " "
        query = "insert into folders_user(folder_id, folder_name, user_id, prompt) values(%s, %s, %s, %s)"
        self.cur.execute(query, (folder_id, folder_name, user_id, prompt))

    # Xóa folder
    def delete_folder_user(self, folder_id):
        self.cur.execute(f"delete from messages_user where conversation_id in (select conversation_id from conversations_user where folder_id ='{folder_id}')")
        self.cur.execute(f"delete from conversations_user where conversation_id in (select conversation_id from conversations_user where folder_id ='{folder_id}')")
        self.cur.execute(f"delete from files where folder_id = '{folder_id}'")
        self.cur.execute(f"delete from folders_user where folder_id = '{folder_id}'")

    # Lấy ra các folder của user:
    def get_folders_user(self, user_id):

        self.cur.execute(f"select folder_id, folder_name, prompt from folders_user where user_id='{user_id}' and folder_id like 'fd%'")
        return self.cur.fetchall()

    # Lấy ra các file trong folder đó:
    def get_folder_files_user(self, folder_id):
        self.cur.execute(f"select file_name, size from files where folder_id='{folder_id}'")
        return self.cur.fetchall()

    # Cập nhật prompt và tên folder
    def update_folder_user(self, folder_id, folder_name, prompt):
        query = "update folders_user set folder_name=%s, prompt=%s where folder_id=%s"
        self.cur.execute(query, (folder_name, prompt, folder_id))

    # Quản lý file trong từng folder của user
    # Lưu thông tin file của user vào table files
    def get_total_size_textfile(self, folder_id):
        self.cur.execute(f"select sum(size) from files where folder_id='{folder_id}' and type='text_file'")
        total_size = self.cur.fetchall()[0][0]
        return total_size

    def save_file_detail(self, file_name, file_size, folder_id, type):
        total_size = self.get_total_size_textfile(folder_id)
        if total_size is None or (total_size < 50 and file_size < 20):
            file_id = "fu" + datetime.now().strftime("%Y%m%d%H%m") + secrets.token_hex(3)
            self.cur.execute(f"insert into files(file_id,file_name,size,folder_id,type) values ('{file_id}','{file_name}','{file_size}','{folder_id}','{type}')")
            return 1
        elif total_size > 50 or file_size > 20:
            return 0

    # Lấy ra các file của user_id
    def get_files_textfile(self, folder_id):
        self.cur.execute(f"select file_name, size from files where folder_id='{folder_id}'and type='text_file'")
        files = self.cur.fetchall()
        return files
    
    def get_files_csvfile(self, user_id):#############################
        self.cur.execute(f"select file_name, size from files where user_id='{user_id}' and type='csv_file'")
        files = self.cur.fetchall()
        return files

    # Xóa thông tin file của user khỏi files
    def delete_file(self, file_name, folder_id):
        self.cur.execute(f"select file_id from files where file_name='{file_name}' and folder_id='{folder_id}'")
        a = self.cur.fetchall()
        lst = []
        for i in a:
            lst.append(i[0])
        for i in lst:
            self.cur.execute(f"delete from files where file_id ='{i}'")

    def delete_file_csv(self, file_name, user_id):#####################
        self.cur.execute(f"select file_id from files where file_name='{file_name}' and user_id='{user_id}' and type='csv_file'")
        a = self.cur.fetchall()
        lst = []
        for i in a:
            lst.append(i[0])
        for i in lst:
            self.cur.execute(f"delete from files where file_id ='{i}'")  

    # Xóa conversation
    def delete_conversation(self, conversation_id):
        self.cur.execute(f"delete from messages_user where conversation_id='{conversation_id}'")
        self.cur.execute(f"delete from conversations_user where conversation_id='{conversation_id}'")

    def delete_conversation_system(self, conversation_id):
        self.cur.execute(f"delete from messages_system where conversation_id='{conversation_id}'")
        self.cur.execute(f"delete from conversations_system where conversation_id='{conversation_id}'")

    # Prompt Template của User
    # thêm prompt template
    def add_prompt_template(self, title, prompt_text, user_id):
        prompt_id = "pt" + datetime.now().strftime("%Y%m%d%H%m") + secrets.token_hex(3)
        query = "insert into prompts(prompt_id, title, prompt_text, user_id) VALUES (%s, %s, %s, %s)"
        self.cur.execute(query, (prompt_id, title, prompt_text, user_id))

    # lấy ra prompt template của user 
    def get_prompt_template(self, user_id):
        self.cur.execute(f"select prompt_id, title, prompt_text from prompts where user_id = '{user_id}'")
        prompt_templates = self.cur.fetchall()
        return prompt_templates

    # xóa prompt template
    def delete_prompt_template(self, prompt_id):
        self.cur.execute(f"delete from prompts where prompt_id='{prompt_id}'")
        
    # Lấy ra admin_department của user_id
    def get_admin_department(self, user_id):
        self.cur.execute(f"select admin_department from users where user_id = '{user_id}'")
        admin_department = self.cur.fetchall()[0][0]
        return admin_department



##### For Admin
    # Quản lý API key của admin 
    def add_api_key(self, admin_department, type, key):
        self.cur.execute(f"insert into apikeys(admin_department, type, key) values ('{admin_department}', '{type}', '{key}')")

    def change_api_key(self, admin_department, type, key):
        self.cur.execute(f"""update apikeys set key ='{key}'
                            where admin_department='{admin_department}' and type='{type}'""")
    
    # Thêm apikey cho embedding model
    def add_embedding_key(self, admin_department, key):
        self.cur.execute(f"insert into apikeys(admin_department, type, key) values ('{admin_department}', 'openai-embedding', '{key}')")

    def get_api_key(self, admin_department):
        self.cur.execute(f"select type, key from apikeys where admin_department = '{admin_department}' and type in ('openaikey','geminikey')")
        apikey = self.cur.fetchall()
        return apikey
    
    # Lấy API key của openai cho embedding model
    def get_embedding_apikey(self, admin_department):
        self.cur.execute(f"select key from apikeys where admin_department ='{admin_department}' and type='openai-embedding'")
        try:
            apikey = self.cur.fetchall()[0][0]
        except:
            apikey = None
        return apikey
    
    # Quản lý file chung của admin
    # Lưu thông tin file của admin vào table files
    def save_file_detail_admin(self, file_name, file_size, folder_id):
        file_id = "fa" + datetime.now().strftime("%Y%m%d%H%m") + secrets.token_hex(3)
        self.cur.execute(f"insert into folder_files(file_id,folder_id,file_name,size) values ('{file_id}','{folder_id}','{file_name}','{file_size}')")

    # Xóa thông tin file của admin khỏi folder_files
    def delete_file_admin(self, file_name, folder_id):
        self.cur.execute(f"select file_id from folder_files where file_name='{file_name}' and folder_id='{folder_id}'")
        a = self.cur.fetchall()
        lst = []
        for i in a:
            lst.append(i[0])
        for i in lst:
            self.cur.execute(f"delete from folder_files where file_id ='{i}'")

    # Quản lý tài khoản admin
    # Lấy ra mk của admin để đăng nhập
    def get_password_of_admin(self, admin_username):
        self.cur.execute(f"select admin_password from admins where admin_username='{admin_username}'")
        return self.cur.fetchall()[0][0]

    # Lấy ra admin_department từ admin_username (unique)
    def get_admin_department_from_admin_username(self, admin_username):
        self.cur.execute(f"select admin_department from admins where admin_username='{admin_username}'")
        return self.cur.fetchall()[0][0]
    
    # Prompt Template của Admin
    # thêm prompt template
    def add_prompt_template_admin(self, title, prompt_text, admin_department):
        prompt_id = "pt" + datetime.now().strftime("%Y%m%d%H%m") + secrets.token_hex(3)
        query = "insert into system_prompts(prompt_id, title, prompt_text, admin_department) VALUES (%s, %s, %s, %s)"
        self.cur.execute(query, (prompt_id, title, prompt_text, admin_department))

    # lấy ra prompt template của admin
    def get_prompt_template_admin(self, admin_department):
        self.cur.execute(f"select prompt_id, title, prompt_text from system_prompts where admin_department = '{admin_department}'")
        prompt_templates = self.cur.fetchall()
        return prompt_templates

    # xóa prompt template
    def delete_prompt_template_admin(self, prompt_id):
        self.cur.execute(f"delete from system_prompts where prompt_id='{prompt_id}'")

    # Folder project của admin
    def add_folder(self, folder_id, folder_name, admin_department, image_url, description, prompt):
        query = "insert into folders(folder_id, folder_name, admin_department, image_url, description, prompt) values(%s, %s, %s, %s, %s, %s)"
        self.cur.execute(query, (folder_id, folder_name, admin_department, image_url, description, prompt))

    # Xóa folder
    def delete_folder(self, folder_id):
        self.cur.execute(f"delete from messages_system where conversation_id in (select conversation_id from conversations_system where folder_id ='{folder_id}')")
        self.cur.execute(f"delete from conversations_system where conversation_id in (select conversation_id from conversations_system where folder_id ='{folder_id}')")
        self.cur.execute(f"delete from folder_files where folder_id = '{folder_id}'")
        self.cur.execute(f"delete from templates_folder where folder_id = '{folder_id}'")
        self.cur.execute(f"delete from folders where folder_id = '{folder_id}'")
    
    # Lấy ra các folder của admin:
    def get_folders(self, admin_department):
        self.cur.execute(f"select folder_id, folder_name, image_url, description, prompt from folders where admin_department='{admin_department}'")
        return self.cur.fetchall()

    # Lấy ra các file trong folder đó:
    def get_folder_files(self, folder_id):
        self.cur.execute(f"select file_name, size from folder_files where folder_id='{folder_id}'")
        return self.cur.fetchall()
    
    # Cập nhật prompt và tên folder
    def update_folder(self, folder_id, folder_name, image_url, description, prompt):
        # query = "update folders set folder_name='{folder_name}', prompt='{prompt}' where folder_id='{folder_id}'"
        query = "update folders set folder_name=%s, image_url=%s, description=%s, prompt=%s where folder_id=%s"
        self.cur.execute(query, (folder_name, image_url, description, prompt, folder_id))

    # Phần template folder
    def add_template_folder(self, folder_id, template_text):
        template_id = "tp" + datetime.now().strftime("%Y%m%d%H%m") + secrets.token_hex(3)
        query = "insert into templates_folder(template_id, template_text, folder_id) values(%s, %s, %s)"
        self.cur.execute(query, (template_id, template_text, folder_id))

    def get_templates_folder(self, folder_id):
        self.cur.execute(f"select template_id, template_text from templates_folder where folder_id = '{folder_id}'")
        return self.cur.fetchall()

    def delete_template_folder(self, template_id, folder_id):
        self.cur.execute(f"delete from templates_folder where template_id = '{template_id}' and folder_id = '{folder_id}'")
