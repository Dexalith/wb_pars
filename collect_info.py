from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
import re
import random


class ProductParser:
    def __init__(self):
        self.driver = None
        self.setup_driver()

    def setup_driver(self):
        """Настройка Chrome драйвера"""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

    def load_links_from_file(self, filename="product_links.json"):
        """Загружаем ссылки из файла"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                links = json.load(f)
            print(f"Загружено {len(links)} ссылок из файла {filename}")
            return links
        except Exception as e:
            print(f"Ошибка при загрузке ссылок: {e}")
            return []

    def parse_product_from_link(self, product_url):
        """Парсим данные товара по ссылке"""
        try:
            print(f"Парсим товар: {product_url}")

            # Переходим по ссылке
            self.driver.get(product_url)
            time.sleep(3)

            # Проверяем, что страница загрузилась
            if "detail.aspx" not in self.driver.current_url:
                print(f"Страница не загрузилась: {product_url}")
                return None

            # Получаем данные со страницы товара
            product_data = self.parse_product_page()

            if product_data:
                product_data['url'] = product_url
                # Извлекаем артикул из URL
                articul_match = re.search(r'/(\d+)/detail', product_url)
                if articul_match:
                    product_data['articul'] = articul_match.group(1)

                print(f"Успешно обработан артикул: {product_data.get('articul', 'N/A')}")
                return product_data
            else:
                print(f"Не удалось спарсить: {product_url}")
                return None

        except Exception as e:
            print(f"Ошибка при парсинге {product_url}: {e}")
            return None

    def parse_product_page(self):
        """Парсим данные со страницы товара"""
        product_data = {}

        try:
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

            # Название товара
            product_data['name'] = self.get_product_name(soup)

            # Цена
            product_data['price'] = self.get_product_price(soup)

            # Рейтинг
            product_data['rating'] = self.get_product_rating(soup)

            # Количество отзывов
            product_data['reviews_count'] = self.get_reviews_count(soup)

            # Описание
            product_data['description'] = self.get_product_description(soup)

            # Изображения
            images = self.get_product_images(soup)
            product_data['images'] = ', '.join(images) if images else ""

            # Характеристики
            characteristics = self.get_characteristics(soup)
            product_data['characteristics'] = json.dumps(characteristics, ensure_ascii=False) if characteristics else ""

            # Продавец
            seller_info = self.get_seller_info(soup)
            product_data.update(seller_info)

            return product_data

        except Exception as e:
            print(f"Ошибка при парсинге страницы товара: {e}")
            return None

    def get_product_name(self, soup):
        """Получаем название товара"""
        try:
            name_tag = soup.find('h1')
            if name_tag:
                return name_tag.get_text(strip=True)

            # Альтернативные селекторы
            name_selectors = [
                ".productHeader--G5fu8",
                "[data-link*='text']",
                "h1.product-page__header"
            ]

            for selector in name_selectors:
                name_elem = soup.select_one(selector)
                if name_elem:
                    return name_elem.get_text(strip=True)

            return "Название не найдено"
        except:
            return "Ошибка при получении названия"

    def get_product_price(self, soup):
        """Получаем цену товара"""
        try:
            # Ищем все элементы с ценами
            price_elements = soup.find_all(['span', 'div', 'ins'],
                                           class_=re.compile(r'price|Price'))

            for element in price_elements:
                price_text = element.get_text(strip=True)
                if '₽' in price_text and any(char.isdigit() for char in price_text):
                    print(f"Найден элемент с ценой: '{price_text}'")

                    # Берем весь текст цены как есть
                    prices = price_text.split('₽')
                    if prices:
                        first_price = prices[0].strip()
                        print(f"Первая цена: '{first_price}'")
                        return first_price

            return "Цена не найдена"

        except Exception as e:
            print(f"Ошибка при получении цены: {e}")
            return "Ошибка получения цены"

    def get_product_rating(self, soup):
        """Получаем рейтинг товара"""
        try:
            rating_selectors = [
                ".product-page__reviews-icon",
                ".address-rate-mini",
                ".sellerRatingWrap--qfxW5 span",
                "[class*='rating']"
            ]

            for selector in rating_selectors:
                rating_tag = soup.select_one(selector)
                if rating_tag:
                    rating_text = rating_tag.get_text(strip=True).replace(',', '.')
                    rating_match = re.search(r'[\d.]+', rating_text)
                    if rating_match:
                        try:
                            return float(rating_match.group())
                        except ValueError:
                            continue
            return 0.0
        except:
            return 0.0

    def get_reviews_count(self, soup):
        """Получаем количество отзывов"""
        try:
            reviews_selectors = [
                ".product-page__reviews-text",
                "[class*='reviews-count']",
                "[class*='review-count']"
            ]

            for selector in reviews_selectors:
                reviews_tag = soup.select_one(selector)
                if reviews_tag:
                    reviews_text = reviews_tag.get_text(strip=True)
                    reviews_match = re.search(r'\d+', reviews_text)
                    if reviews_match:
                        return int(reviews_match.group())
            return 0
        except:
            return 0

    def get_product_description(self, soup):
        """Получаем описание товара"""
        try:
            desc_selectors = [
                "p.collapsable__text",
                ".product-page__description",
                ".description__text"
            ]

            for selector in desc_selectors:
                desc_tag = soup.select_one(selector)
                if desc_tag:
                    return desc_tag.get_text(strip=True)
            return "Описание отсутствует"
        except:
            return "Ошибка при получении описания"

    def get_product_images(self, soup):
        """Получаем изображения товара"""
        images = []
        try:
            img_tags = soup.find_all('img', src=re.compile(r'\.(webp|jpg|png|jpeg)'))
            for img in img_tags:
                src = img.get('src') or img.get('data-src')
                if src and src.startswith('http') and src not in images:
                    if any(pattern in src for pattern in ['images.wbstatic.net', 'basket-', 'geobasket']):
                        images.append(src)
                        if len(images) >= 10:
                            break
        except Exception as e:
            print(f"Ошибка при получении изображений: {e}")
        return images

    def get_characteristics(self, soup):
        """Получаем характеристики товара"""
        characteristics = {}
        try:
            spec_section = soup.find('div', class_='product-params')
            if spec_section:
                rows = spec_section.find_all('div', class_='product-params__row')
                for row in rows:
                    key_elem = row.find('span', class_='product-params__label')
                    value_elem = row.find('span', class_='product-params__value')
                    if key_elem and value_elem:
                        key = key_elem.get_text(strip=True)
                        value = value_elem.get_text(strip=True)
                        characteristics[key] = value
        except Exception as e:
            print(f"Ошибка при получении характеристик: {e}")
        return characteristics

    def get_seller_info(self, soup):
        """Получаем информацию о продавце"""
        seller_info = {}
        try:
            seller_selectors = [
                ".sellerAndBrandItemName--RV73r",
                ".seller-info__name",
                "[class*='seller-name']"
            ]

            for selector in seller_selectors:
                seller_tag = soup.select_one(selector)
                if seller_tag:
                    seller_info['seller_name'] = seller_tag.get_text(strip=True)
                    break

            seller_link_selectors = [
                "a.seller-info__name",
                "[class*='seller-link']"
            ]

            for selector in seller_link_selectors:
                seller_link = soup.select_one(selector)
                if seller_link and seller_link.get('href'):
                    seller_href = seller_link.get('href')
                    seller_info['seller_url'] = "https://www.wildberries.ru" + seller_href
                    break

        except Exception as e:
            print(f"Ошибка при получении информации о продавце: {e}")

        # Заполняем обязательные поля
        if 'seller_name' not in seller_info:
            seller_info['seller_name'] = "Продавец не указан"
        if 'seller_url' not in seller_info:
            seller_info['seller_url'] = ""

        return seller_info

    def export_to_excel(self, products, filename="wildberries_catalog.xlsx"):
        """Экспорт данных в Excel"""
        try:
            if not products:
                print("Нет данных для экспорта")
                return

            df = pd.DataFrame(products)

            if df.empty:
                print("DataFrame пустой")
                return

            print(f"Экспортируем {len(df)} товаров в Excel...")
            df.to_excel(filename, index=False)
            print(f"Основной каталог сохранен в {filename}")

            # Фильтрованный файл
            if 'rating' in df.columns and 'price' in df.columns:
                # Преобразуем цены в числа для фильтрации
                def parse_price(price_str):
                    if isinstance(price_str, str):
                        numbers = re.findall(r'\d+', price_str.replace(' ', ''))
                        return int(numbers[0]) if numbers else 0
                    return price_str

                df['price_numeric'] = df['price'].apply(parse_price)

                filtered_df = df[
                    (df['rating'] >= 4.5) &
                    (df['price_numeric'] <= 10000)
                    ]

                if not filtered_df.empty:
                    filtered_filename = "filtered_catalog.xlsx"
                    filtered_df.to_excel(filtered_filename, index=False)
                    print(f"Фильтрованный каталог сохранен в {filtered_filename}")
                    print(f"В фильтрованном каталоге: {len(filtered_df)} товаров")
                else:
                    print("Нет товаров, соответствующих фильтру")

        except Exception as e:
            print(f"Ошибка при экспорте в Excel: {e}")

    def close(self):
        """Закрытие драйвера"""
        if self.driver:
            self.driver.quit()


if __name__ == "__main__":
    parser = ProductParser()
    try:
        print("Запуск парсера товаров Wildberries...")

        # Загружаем ссылки из файла
        product_links = parser.load_links_from_file("product_links.json")

        if not product_links:
            print("Не найдено ссылок в файле")
            exit()

        print(f"Загружено {len(product_links)} ссылок")

        # Парсим каждый товар
        print("Начинаем парсинг товаров...")
        all_products = []

        # Ограничиваем количество для теста
        test_links = product_links[:15]

        for i, link in enumerate(test_links):
            print(f"Обрабатываем товар {i + 1}/{len(test_links)}")

            # Добавляем задержку между запросами
            time.sleep(random.uniform(2, 4))

            product_data = parser.parse_product_from_link(link)
            if product_data:
                all_products.append(product_data)

        print(f"Успешно обработано товаров: {len(all_products)}")

        # Экспорт в Excel
        if all_products:
            parser.export_to_excel(all_products)
            print("\nСобранные данные:")
            for product in all_products:
                print(
                    f"  - {product.get('name', 'N/A')[:50]}... | Цена: {product.get('price', 'N/A')} | Рейтинг: {product.get('rating', 'N/A')}")
        else:
            print("Не удалось собрать данные о товарах")

    except Exception as e:
        print(f"Критическая ошибка: {e}")
    finally:
        parser.close()
        print("Парсер товаров завершил работу")