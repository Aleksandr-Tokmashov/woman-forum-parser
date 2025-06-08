import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from time import sleep

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

def parse_topic_pages(links):
    results = []
    
    for link in links:
        try:
            # Загружаем страницу темы
            response = requests.get(link)
            if response.status_code != 200:
                continue
                
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
                results.append({
                    'link': link,
                    'title': title,
                    'comment': comment,
                    'date': date  # Добавляем дату в результат
                })
            
            # Пауза между запросами
            sleep(1)
            
        except Exception as e:
            print(f"Ошибка при обработке {link}: {e}")
            continue
    
    return results

# Пример использования
if __name__ == "__main__":
    # Получаем ссылки (используем предыдущую функцию)
    links = parse_woman_forum()
    print(f"Получено {len(links)} ссылок для парсинга")
    
    # Парсим содержимое страниц (первые 5 для примера)
    parsed_data = parse_topic_pages(links[:10])
    
    # Выводим результаты
    for i, item in enumerate(parsed_data, 1):
        print(f"\nРезультат {i}:")
        print(f"Ссылка: {item['link']}")
        print(f"Заголовок: {item['title']}")
        print(f"Комментарий: {item['comment'][:100] + '...' if item['comment'] else 'Нет комментария'}")
        print(f"Дата: {item['date']}")