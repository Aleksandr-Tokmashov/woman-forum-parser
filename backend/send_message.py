from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import os

app = Flask(__name__)

def send_forum_post(forum_url, message):
    # Настройка для работы в виртуальной машине
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")

    # Важные настройки для стабильности
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    try:
        # Инициализация драйвера с таймаутом
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)