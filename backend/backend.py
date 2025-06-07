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
from flask import Flask, request, jsonify
from flask_cors import CORS  # Добавьте этот импорт

app = Flask(__name__)
CORS(app) 


# Инициализация Yandex Cloud ML
def load_credentials():
    yc_token = os.popen("yc iam create-token").read().strip()
    set_key(".env", "AUTH", yc_token)
    load_dotenv()
    
    folder_id = os.getenv("FOLDER_ID")
    auth = os.getenv("AUTH")

    if not folder_id or not auth:
        raise ValueError("Не найдены FOLDER_ID или AUTH в .env файле!")

    return YCloudML(folder_id=folder_id, auth=auth)

try:
    sdk = load_credentials()
    model = sdk.models.completions("yandexgpt").configure(temperature=0.5)
except Exception as e:
    print(f"Ошибка инициализации Yandex Cloud ML: {str(e)}")
    model = None

# 1. Функция анализа негатива
def contains_negativity(text: str) -> bool | str:
    if not model:
        return "Сервис анализа текста недоступен"
    
    negativity_prompt = f"""
    Проанализируй, содержит ли пост негатив.
    
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

# 2. Функция отправки поста на форум
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

# 3. Функция парсинга списка тем форума
def parse_woman_forum():
    base_url = "https://www.woman.ru/forum/"
    sort_param = "?sort=1d"
    page = 1
    unique_links = set()
    
    while True:
        if page == 1:
            url = base_url + sort_param
        else:
            url = f"{base_url}{page}/{sort_param}"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                break
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            if soup.find(class_="error-page__content error-page__wrapper"):
                break
                
            topic_links = soup.find_all('a', class_='list-item__link')
            for link in topic_links:
                href = link.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    unique_links.add(full_url)
            
            page += 1
            time.sleep(1)
            
        except Exception as e:
            print(f"Ошибка при парсинге страницы {page}: {str(e)}")
            break
    
    return list(unique_links)

# 4. Функция парсинга отдельных тем
def parse_topic_page(link):
    try:
        response = requests.get(link, timeout=10)
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title_element = soup.find(class_="card__topic-title")
        title = title_element.get_text(strip=True) if title_element else None
        
        comment_element = soup.find(class_="card__comment")
        comment = comment_element.get_text(strip=True) if comment_element else None
        
        if title or comment:
            return {
                'link': link,
                'title': title,
                'comment': comment
            }
        return None
        
    except Exception as e:
        print(f"Ошибка при обработке {link}: {e}")
        return None

def parse_topic_pages(links):
    results = []
    
    # Используем ThreadPool для ускорения парсинга
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(parse_topic_page, link) for link in links]
        for future in futures:
            result = future.result()
            if result:
                results.append(result)
            time.sleep(0.5)  # Задержка между запросами
    
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
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)

