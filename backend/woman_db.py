import ydb
import os
from datetime import datetime
from dotenv import load_dotenv, set_key

def load_credentials():

    yc_token = os.popen("yc iam create-token").read().strip()
    set_key(".env", "AUTH", yc_token)
    load_dotenv()
    
    auth = os.getenv("AUTH")
    endpoint = os.getenv("ENDPOINT")
    db_path = os.getenv("DB_PATH")

    if not auth or not db_path:
        raise ValueError("Не найдены FOLDER_ID или AUTH в .env файле!")

    return {"auth": auth, "endpoint": endpoint, "db_path": db_path}

config_data = load_credentials()
driver_config = ydb.DriverConfig(
    config_data["endpoint"], config_data["db_path"],
    credentials=ydb.AccessTokenCredentials(config_data["auth"]),

)
# Полный путь к таблице (можно использовать относительный путь с префиксом ./)
table_path = config_data["db_path"] + "/threads"

# Данные для вставки
data = {
    'thread_url': 'https://www.woman.ru/psycho/socialization/thread-donor-dlya-rebenka-id6271888/',
    'title': 'Муж идиот',
    'content': 'как предложить парню с которым ты с дества знакома, стать донором для твоего ребенка',
    'is_negative': True,  
    'date': datetime.strptime('2025-06-06T00:14:26+03:00', '%Y-%m-%dT%H:%M:%S%z'),
    'answer': "У вас неправильная позиция. Пересмотрите свои взгляды",
    'is_answer_sent': False
}

# Функция для вставки данных
def insert_data(session):
    query = f"""
    UPSERT INTO `{table_path}` (
        thread_url,
        title,
        content,
        is_negative,
        date,
        answer,
        is_answer_sent
    ) VALUES (
        "{data['thread_url']}",
        "{data['title']}",
        "{data['content']}",
        {data['is_negative']},
        CAST("{data['date'].isoformat()}" AS Datetime),
        "{data['answer']}",
        {data["is_answer_sent"]}
    );
    """
    session.transaction().execute(query, commit_tx=True)

# Основной код
with ydb.Driver(driver_config) as driver:
    try:
        driver.wait(timeout=15)
        with ydb.SessionPool(driver) as pool:
            # Выполняем операцию вставки данных
            pool.retry_operation_sync(insert_data)
            print(f"Данные успешно добавлены в таблицу '{table_path}'")
    except Exception as e:
        print(f"Ошибка при добавлении данных: {e}")
        print("Последние ошибки драйвера:")
        print(driver.discovery_debug_details())