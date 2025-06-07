import re
from yandex_cloud_ml_sdk import YCloudML
from dotenv import load_dotenv, set_key
import os

def load_credentials():

    yc_token = os.popen("yc iam create-token").read().strip()
    set_key(".env", "AUTH", yc_token)
    load_dotenv()
    
    folder_id = os.getenv("FOLDER_ID")
    auth = os.getenv("AUTH")

    if not folder_id or not auth:
        raise ValueError("Не найдены FOLDER_ID или AUTH в .env файле!")

    return YCloudML(folder_id=folder_id, auth=auth)

sdk = load_credentials()
model = sdk.models.completions("yandexgpt").configure(temperature=0.5)

def contains_negativity(text: str) -> bool | str:
    # Проверка на негатив
    negativity_prompt = f"""
    Проанализируй, содержит ли пост негатив.
    
    Текст для анализа: "{text}"
    
    Ответь строго одним словом "да" или "нет" без пояснений.
    """
    
    negativity_result = model.run(negativity_prompt)
    response_text = negativity_result.text if hasattr(negativity_result, 'text') else str(negativity_result)
    
    match = re.search(r'\b(да|нет)\b', response_text, re.IGNORECASE)
    
    if not match or match.group(0).lower() != 'да':
        return False
    
    # Если негатив обнаружен - формируем конструктивный ответ
    constructive_prompt = f"""
    Пользователь написал следующий пост, содержащий негатив: "{text}"
    
    Сформируй конструктивный и вежливый ответ в ДВУХ предложениях, который:
    1. Проявит понимание к чувствам автора
    2. Предложит позитивный взгляд на ситуацию
    
    Ответ должен быть конкретным и содержательным.
    """
    
    constructive_result = model.run(constructive_prompt)
    constructive_response = constructive_result.text if hasattr(constructive_result, 'text') else str(constructive_result)
    
    return constructive_response.strip()

if __name__ == "__main__":
    response = contains_negativity("Ненавижу эту погоду! Все время дождь!")
    if response:
        print("Негатив обнаружен. Конструктивный ответ:")
        print(response)
    else:
        print("Негатив не обнаружен")