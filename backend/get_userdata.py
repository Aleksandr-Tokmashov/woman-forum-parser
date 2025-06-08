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
table_path = config_data["db_path"] + "/users"


def get_userdata(session, name):
    query = f"""
    SELECT *
    FROM `{table_path}`
    WHERE name = "{name}";
    """
    result_sets = session.transaction().execute(query, commit_tx=True)
    return result_sets[0].rows

# Обновленный основной код с примером использования
with ydb.Driver(driver_config) as driver:
    try:
        driver.wait(timeout=15)
        with ydb.SessionPool(driver) as pool:
            # Пример вызова функции поиска по заголовку
            search_title = "sato"
            results = pool.retry_operation_sync(get_userdata, None, search_title)
            
            if results:
                for row in results:
                    print(row)
            else:
                print(f"Записи не найдены")
                
    except Exception as e:
        print(f"Ошибка при выполнении запроса: {e}")
        print("Последние ошибки драйвера:")
        print(driver.discovery_debug_details())