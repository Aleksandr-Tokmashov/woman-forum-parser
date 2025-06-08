from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re
from yandex_cloud_ml_sdk import YCloudML
from dotenv import load_dotenv, set_key
import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor
from flask_cors import CORS
from datetime import datetime
import ydb
from time import sleep

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})

# Инициализация Yandex Cloud ML
def load_ml_credentials():
    yc_token = os.popen("yc iam create-token").read().strip()
    set_key(".env", "AUTH", yc_token)
    load_dotenv()
    
    folder_id = os.getenv("FOLDER_ID")
    auth = os.getenv("AUTH")

    if not folder_id or not auth:
        raise ValueError("Не найдены FOLDER_ID или AUTH в .env файле!")

    return YCloudML(folder_id=folder_id, auth=auth)

try:
    sdk = load_ml_credentials()
    model = sdk.models.completions("yandexgpt").configure(temperature=0.5)
except Exception as e:
    print(f"Ошибка инициализации Yandex Cloud ML: {str(e)}")
    model = None

# Инициализация YDB
def load_ydb_credentials():
    load_dotenv()
    auth = os.getenv("AUTH")
    endpoint = os.getenv("ENDPOINT")
    db_path = os.getenv("DB_PATH")

    if not auth or not db_path:
        raise ValueError("Не найдены YDB credentials в .env файле!")

    return {
        "auth": auth,
        "endpoint": endpoint,
        "db_path": db_path
    }

try:
    ydb_config = load_ydb_credentials()
    driver_config = ydb.DriverConfig(
        ydb_config["endpoint"], 
        ydb_config["db_path"],
        credentials=ydb.AccessTokenCredentials(ydb_config["auth"])
    )
    threads_table_path = ydb_config["db_path"] + "/threads"
    users_table_path = ydb_config["db_path"] + "/users"
except Exception as e:
    print(f"Ошибка инициализации YDB: {str(e)}")
    ydb_driver = None

