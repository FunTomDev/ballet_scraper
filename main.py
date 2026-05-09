from parsers import BolshoyParser, RboParser, OperadeparisParser, JacParser, AbtParser, WienerParser, MariinskyParser, ScalaParser
import os
import json
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials

bolshoy = BolshoyParser()
rbo = RboParser()
operadeparis = OperadeparisParser()
jac = JacParser()
abt = AbtParser()
wiener = WienerParser()
mariinsky = MariinskyParser()
scala = ScalaParser()

if not os.path.exists("data/"):
    os.mkdir("data/")

with open("data/bolshoi_shows.json", "w", encoding="utf-8") as file:
    json.dump(bolshoy.shows, file, indent=4, ensure_ascii=False)

with open("data/rbo_shows.json", "w", encoding="utf-8") as file:
    json.dump(rbo.shows, file, indent=4, ensure_ascii=False)

with open("data/operadeparis_shows.json", "w", encoding="utf-8") as file:
    json.dump(operadeparis.shows, file, indent=4, ensure_ascii=False)

with open("data/jac_shows.json", "w", encoding="utf-8") as file:
    json.dump(jac.shows, file, indent=4, ensure_ascii=False)

with open("data/abt_shows.json", "w", encoding="utf-8") as file:
    json.dump(abt.shows, file, indent=4, ensure_ascii=False)

with open("data/wiener_shows.json", "w", encoding="utf-8") as file:
    json.dump(wiener.shows, file, indent=4, ensure_ascii=False)

with open("data/mariinsky_shows.json", "w", encoding="utf-8") as file:
    json.dump(mariinsky.shows, file, indent=4, ensure_ascii=False)

with open("data/scala_shows.json", "w", encoding="utf-8") as file:
    json.dump(scala.shows, file, indent=4, ensure_ascii=False)

def extract_performance_info(parser):
    today = datetime.now().date()
    today_perf = None
    next_perf = None
    sorted_shows = sorted(parser.shows, key=lambda x: datetime.strptime(x['Дата'], "%Y.%m.%d").date())
    for show in sorted_shows:
        show_date = datetime.strptime(show['Дата'], "%Y.%m.%d").date()
        if today_perf and next_perf:
            break
        if show_date == today and not today_perf:
            today_perf = show
        elif show_date > today and not next_perf:
            if parser.name =="American Ballet Theatre":
                print(f"Next performance for {parser.name} found: {show['Дата']}")
            next_perf = show
    return today_perf, next_perf

def collect_data(parsers):
    data = []
    for parser in parsers:
        today_perf, next_perf = extract_performance_info(parser)
        row = [
            getattr(parser, 'name', ''),  # Название театра
            getattr(parser, 'domain', ''),  # Ссылка на театр
        ]
        # Сегодняшний спектакль
        if today_perf:
            row += [
                today_perf.get('Дата', ''),
                today_perf.get('Название', ''),
                today_perf.get('Ссылка', ''),
                today_perf.get('Описание', ''),
                today_perf.get('Имена', ''),
                today_perf.get('Изображение', ''),
                today_perf.get('Самый дорогой билет', ''),
                today_perf.get('Самый дешевый билет', ''),
            ]
        else:
            row += [''] * 8
            
        if next_perf:
            row += [
                next_perf.get('Дата', ''),
                next_perf.get('Название', ''),
                next_perf.get('Ссылка', ''),
                next_perf.get('Описание', ''),
                next_perf.get('Имена', ''),
                next_perf.get('Изображение', ''),
                next_perf.get('Самый дорогой билет', ''),
                next_perf.get('Самый дешевый билет', ''),
            ]
        else:
            row += [''] * 8
        data.append(row)
    return data

def save_to_google_sheet(sheet_name, headers, data, creds_json_path):
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(creds_json_path, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open(sheet_name).sheet1
    sheet.clear()
    sheet.append_row(headers)
    for row in data:
        sheet.append_row(row)

parsers = [bolshoy, rbo, operadeparis, jac, abt, wiener, mariinsky, scala]
headers = [
    "Название театра", "Ссылка на театр",
    "Дата сегодня", "Название балета", "Ссылка на балет", "Описание", "Имена", "Изображение", "Самый дорогой билет", "Самый дешевый билет",
    "Дата ближайшего спектакля", "Название балета", "Ссылка на балет", "Описание", "Имена", "Изображение", "Самый дорогой билет", "Самый дешевый билет"
]
data = collect_data(parsers)
save_to_google_sheet("Ballet performances", headers, data, "credentials.json")


