#!/usr/bin/env python3
import requests
import json

PLANKA_URL = "http://your_url_planka"
USERNAME = "archiver@planka-account.com"
PASSWORD = "password"
ARCHIVE_BOARD_ID = "archive_board_id"

# Аутентификация
auth = requests.post(f"{PLANKA_URL}/api/access-tokens",
                    json={"emailOrUsername": USERNAME, "password": PASSWORD})
token = auth.json()['item']

headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

# Получаем списки на доске архива
response = requests.get(f"{PLANKA_URL}/api/boards/{ARCHIVE_BOARD_ID}?include=lists",
                       headers=headers)
data = response.json()

print("Колонки на доске 'Архив':")
for lst in data['included']['lists']:
    print(f"  '{lst.get('name')}' - ID: {lst.get('id')}")