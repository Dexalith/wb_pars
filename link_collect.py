from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import json
import time
import re


class LinkCollector:
    def __init__(self):
        self.wb_url = "https://www.wildberries.ru/"
        self.driver = None
        self.setup_driver()

    def setup_driver(self):
        """Настройка браузера"""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

    def collect_product_links(self, query, pages=2):
        """Поиск товаров и сбор ссылок"""
        try:
            encoded_query = query.replace(' ', '%20')
            search_url = f"https://www.wildberries.ru/catalog/0/search.aspx?search={encoded_query}"
            print(f"Ищем товары по запросу: {query}")
            print(f"Переходим по ссылке: {search_url}")

            self.driver.get(search_url)
            time.sleep(5)

            # Ждем загрузки товаров
            WebDriverWait(self.driver, 4).until(
                EC.presence_of_element_located((By.CLASS_NAME, "product-card"))
            )

            product_links = []
            for page in range(1, pages + 1):
                print(f"Обрабатываем страницу {page}")

                # Прокрутка для загрузки всех товаров
                self.scroll_page()
                time.sleep(2)

                # Получаем HTML и извлекаем ссылки
                html = self.driver.page_source
                page_links = self.extract_links_from_page(html)
                product_links.extend(page_links)

                print(f"Найдено товаров на странице: {len(page_links)}")

                # Переход на следующую страницу
                if page < pages:
                    try:
                        next_btn = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.pagination-next"))
                        )
                        if next_btn.is_enabled():
                            self.driver.execute_script("arguments[0].click();", next_btn)
                            time.sleep(3)
                            WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located((By.CLASS_NAME, "product-card"))
                            )
                        else:
                            break
                    except Exception as e:
                        print(f"Не удалось перейти на следующую страницу: {e}")
                        break

            print(f"Всего собрано ссылок на товары: {len(product_links)}")
            return product_links

        except Exception as e:
            print(f"Ошибка при поиске товаров: {e}")
            return []

    def extract_links_from_page(self, html):
        """Извлекаем ссылки на товары со страницы"""
        soup = BeautifulSoup(html, 'html.parser')
        links = []

        # Ищем карточки товаров
        product_cards = soup.find_all('article', {'class': 'product-card'})

        for card in product_cards:
            try:
                # Ищем ссылку в карточке товара
                link_tag = card.find('a', class_='product-card__link')
                if link_tag and link_tag.get('href'):
                    full_url = link_tag['href']
                    links.append(full_url)
            except Exception as e:
                print(f"Ошибка при извлечении ссылки: {e}")
                continue

        return links

    def scroll_page(self):
        """Прокрутка страницы для загрузки всех товаров"""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        for _ in range(3):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def save_links_to_file(self, links, filename="product_links.json"):
        """Сохраняем ссылки в файл"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(links, f, ensure_ascii=False, indent=2)
            print(f"Ссылки сохранены в файл: {filename}")
        except Exception as e:
            print(f"Ошибка при сохранении ссылок: {e}")

    def close(self):
        """Закрытие браузера"""
        if self.driver:
            self.driver.quit()


if __name__ == "__main__":
    collector = LinkCollector()
    try:
        print("Запуск сборщика ссылок Wildberries")

        # Собираем ссылки
        product_links = collector.collect_product_links("пальто из натуральной шерсти", pages=2)

        if product_links:
            # Сохраняем ссылки в файл
            collector.save_links_to_file(product_links)
            print(f"Готово! Собрано {len(product_links)} ссылок")
        else:
            print("Товары не найдены")

    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        collector.close()
        print("Работа завершена")