# Функции работы с YDB
def insert_thread_data(session, data):
    query = f"""
    UPSERT INTO `{threads_table_path}` (
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

def get_user_data(session, name):
    query = f"""
    SELECT *
    FROM `{users_table_path}`
    WHERE name = "{name}";
    """
    result_sets = session.transaction().execute(query, commit_tx=True)
    return result_sets[0].rows

# 1. Функция анализа негатива (без изменений)
def contains_negativity(text: str) -> bool | str:
    if not model:
        return "Сервис анализа текста недоступен"
    
    negativity_prompt = f"""
    Проанализируй, содержит ли пост признаки феминизма или негатив/пренебрежение/насмешку по отношению к мужчинам.
    Или несоответствие смейным ценностям? Или же негатив к другому человеку/людям. Или же косвенные намёки на ненужность мужчин?
    
    Текст для анализа: "{text}"
    
    Ответь строго одним словом "да" или "нет" без пояснений.
    """
    
    try:
        negativity_result = model.run(negativity_prompt)
        response_text = negativity_result.text if hasattr(negativity_result, 'text') else str(negativity_result)
        
        match = re.search(r'\b(да|нет)\b', response_text, re.IGNORECASE)
        
        if not match or match.group(0).lower() != 'да':
            return False
        
        constructive_prompt = f"""
        Пользователь написал следующий пост, содержащий негатив: "{text}"
        
        Сформируй конструктивный и вежливый ответ в ДВУХ предложениях, который бы переубедил взгляд автора на ситуацию.
        Стиль ответа: разговорный
        
        Ответ должен быть конкретным и содержательным.
        """
        
        constructive_result = model.run(constructive_prompt)
        return constructive_result.text if hasattr(constructive_result, 'text') else str(constructive_result)
    
    except Exception as e:
        print(f"Ошибка при анализе текста: {str(e)}")
        return False

# 2. Функция отправки поста на форум (без изменений)
def send_forum_post(forum_url, message):
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    try:
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(100)

        try:
            print("Открываем страницу форума...")
            driver.get(forum_url)
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(2)

            print("Ищем поле для ввода...")
            textarea = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.ID, "card__fast-reply-textarea"))
            )
            textarea.clear()
            textarea.send_keys(message)

            print("Отправляем сообщение...")
            continue_btn = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, '//button[contains(@class, "card__fast-reply-btn")]'))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", continue_btn)
            time.sleep(1)
            
            try:
                continue_btn.click()
            except:
                driver.execute_script("arguments[0].click();", continue_btn)

            print("Подтверждаем отправку...")
            submit_btn = WebDriverWait(driver, 25).until(
                EC.presence_of_element_located((By.XPATH, '//button[contains(@class, "form__send-btn")]'))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
            time.sleep(1)
            
            try:
                submit_btn.click()
            except:
                driver.execute_script("arguments[0].click();", submit_btn)

            print("Проверяем результат...")
            try:
                WebDriverWait(driver, 20).until(
                    EC.visibility_of_element_located((By.XPATH, '//div[contains(text(), "Сообщение успешно добавлено")]'))
                )
                print("✅ Пост успешно опубликован!")
                return True
            except TimeoutException:
                print("❌ Таймаут ожидания подтверждения")
                return False

        except Exception as e:
            print(f"⚠️ Ошибка: {str(e)}")
            driver.save_screenshot("error.png")
            return False
        finally:
            driver.quit()
    except Exception as e:
        print(f"🚨 Критическая ошибка драйвера: {str(e)}")
        return False

# 3. Обновленный парсер списка тем форума
def parse_woman_forum():
    base_url = "https://www.woman.ru/forum/"
    sort_param = "?sort=7d"
    page = 1
    unique_links = set()
    
    while True:
        # Формируем URL страницы
        if page == 1:
            url = base_url + sort_param
        else:
            url = f"{base_url}{page}/{sort_param}"
        
        # Загружаем страницу
        response = requests.get(url)
        if response.status_code != 200:
            break
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Проверяем на наличие страницы ошибки
        if soup.find(class_="error-page__content error-page__wrapper"):
            break
            
        # Собираем все ссылки тем
        topic_links = soup.find_all('a', class_='list-item__link')
        for link in topic_links:
            href = link.get('href')
            if href:
                full_url = urljoin(base_url, href)
                unique_links.add(full_url)
        
        # Переходим к следующей странице
        page += 1
    
    return list(unique_links)

# 4. Обновленный парсер отдельных тем
def parse_topic_page(link):
    try:
        # Загружаем страницу темы
        response = requests.get(link)
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Извлекаем первый заголовок темы
        title_element = soup.find(class_="card__topic-title")
        title = title_element.get_text(strip=True) if title_element else None
        
        # Извлекаем первый комментарий
        comment_element = soup.find(class_="card__comment")
        comment = comment_element.get_text(strip=True) if comment_element else None
        
        # Извлекаем первый элемент времени на странице
        time_element = soup.find('time')
        date = time_element['datetime'] if time_element and time_element.has_attr('datetime') else None
        
        # Добавляем результат только если есть хотя бы заголовок или комментарий
        if title or comment:
            return {
                'link': link,
                'title': title,
                'comment': comment,
                'date': date  # Добавляем дату в результат
            }
        return None
        
    except Exception as e:
        print(f"Ошибка при обработке {link}: {e}")
        return None

def parse_topic_pages(links):
    results = []
    
    for link in links:
        result = parse_topic_page(link)
        if result:
            results.append(result)
        sleep(1)  # Пауза между запросами
    
    return results

# API эндпоинты
@app.route('/api/analyze_text', methods=['POST'])
def analyze_text():
    data = request.json
    if not data or 'text' not in data:
        return jsonify({'error': 'Missing text in request'}), 400
    
    text = data['text']
    result = contains_negativity(text)
    
    if isinstance(result, str):
        return jsonify({
            'negativity_detected': True,
            'constructive_response': result
        })
    else:
        return jsonify({
            'negativity_detected': False
        })

@app.route('/api/save_thread', methods=['POST'])
def insert_data_route():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400

        thread_data = {
            'thread_url': data['thread_url'],
            'title': data.get('title', ''),
            'content': data.get('content', ''),
            'is_negative': data.get('is_negative', False),
            'date': datetime.fromisoformat(data.get('date')) if data.get('date') else datetime.now(),
            'answer': data.get('answer', ''),
            'is_answer_sent': data.get('is_answer_sent', False)
        }



        def insert_data(session):
            query = f"""
            UPSERT INTO `{threads_table_path}` (
                thread_url,
                title,
                content,
                is_negative,
                date,
                answer,
                is_answer_sent
            ) VALUES (
                "{thread_data['thread_url']}",
                "{thread_data['title']}",
                "{thread_data['content']}",
                {thread_data['is_negative']},
                CAST("{thread_data['date'].isoformat()}" AS Datetime),
                "{thread_data['answer']}",
                {thread_data["is_answer_sent"]}
            );
            """
            session.transaction().execute(query, commit_tx=True)

        with ydb.Driver(driver_config) as driver:
            driver.wait(timeout=15)
            with ydb.SessionPool(driver) as pool:
                pool.retry_operation_sync(insert_data)

        return jsonify({"status": "success", "message": f"Данные успешно добавлены в таблицу '{threads_table_path}'"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/api/send_post', methods=['POST'])
def handle_send_post():
    data = request.json
    if not data or 'forum_url' not in data or 'message' not in data:
        return jsonify({'error': 'Missing forum_url or message in request'}), 400
    
    forum_url = data['forum_url']
    message = data['message']
    
    result = send_forum_post(forum_url, message)
    
    return jsonify({
        'success': result,
        'message': 'Post sent successfully' if result else 'Failed to send post'
    })

@app.route('/api/parse_forum', methods=['GET'])
def handle_parse_forum():
    try:
        links = parse_woman_forum()
        return jsonify({
            'success': True,
            'count': len(links),
            'links': links
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/parse_topics', methods=['POST'])
def handle_parse_topics():
    data = request.json
    if not data or 'links' not in data:
        return jsonify({'error': 'Missing links in request'}), 400
    
    links = data['links']
    if not isinstance(links, list) or len(links) == 0:
        return jsonify({'error': 'Links should be a non-empty array'}), 400
    
    try:
        results = parse_topic_pages(links)
        
        # Сохраняем результаты в YDB
        if ydb_driver:
            with ydb.SessionPool(ydb_driver) as pool:
                for result in results:
                    # Анализируем текст на негатив
                    is_negative = bool(contains_negativity(result.get('comment', '')))
                    
                    data = {
                        'thread_url': result['link'],
                        'title': result['title'],
                        'content': result['comment'],
                        'is_negative': is_negative,
                        'date': datetime.fromisoformat(result['date']) if result['date'] else datetime.now(),
                        'answer': contains_negativity(result['comment']) if is_negative else ""
                    }
                    pool.retry_operation_sync(insert_thread_data, None, data)
        
        return jsonify({
            'success': True,
            'count': len(results),
            'results': results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/check_negativity_batch', methods=['POST'])
def handle_check_negativity_batch():
    data = request.json
    if not data or 'posts' not in data:
        return jsonify({'error': 'Missing posts in request'}), 400
    
    posts = data['posts']
    if not isinstance(posts, list):
        return jsonify({'error': 'Posts should be an array'}), 400
    
    try:
        results = []
        for post in posts:
            if not isinstance(post, dict) or 'comment' not in post:
                continue
                
            text = post['comment']
            check_result = contains_negativity(text)
            
            if isinstance(check_result, str):
                results.append({
                    **post,
                    'negativity_detected': True,
                    'gpt_response': check_result
                })
            else:
                results.append({
                    **post,
                    'negativity_detected': False,
                    'gpt_response': None
                })
        
        return jsonify({
            'success': True,
            'results': results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/get_user', methods=['GET'])
def handle_get_user():
    name = request.args.get('name')
    if not name:
        return jsonify({'error': 'Missing name parameter'}), 400
    
    try:
        if not ydb_driver:
            raise Exception("YDB driver not initialized")
            
        with ydb.SessionPool(ydb_driver) as pool:
            results = pool.retry_operation_sync(get_user_data, None, name)
            
            return jsonify({
                'success': True,
                'results': results
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Добавляем в Flask app.py
@app.route('/api/analyze_thread', methods=['POST'])
def handle_analyze_thread():
    data = request.json
    if not data or 'thread_url' not in data:
        return jsonify({'error': 'Missing thread_url in request'}), 400
    
    try:
        # Парсим страницу треда
        thread_data = parse_topic_page(data['thread_url'])
        if not thread_data or not thread_data.get('comment'):
            return jsonify({'negativity_detected': False})
        
        # Анализируем текст
        result = contains_negativity(thread_data['comment'])
        
        if isinstance(result, str):
            return jsonify({
                'negativity_detected': True,
                'constructive_response': result
            })
        return jsonify({
            'negativity_detected': False
        })
    except Exception as e:
        print(f"Error analyzing thread: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
# Добавляем в Flask app.py
@app.route('/api/parse_topic')
def handle_parse_topic():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'Missing url parameter'}), 400
    
    try:
        result = parse_topic_page(url)
        return jsonify({
            'success': True,
            'title': result.get('title'),
            'content': result.get('comment'),
            'date': result.get('date')
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


    
@app.route('/api/update_thread', methods=['POST'])
def handle_update_thread():
    try:
        data = request.json
        if not data or 'thread_url' not in data:
            return jsonify({"status": "error", "message": "Missing thread_url"}), 400

        thread_data = {
            'thread_url': data['thread_url'],
            'is_answer_sent': data.get('is_answer_sent', True)
        }

        def update_data(session):
            query = f"""
            UPDATE `{threads_table_path}`
            SET is_answer_sent = {thread_data['is_answer_sent']}
            WHERE thread_url = "{thread_data['thread_url']}"
            """
            session.transaction().execute(query, commit_tx=True)

        with ydb.Driver(driver_config) as driver:
            driver.wait(timeout=15)
            with ydb.SessionPool(driver) as pool:
                pool.retry_operation_sync(update_data)

        return jsonify({"status": "success", "message": f"Thread '{thread_data['thread_url']}' successfully updated"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
# Остальные эндпоинты остаются без изменений
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)