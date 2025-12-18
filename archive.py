#!/usr/bin/env python3
"""
РАБОЧИЙ СКРИПТ ДЛЯ АРХИВАЦИИ КАРТОЧЕК В PLANKA
Перемещает карточки из колонки "Выполнено" в архивные колонки на отдельной доске "Архив"
"""

import requests
import json
import os
import sys
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

# ========== КОНФИГУРАЦИЯ ==========
PLANKA_URL = "http://your_planka_url"    # server planka URL
USERNAME = "your_planka_account"                      # Special account login 
PASSWORD = "password"                     # account password
ARCHIVE_DAYS = 14                           
DONE_LIST_NAME = "Done"                # Done list name 
ARCHIVE_BOARD_ID = "archive board id"    # Archive desk ID 

# СОПОСТАВЛЕНИЕ: ID исходной доски -> ID архивной колонки на доске "Архив"
# Формат: {ID_рабочей_доски: ID_колонки_в_архиве}
ARCHIVE_MAPPING = {
    "Desk ID": "List ID",  # Department - list "Department" in archive

}
# =====================================

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('planka_archive.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('planka_archiver')

class PlankaArchiver:
    def __init__(self, base_url: str, username: str, password: str):
        """Инициализация архиватора"""
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.token = None
        self.headers = None
        self._authenticate(username, password)
    
    def _authenticate(self, username: str, password: str) -> None:
        """Аутентификация в Planka"""
        try:
            auth_url = f"{self.base_url}/api/access-tokens"
            logger.info(f"🔐 Аутентификация пользователя {username}...")
            
            response = self.session.post(
                auth_url,
                json={"emailOrUsername": username, "password": password},
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"❌ Ошибка аутентификации: {response.status_code}")
                logger.error(f"Ответ: {response.text[:200]}")
                sys.exit(1)
            
            auth_data = response.json()
            self.token = auth_data.get('item')
            
            if not self.token:
                logger.error("❌ Токен не найден в ответе сервера")
                sys.exit(1)
            
            self.headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            self.session.headers.update(self.headers)
            logger.info("✅ Аутентификация успешна")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при аутентификации: {e}")
            sys.exit(1)
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Выполняет запрос к API Planka"""
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"
        
        try:
            logger.debug(f"📨 {method} {url}")
            response = self.session.request(method, url, **kwargs)
            
            # Проверяем, не вернул ли сервер HTML вместо JSON
            if response.text.strip().startswith(('<!doctype html>', '<html')):
                logger.warning(f"⚠️  Сервер вернул HTML вместо JSON для {endpoint}")
                return None
            
            if response.status_code >= 400:
                logger.error(f"HTTP {response.status_code} для {method} {endpoint}")
                if response.text:
                    logger.error(f"Ошибка: {response.text[:200]}")
                return None
            
            if response.status_code == 204:  # No Content
                return None
            
            if not response.text.strip():
                return None
            
            try:
                return response.json()
            except json.JSONDecodeError:
                logger.error(f"❌ Не удалось разобрать JSON ответ от {url}")
                logger.error(f"Ответ: {response.text[:300]}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка при запросе {method} {url}: {e}")
            return None
    
    def get_board_info(self, board_id: str) -> Optional[Dict]:
        """Получает информацию о доске"""
        result = self._make_request('GET', f'boards/{board_id}')
        if result and 'item' in result:
            return result['item']
        return None
    
    def get_board_lists(self, board_id: str) -> List[Dict]:
        """Получает все списки (колонки) на доске"""
        result = self._make_request('GET', f'boards/{board_id}?include=lists')
        if not result or 'included' not in result:
            return []
        
        included = result['included']
        if 'lists' in included:
            return included['lists']
        return []
    
    def get_board_cards(self, board_id: str) -> List[Dict]:
        """Получает все карточки на доске"""
        result = self._make_request('GET', f'boards/{board_id}?include=cards')
        if not result or 'included' not in result:
            return []
        
        included = result['included']
        if 'cards' in included:
            # Преобразуем карточки в удобный формат
            cards = []
            for card_obj in included['cards']:
                if isinstance(card_obj, dict):
                    cards.append({
                        'id': card_obj.get('id'),
                        'name': card_obj.get('name', 'Untitled'),
                        'listId': card_obj.get('listId'),
                        'boardId': board_id,
                        'updatedAt': card_obj.get('updatedAt', card_obj.get('createdAt', '')),
                        'createdAt': card_obj.get('createdAt', ''),
                    })
            return cards
        return []
    
    def parse_datetime(self, date_str: str) -> Optional[datetime]:
        """Парсит дату из строки формата Planka (2025-12-15T11:42:21.079Z)"""
        if not date_str:
            return None
        
        try:
            # Преобразуем Z в +00:00 для корректного парсинга
            if date_str.endswith('Z'):
                date_str = date_str.replace('Z', '+00:00')
            
            dt = datetime.fromisoformat(date_str)
            
            # Убеждаемся, что есть информация о часовом поясе
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            
            return dt
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга даты '{date_str}': {e}")
            return None
    
    def move_card_between_boards(self, card_id: str, target_board_id: str, target_list_id: str) -> bool:
        """Перемещает карточку на другую доску"""
        # КЛЮЧЕВОЙ МОМЕНТ: Для перемещения между досками нужно указать И boardId, И listId
        data = {
            "boardId": target_board_id,
            "listId": target_list_id,
            "position": 0
        }
        
        result = self._make_request('PATCH', f'cards/{card_id}', json=data)
        return result is not None
    
    def find_done_list_id(self, board_id: str) -> Optional[str]:
        """Находит ID колонки 'Выполнено' на указанной доске"""
        lists = self.get_board_lists(board_id)
        
        for lst in lists:
            if lst.get('name') == DONE_LIST_NAME:
                return lst['id']
        
        return None
    
    def get_archive_list_name(self, board_id: str, archive_list_id: str) -> str:
        """Получает название архивной колонки по её ID"""
        lists = self.get_board_lists(ARCHIVE_BOARD_ID)
        
        for lst in lists:
            if lst.get('id') == archive_list_id:
                return lst.get('name', 'Без названия')
        
        return f"Колонка {archive_list_id}"
    
    def process_source_board(self, source_board_id: str, archive_list_id: str) -> int:
        """Обрабатывает исходную доску: находит старые карточки и перемещает их в архив"""
        logger.info(f"\n📂 Обработка доски ID: {source_board_id}")
        
        # 1. Получаем информацию о доске
        board_info = self.get_board_info(source_board_id)
        if not board_info:
            logger.error(f"❌ Доска {source_board_id} не найдена")
            return 0
        
        board_name = board_info.get('name', f'Доска {source_board_id}')
        logger.info(f"  Название: {board_name}")
        
        # 2. Находим колонку "Выполнено"
        done_list_id = self.find_done_list_id(source_board_id)
        if not done_list_id:
            logger.info(f"  ℹ️ Колонка '{DONE_LIST_NAME}' не найдена")
            return 0
        
        logger.info(f"  ✅ Найдена колонка '{DONE_LIST_NAME}'")
        
        # 3. Получаем название архивной колонки
        archive_list_name = self.get_archive_list_name(ARCHIVE_BOARD_ID, archive_list_id)
        
        # 4. Получаем все карточки на доске
        all_cards = self.get_board_cards(source_board_id)
        
        # Фильтруем карточки из колонки "Выполнено"
        done_cards = [card for card in all_cards if card.get('listId') == done_list_id]
        logger.info(f"  📊 Карточек в '{DONE_LIST_NAME}': {len(done_cards)}")
        
        if not done_cards:
            logger.info(f"  ℹ️ Нет карточек для архивации")
            return 0
        
        # 5. Фильтруем по дате (updatedAt)
        now_utc = datetime.now(timezone.utc)
        cutoff_date = now_utc - timedelta(days=ARCHIVE_DAYS)
        
        logger.info(f"  📅 Архивируем карточки старше: {cutoff_date.strftime('%d.%m.%Y')}")
        logger.info(f"  📅 Текущая дата: {now_utc.strftime('%d.%m.%Y %H:%M')} UTC")
        logger.info(f"  🎯 Целевая колонка: '{archive_list_name}'")
        
        moved_count = 0
        
        for card in done_cards:
            try:
                date_str = card.get('updatedAt')
                if not date_str:
                    continue
                
                card_date = self.parse_datetime(date_str)
                if not card_date:
                    continue
                
                days_old = (now_utc - card_date).days
                
                # Проверяем, старая ли карточка
                if card_date < cutoff_date:
                    card_id = card['id']
                    card_name = card.get('name', f'Карточка {card_id}')
                    card_name_short = card_name[:40] + ('...' if len(card_name) > 40 else '')
                    updated_str = card_date.strftime('%d.%m.%Y')
                    
                    logger.info(f"    📅 '{card_name_short}' ({days_old} дней, обновлена: {updated_str})")
                    
                    # Перемещаем карточку на доску архива
                    if self.move_card_between_boards(card_id, ARCHIVE_BOARD_ID, archive_list_id):
                        logger.info(f"    ✅ Перемещено в '{archive_list_name}'")
                        moved_count += 1
                    else:
                        logger.error(f"    ❌ Ошибка перемещения")
                else:
                    logger.debug(f"    ⏳ '{card.get('name')}' ({days_old} дней) - еще рано")
            
            except Exception as e:
                logger.error(f"    ⚠️ Ошибка обработки карточки {card.get('id')}: {e}")
        
        logger.info(f"  📦 Перемещено: {moved_count} карточек")
        return moved_count
    
    def verify_archive_mapping(self):
        """Проверяет корректность настроек ARCHIVE_MAPPING"""
        logger.info("🔍 Проверка настроек архивации...")
        
        # Проверяем доску архива
        archive_board = self.get_board_info(ARCHIVE_BOARD_ID)
        if not archive_board:
            logger.error(f"❌ Доска архива {ARCHIVE_BOARD_ID} не найдена!")
            return False
        
        archive_board_name = archive_board.get('name', 'Архив')
        logger.info(f"✅ Доска архива: '{archive_board_name}'")
        
        # Получаем все списки на доске архива
        archive_lists = self.get_board_lists(ARCHIVE_BOARD_ID)
        archive_list_names = {lst['id']: lst.get('name', 'Без названия') for lst in archive_lists}
        
        logger.info(f"📋 Колонки на доске архива:")
        for list_id, list_name in archive_list_names.items():
            logger.info(f"  • '{list_name}' (ID: {list_id})")
        
        # Проверяем каждое сопоставление
        for source_board_id, archive_list_id in ARCHIVE_MAPPING.items():
            source_board = self.get_board_info(source_board_id)
            source_board_name = source_board.get('name', f'Доска {source_board_id}') if source_board else 'НЕ НАЙДЕНА'
            
            if archive_list_id in archive_list_names:
                logger.info(f"✅ {source_board_name} → '{archive_list_names[archive_list_id]}'")
            elif archive_list_id == "НАЙДИТЕ_ID":
                logger.warning(f"⚠️  {source_board_name} → НЕ НАСТРОЕНО (замените 'НАЙДИТЕ_ID')")
            else:
                logger.error(f"❌ {source_board_name} → Колонка ID {archive_list_id} НЕ НАЙДЕНА в архиве!")
        
        return True
    
    def run(self):
        """Запускает процесс архивации"""
        logger.info("=" * 60)
        logger.info("🚀 ЗАПУСК АРХИВАЦИИ КАРТОЧЕК")
        logger.info(f"Дней для архивации: {ARCHIVE_DAYS}")
        logger.info(f"Доска архива ID: {ARCHIVE_BOARD_ID}")
        logger.info("=" * 60)
        
        # Проверяем настройки
        if not self.verify_archive_mapping():
            logger.error("❌ Ошибка в настройках архивации!")
            return
        
        total_moved = 0
        
        # Обрабатываем каждую доску по очереди
        for source_board_id, archive_list_id in ARCHIVE_MAPPING.items():
            # Пропускаем не настроенные сопоставления
            if archive_list_id == "НАЙДИТЕ_ID":
                logger.warning(f"\n⚠️  Пропускаем доску {source_board_id} - не настроена архивная колонка")
                continue
            
            moved = self.process_source_board(source_board_id, archive_list_id)
            total_moved += moved
        
        # Итоги
        logger.info("\n" + "=" * 60)
        if total_moved > 0:
            logger.info(f"✅ АРХИВАЦИЯ УСПЕШНО ЗАВЕРШЕНА!")
        else:
            logger.info(f"📊 АРХИВАЦИЯ ЗАВЕРШЕНА")
        logger.info(f"Всего перемещено карточек: {total_moved}")
        logger.info("=" * 60)

def main():
    """Точка входа в программу"""
    try:
        # Проверяем обязательные настройки
        if USERNAME == "ваш_логин" or PASSWORD == "ваш_пароль":
            logger.error("❌ ЗАМЕНИТЕ USERNAME и PASSWORD на ваши реальные данные!")
            sys.exit(1)
        
        # Проверяем наличие не настроенных сопоставлений
        needs_config = False
        for board_id, list_id in ARCHIVE_MAPPING.items():
            if list_id == "НАЙДИТЕ_ID":
                logger.error(f"❌ Замените 'НАЙДИТЕ_ID' для доски {board_id} на реальный ID колонки архива!")
                needs_config = True
        
        if needs_config:
            logger.info("\n💡 Как найти ID архивных колонок:")
            logger.info("   1. Откройте доску 'Архив' в веб-интерфейсе")
            logger.info("   2. Посмотрите ID в URL для каждой колонки")
            logger.info("   3. Или запустите диагностический скрипт для поиска ID")
            sys.exit(1)
        
        # Запускаем архиватор
        archiver = PlankaArchiver(PLANKA_URL, USERNAME, PASSWORD)
        archiver.run()
        
    except KeyboardInterrupt:
        logger.info("\n⚠️  Прервано пользователем")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()