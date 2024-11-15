CREATE TABLE admins(
    admin_department varchar(20) primary key check (admin_department in ('DG1', 'DN1')),
    admin_username varchar(50) not null unique,
    admin_password varchar(150) not null,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users(
    user_id varchar(20) primary key,
    username VARCHAR(50) NOT NULL unique,
    password varchar(150) not null,
    admin_department varchar(20) references admins(admin_department) not null,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE folders_user(
    folder_id varchar(20) primary key,
    folder_name varchar(100),
	user_id varchar(20) references users(user_id),
	prompt varchar(10000)
);

CREATE TABLE conversations_user(
    conversation_id VARCHAR(20) primary key,
	conversation_name varchar(30) not null,
    folder_id VARCHAR(20) REFERENCES folders_user(folder_id),
    type varchar(20) check (type in ('text_file','csv_file')) not null,
    start_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages_user(
    message_id int,
    conversation_id varchar(20) references conversations_user(conversation_id),
    sender VARCHAR(50) NOT NULL,
    message_text TEXT not null,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    Primary key(message_id,conversation_id)
);

CREATE TABLE files(
    file_id varchar(20) primary key,
    file_name varchar(50) not null,
    size real not null,
    folder_id  VARCHAR(20) REFERENCES folders_user(folder_id),
    type varchar(20) check (type in ('text_file','csv_file')) not null,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prompts(
    prompt_id varchar(20) primary key,
    title varchar(200) not null,
    prompt_text varchar(10000) not null,
    user_id VARCHAR(20) REFERENCES users(user_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE apikeys(
    admin_department varchar(20) references admins(admin_department), 
    type varchar(20) CHECK (type IN ('openaikey', 'geminikey','openai-embedding')),
    key varchar(150) default null,
    primary key(admin_department, type)
);

CREATE TABLE folders(
	folder_id varchar(20) primary key,
    folder_name varchar(100),
	admin_department varchar(20) references admins(admin_department),
	image_url varchar(400),
	description varchar(200),
	prompt varchar(10000)
);

CREATE TABLE templates_folder(
    template_id varchar(20) primary key,
    template_text varchar(2000) not null,
    folder_id VARCHAR(20) REFERENCES folders(folder_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE folder_files(
	file_id varchar(20) primary key,
	folder_id varchar(20) references folders(folder_id),
    file_name varchar(50) not null,
    size real not null
);

CREATE TABLE conversations_system(
    conversation_id VARCHAR(20) primary key,
	conversation_name varchar(30) not null,
    user_id VARCHAR(20) REFERENCES users(user_id),
	folder_id varchar(20) references folders(folder_id),
    start_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
	unique(user_id, folder_id, conversation_id)
);

CREATE TABLE messages_system(
    message_id int,
    conversation_id varchar(20) references conversations_system(conversation_id),
    sender VARCHAR(50) NOT NULL,
    message_text TEXT not null,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    Primary key(message_id,conversation_id)
);

insert into admins(admin_department, admin_username, admin_password) VALUES('DG1','AdminDG1','thisaccountisjustforadmindg1');
insert into admins(admin_department, admin_username, admin_password) VALUES('DN1','AdminDN1','thisaccountisjustforadmindn1');


-- Tạo function để tự động tính `message_id` cho mỗi `conversation_id` của user.
CREATE OR REPLACE FUNCTION calculate_message_id_user()
RETURNS TRIGGER AS $$
DECLARE
    max_id INT;
BEGIN
    -- Lấy `message_id` lớn nhất trong mỗi `conversation_id`
    SELECT COALESCE(MAX(message_id), 0) + 1 INTO max_id
    FROM messages_user
    WHERE conversation_id = NEW.conversation_id;

    -- Gán `message_id` mới cho bản ghi
    NEW.message_id := max_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Tạo trigger để tự động cập nhật `message_id` cho từng bản ghi mới
CREATE TRIGGER set_message_id_new_for_user
BEFORE INSERT ON messages_user
FOR EACH ROW
EXECUTE FUNCTION calculate_message_id_user();


-- Tạo function để tự động tính `message_id` cho mỗi `conversation_id` của system.
CREATE OR REPLACE FUNCTION calculate_message_id_system()
RETURNS TRIGGER AS $$
DECLARE
    max_id INT;
BEGIN
    -- Lấy `message_id` lớn nhất trong mỗi `conversation_id`
    SELECT COALESCE(MAX(message_id), 0) + 1 INTO max_id
    FROM messages_system
    WHERE conversation_id = NEW.conversation_id;

    -- Gán `message_id` mới cho bản ghi
    NEW.message_id := max_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Tạo trigger để tự động cập nhật `message_id` cho từng bản ghi mới
CREATE TRIGGER set_message_id_new_for_system
BEFORE INSERT ON messages_system
FOR EACH ROW
EXECUTE FUNCTION calculate_message_id_system();
