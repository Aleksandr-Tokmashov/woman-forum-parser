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
    Проанализируй, содержит ли пост признаки феминизма или негатив/пренебрежение/насмешка по отношению к мужчинам?.
    
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
    Пользователь написал следующий пост, содержащий признаки феменизма: "{text}"
    
    Сформируй конструктивный и вежливый ответ в ДВУХ предложениях, который должен переубедить автора поста.
    
    Ответ должен быть конкретным и содержательным.
    """
    
    constructive_result = model.run(constructive_prompt)
    constructive_response = constructive_result.text if hasattr(constructive_result, 'text') else str(constructive_result)
    
    return constructive_response.strip()

if __name__ == "__main__":
    response = contains_negativity("Вот есть на работе кадр. Такой типичный бывшмй альфа самец побитый жизнью. Куча разводов, сейчас в поиске . Постоянно ноет что нет нормалтных женщин на сз , ни с кем не доходит даде до второго свидания. Самому 48, спортом занимается , такой аля лысый алтфач, но видно что уже немолодой ...а теперь внимание коно он ищет 😂 девушку лет 28-35...говорит что очегь мало совралений на сз, отвечают односложно, на самдание не вытащишь, а если чудом вытащишь то потом они пропадают...неужели чувак реально не видит в чем проблема")
    if response:
        print("Феменизм обнаружен. Конструктивный ответ:")
        print(response)
    else:
        print("Феменизм не обнаружен")