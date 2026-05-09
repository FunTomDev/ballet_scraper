from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import json
import os
import asyncio, aiohttp
from datetime import datetime, timedelta
import requests
import undetected_chromedriver as uc
from bs4 import BeautifulSoup as bs
import calendar

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://bolshoi.ru/",
}
class BolshoyParser():
    def __init__(self):
        self.api_domain = "https://bolshoi.ru/cms/api/"
        self.domain = "https://bolshoi.ru/"
        self.cookies = self.get_qrator_cookies()
        self.name = "Большой театр"

        self.shows = asyncio.run(self.scrape())

    async def scrape(self):
        ballet_shows_data_api = "https://bolshoi.ru/ticket-api/shows"
        ballet_shows_list_api = "https://www.bolshoi.ru/cms/api/performances/ballet/?format=json&utm_referrer=https%3A%2F%2Fwww.bolshoi.ru%2Fcms%2Fapi%2Fperformances%2Fballet%2F"
        try:
            async with aiohttp.ClientSession(headers={**HEADERS, "Cookie": self.cookies}) as session:
                async with session.get(ballet_shows_list_api, headers={**HEADERS, "Cookie": self.cookies}) as response:
                    shows_list = json.loads(await response.text())
                async with session.get(ballet_shows_data_api, headers={**HEADERS, "Cookie": self.cookies}) as response:
                    shows_data = json.loads(await response.text())
                
                common_items = []
                for item in shows_data:
                    for show in shows_list:
                        if item['showName'] in show['title']:
                            common_items.append({
                                "Название": item["showName"],
                                "Ссылка": self.domain.rstrip('/') + show['url'] if show['url'].startswith('/') else show['url'],
                                'Api_url': self.api_domain.rstrip('/') + show['url'] if show['url'].startswith('/') else show['url'],
                                "Дата": item['specDate'].replace('-', '.'),
                                "Самый дорогой билет": item['maxPrice'],
                                "Самый дешевый билет": item['minPrice'],
                                "Изображение": show['image2x'],
                            })
                
                tasks = [self.get_performances_data(session, show) for show in common_items]
                shows = await asyncio.gather(*tasks)

                return shows

        except Exception as e:
            print(f"Couldn't get Bolshoy data - {e}")
            return []
    
    async def get_performances_data(self, session, item):
        try:
            async with session.get(item['Api_url']+"?format=json", headers={**HEADERS, "Cookie": self.cookies}) as response:
                details = json.loads(await response.text())
                description = bs(details['detail']['about']['text'], 'html.parser')
                directors = bs(details['detail']['directors']['beforeText'], 'html.parser')
                item['Описание'] = description.get_text(" ", strip=True)
                item['Имена'] = directors.get_text(" ", strip=True)
        except Exception as e:  
            print(f"Could not get performance details for {item['Название']}: {e}")
            item['Описание'] = ''
            item['Имена'] = ''

        return item

    def get_qrator_cookies(self):
        shows_data_api = "https://bolshoi.ru/ticket-api/shows"

        options = uc.ChromeOptions()
        options.add_argument("--window-position=-32000,-32000")  # offscreen
        driver = uc.Chrome(options=options)

        driver.get(shows_data_api)
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, 'pre')))

        bad_cookies = {item['name']: item['value'] for item in driver.get_cookies()}

        cookies = "; ".join([f"{k}={v}" for k, v in bad_cookies.items()])
        return cookies

class RboParser():
    def __init__(self):
        self.domain = "https://www.rbo.org.uk/"
        self.name = "Royal Ballet"
        self.shows = self.scrape()
    
    def scrape(self):
        available_shows = self.get_available_shows()
        return self.get_shows_data(available_shows)

    def get_available_shows(self):
        url = "https://www.rbo.org.uk/api/availability/"
        try:
            with requests.Session() as session:
                r = session.get(url)
                availability = r.json()['data']
                available_shows = {}
                for item in availability:
                    if not item['attributes']['ticketsAvailable']:
                        print(f"Show with id: {item['id']} has no available tickets - can't get ticket prices")
                    else:
                        available_shows[item['id']] = {
                                "max_price": item['attributes']['maxPriceAvailable'] if item['attributes']['maxPriceAvailable'] else '0',
                                "min_price": item['attributes']['minPriceAvailable'] if item['attributes']['minPriceAvailable'] else '0'
                            }
            return available_shows
        except Exception as e:
            print(f"Couldn't get available shows: {e}")
            return {}
    
    def get_shows_data(self, available_shows):
        try:
            url = "https://www.rbo.org.uk/api/events"
            with requests.Session() as session:
                r = session.get(url)
                data = r.json()['data']
                shows = []
                for item in data:
                    if '922' in [tag['id'] for tag in item['relationships']['tags']['data']] and item['id'].isdigit() and item['id'] in available_shows.keys():
                        shows.append({
                            "Название": item['attributes'].get("title", ""),
                            "Ссылка": self.domain.rstrip('/') + "/tickets-and-events/" + item['attributes']['slug'] + "-details",
                            "Дата": item['attributes']['performances'][0]['date'][:10].replace('-', '.'),
                            "Самый дорогой билет": available_shows[item['id']]['max_price'],
                            "Самый дешевый билет": available_shows[item['id']]['min_price'],
                            "Изображение": item['attributes']['imageTray']['desktopPath'],
                            "Имена": "",
                            "Описание": bs(item['attributes']['description'].rstrip('\n'), 'html.parser').get_text("\n", strip=True),
                        })
                return shows
        except Exception as e:
            print(f"Couldn't get shows data: {e}")
            return []

class OperadeparisParser():
    def __init__(self):
        self.domain = "https://www.operadeparis.fr/"
        self.name = "Opéra de Paris"
        self.shows = asyncio.run(self.scrape())
    
    async def scrape(self):
        async with aiohttp.ClientSession() as session:
            return await self.get_shows(session)

    async def get_shows(self, session):
        tasks = [self.get_page_data(session, page) for page in range(1, 6)]
        data = [item for sublist in await asyncio.gather(*tasks) for item in sublist]
        tasks = []
        for item in data:
            show = {
                "Название": item.get("title", ""),
                "Ссылка": item.get('full_url', ''),
                "Дата": item.get('next_performance_date', '').split(' ')[0].replace('-', '.'),
                "Изображение": item['main_media'].get('media', '') if item['main_media'] else '',
                "Имена": "",
            }
            tasks.append(self.get_show_details(session, show))
        
        shows = await asyncio.gather(*tasks)
        return shows

    async def get_page_data(self, session, page):
        url = f"https://www.operadeparis.fr/ajax/agenda/details/spectacles-ballet?page={page}"
        async with session.get(url) as response:
            page_data = await response.json()
            return [item for item in page_data['data']] 

    async def get_show_details(self, session, show):
        url = show['Ссылка'].rstrip('/') + '/performances'
        async with session.get(url) as response:
            details = await response.json()
            prices = details['body']['rows'][0]
            sorted_prices = sorted([int(item['price'].split(' ')[0]) for item in prices['categories']], key=lambda x: x)
            if len(sorted_prices) == 0:
                min_price = 0
                max_price = 0
            else:
                min_price = sorted_prices[0]
                max_price = sorted_prices[-1]
            
            show["Самый дорогой билет"] = max_price
            show["Самый дешевый билет"] = min_price
        
        async with session.get(show['Ссылка']) as response:
            page = bs(await response.text(), 'html.parser')
            description = page.find('div',  {'class': 'component-text-max-line__texts'}).get_text(' ', strip=True).replace('\xa0', ' ')
            show['Описание'] = description

        return show

class JacParser():
    def __init__(self):
        self.name = "New National Theatre Tokyo"
        self.domain = "https://www.nntt.jac.go.jp/"
        self.shows = asyncio.run(self.scrape())

    async def scrape(self):
        async with aiohttp.ClientSession() as session:
            shows = await self.get_performances(session)
            return shows

    async def get_performances(self, session):
        url = "https://www.nntt.jac.go.jp/ballet/js/performance.json"
        shows = []
        tasks = []
        async with session.get(url) as response:
            data = await response.json()
            for item in data:
                soup = bs(item['detail'], 'html.parser')
                show = {
                    "Название": soup.get_text(' ', strip=True),
                    "Ссылка": item['url'],
                    "Дата": item['startDate'].replace('/', '.'),
                    "Изображение": item['image_sp'],
                }
                shows.append(show)
                tasks.append(self.get_details(session, show))

            shows = await asyncio.gather(*tasks)
            return shows

    async def get_details(self, session, show):
        url = show['Ссылка']
        async with session.get(url) as response:
            page = await response.text()
            soup = bs(page, 'html.parser')
            description = soup.find('div', class_='gd__introductionInner').find('p').get_text(' ', strip=True)
            names = ', '.join([li.get_text(' ', strip=True) for li in soup.find('div', class_='gd__StaffBoxLeft').find_all('li') if len(li.find_all()) == 0])
            prices = [int(item.get_text(' ', strip=True)[:-1].replace(',', '')) for item in soup.find('div', class_='gd__Ticket').find('table', class_='gd__CommonTable01').find_all('td', {'class': 'gd__CommonTableStyle04'})]
            max_price = max(prices)
            min_price = min(prices)
            show['Описание'] = description
            show["Самый дорогой билет"] = max_price
            show["Самый дешевый билет"] = min_price
            show['Имена'] = names
        return show

class AbtParser():
    def __init__(self):
        self.name = "American Ballet Theatre"
        self.domain = "https://www.abt.org/"
        self.shows = asyncio.run(self.scrape())
    
    async def scrape(self):
        try:
            async with aiohttp.ClientSession() as session:
                shows = await self.get_performances(session)
                return shows
        except Exception as e:
            print("Couldn't get data from session:", e)

    async def get_performances(self, session):
        url = 'https://www.abt.org/wp-admin/admin-ajax.php?action=get_calendar_events'
        start = datetime.now().date()
        end = (datetime.now() + timedelta(days=90)).date()
        payload = {
            "event_category[]": ["Performance", "Special Events"],
            "filter_performance[]": ["32"],
            "start": start.strftime("%Y-%m-%d"),
            "end": end.strftime("%Y-%m-%d")
        }

        try:
            async with session.post(url, data=payload) as response:
                data = json.loads(await response.text())
                shows = []
                tasks = []
                for item in data:
                    soup = bs(item['popup'], 'html.parser')
                    url = soup.find('p', class_='buttons').find_all('a', {'class': 'btn'})[-1]['href']
                    description = soup.find('div', class_='descriptionfull').get_text(' ', strip=True).replace('\xa0', ' ')
                    names = soup.find('p', class_='people').get_text(' ', strip=True)
                    show = {
                        "Название": item['title'],
                        "Ссылка": url,
                        "Описание": description,
                        "Дата": item['start'][:10].replace('-', '.'),
                        "Имена": names,
                        "Самый дорогой билет": 220,
                        "Самый дешевый билет": 35,
                    }

                    tasks.append(self.get_image(session, show))

                shows = await asyncio.gather(*tasks)

                return shows
        except Exception as e:
            print("Couldn't get performance data:", e)
            return []
    async def get_image(self, session, show):
        url = show['Ссылка']
        async with session.get(url) as response:
            soup = bs(await response.text(), 'html.parser')
            div_element = soup.find('div', id='pm-wrap')

            if div_element and 'style' in div_element.attrs:
                style_attribute = div_element['style']
                if 'background-image' in style_attribute:
                    # Extract the URL from the style string
                    url_start_index = style_attribute.find("url('") + 5
                    url_end_index = style_attribute.find("')")
                    image_url = style_attribute[url_start_index:url_end_index]
                    show['Изображение'] = image_url
                else:
                    print("The 'style' attribute does not contain 'background-image'.")
            else:
                print("Element with id 'pm-wrap' or its style could not be located")
        return show

class WienerParser():
    def __init__(self):

        self.months = {
            "january": "januar",
            "february": "februar",
            "march": "maerz",
            "april": "april",
            "may": "mai",
            "june": "juni",
            "september": "september",
            "october": "oktober",
            "november": "november",
            "december": "dezember"
        }

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        }

        self.domain = "https://www.wiener-staatsoper.at/"
        self.name = "Wiener Staatsoper"
        self.shows = asyncio.run(self.scrape())

    async def scrape(self):
        try:
            async with aiohttp.ClientSession() as session:
                shows = await self.get_performances(session)
                return shows
        except Exception as e:
            print("Couldn't create session:", e)
            return []

    async def get_performances(self, session):
        current_month_name_en = datetime.now().strftime('%B').lower()
        current_month_no = datetime.now().month
        next_month_no = current_month_no + 1
        next_month_name_en = calendar.month_name[next_month_no].lower()

        this_month_url = f"https://www.wiener-staatsoper.at/kalender/ballett/2025/{self.months[current_month_name_en]}"
        next_month_url = f"https://www.wiener-staatsoper.at/kalender/ballett/2025/{self.months[next_month_name_en]}"

        try:
            async with session.get(this_month_url) as response:
                soup = bs(await response.text(), 'html.parser')
                event_details_links = [f"https://www.wiener-staatsoper.at/_ticket-infos/16e3d5776547e890c267da9dc31f02c3/default.{item['data-event'].lstrip('eventItem')}.de.html" for item in soup.find_all('div', {'class': 'sticky-date'})]
                print(event_details_links)

                tasks = []
                shows = []
                for link in event_details_links:
                    tasks.append(self.get_details(session, link))
                
                shows = await asyncio.gather(*tasks)

            async with session.get(next_month_url) as response:
                soup = bs(await response.text(), 'html.parser')
                event_details_links = [f"https://www.wiener-staatsoper.at/_ticket-infos/16e3d5776547e890c267da9dc31f02c3/default.{item['data-event'].lstrip('eventItem')}.de.html" for item in soup.find_all('div', {'class': 'sticky-date'})]

                tasks = []
                for link in event_details_links:
                    tasks.append(self.get_details(session, link))
                
                append_showlist = [item for item in await asyncio.gather(*tasks) if item is not None]
                shows += append_showlist
            
            print(shows)
            return shows

        except Exception as e:
            print("Couldn't get performances list from given urls :", e)
            return []

    async def get_details(self, session, url):
        try:
            async with session.get(url) as response:
                soup = bs(await response.text(), 'html.parser')

                link = self.domain.rstrip('/') + soup.find('div', class_='btn-row').find_all('a')[-1]['href']
                date = datetime.strptime(soup.find('div', class_='offcanvas-header').find('p').get_text(' ', strip=True), '%A %d. %B %Y').strftime('%Y.%m.%d')
                prices = [int(item.get_text(' ', strip=True).split(' ')[0]) for item in soup.find_all('span', 'category-price')[:-1]]
                max_price = max(prices)
                min_price = min(prices)
            
            async with session.get(link) as response:
                soup = bs(await response.text(), 'html.parser')
                image = soup.find('div', id='production-video').find('img')['src']
                if not image:
                    image = ''
                
                title = soup.find('h1', id='eventHeadline').get_text(' ', strip=True)

                cast_element = soup.find('div', class_='production-cast')
                cast_slides = cast_element.find_all('div', 'swiper-slide')
                names = ', '.join([item.get_text(': ', strip=True) for slide in cast_slides for item in slide.find_all('div', recursive=False)])
                description = ' '.join([item.get_text(' ', strip=True) for item in soup.find('div', {'class': 'frame frame-default frame-type-text frame-layout-0'}).find_all('p')])

                show = {
                        "Название": title,
                        "Ссылка": link,
                        "Описание": description,
                        "Дата": date,
                        "Имена": names,
                        "Самый дорогой билет": max_price,
                        "Самый дешевый билет": min_price,
                        "Изображение": image,
                    }
                print(show)
                return show

        except Exception as e:
            print(f"Couldn't get details from url {url}: {e}")
            return

class MariinskyParser():
    def __init__(self):
        self.domain = 'https://www.mariinsky.ru/'
        self.name = "Mariinsky Theatre"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        }

        self.shows = asyncio.run(self.scrape())
    
    async def scrape(self):
        try:
            async with aiohttp.ClientSession() as session:
                shows = await self.get_performances(session)
                return shows
        
        except Exception as e: 
            print("Couldn't create session:", e)
            return []
    
    async def get_performances(self, session):
        url = 'https://www.mariinsky.ru/playbill/playbill/?type=ballet'
        try:
            async with session.get(url) as response:
                soup = bs(await response.text(), 'html.parser')
                performance_divs = soup.find_all('div', class_='c_ballet')

                tasks = []
                for div in performance_divs:
                    try:
                        ticket_link = 'https:' + div.find('div', class_='t_button').find('a')['href'].replace('/ru/', '/en/')
                    except Exception as e:
                        print("Couldn't get ticket link:", e)
                        continue
                    details_link = self.domain.rstrip('/') + div.find('div', class_='spec_name').find('a')['href']
                    print([ticket_link, details_link])
                    tasks.append(self.get_details(session, [ticket_link, details_link]))
                
                shows = await asyncio.gather(*tasks)
                return shows
            
        except Exception as e:
            print("Couldn't get performances 469:", e)
            return []

    async def get_details(self, session, links):
        try:
            max_retries = 15
            delay = 2
            for i in range(max_retries):
                try:
                    async with session.get(links[0], timeout=aiohttp.ClientTimeout(total=20)) as response:
                        if response.status in [503, 504]:
                            print(f"Attempt {i+1}/{max_retries}: Got {response.status} error. Retrying in {delay} seconds...")
                            await asyncio.sleep(delay)
                            delay *= 2
                            continue
                        response.raise_for_status()
                        soup = bs(await response.text(), 'lxml')
                        min_price = int(soup.find('min_price').get_text(' ', strip=True))
                        max_price = int(soup.find('max_price').get_text(' ', strip=True))
                        date = datetime.strptime(soup.find('date').get_text(' ', strip=True), '%d %B %Y, %A').strftime('%Y.%m.%d')
                        break
                except Exception as e:
                    print(f"Error on attempt {i+1}: {e}")
                    await asyncio.sleep(delay)
                    delay *= 2
            else:
                print(f"Failed to get ticket data from {links[0]} after {max_retries} attempts.")
                date = ''
                min_price = 0
                max_price = 0
        except Exception as e:
            print(f"Couldn't get ticket data from {links[0]}:", e)
            date = ''
            min_price = 0
            max_price = 0
        
        try:
            async with session.get(links[1]) as response:
                soup = bs(await response.text(), 'html.parser')
                title = soup.find('h1').get_text(' ', strip=True)
                image_div = soup.find('div', id='spec_img_cont')
                if image_div:
                    image = self.domain.rstrip('/') + self.domain.rstrip('/') + image_div.find('img')['src']
                else:
                    image = ''
                
                details_div = soup.find('div', id='spec_info_container').find('div', recursive=False).find('div', recursive=False)
                description = details_div.find_all('div', recursive=False)[-5].find('p')
                if description:
                    description = description.get_text(' ', strip=True).replace('\xa0', ' ')
                else:
                    description = ''

                names = details_div.find('div', class_='spec_inf_b').get_text(' ', strip=True)

                show = {
                        "Название": title,
                        "Ссылка": links[1],
                        "Описание": description,
                        "Дата": date,
                        "Имена": names,
                        "Самый дорогой билет": max_price,
                        "Самый дешевый билет": min_price,
                        "Изображение": image,
                    }
                return show

        except Exception as e:
            print("Couldn't get details data:", e, response.status)
            return

class ScalaParser():
    def __init__(self):
        self.domain = 'https://www.teatroallascala.org/'
        self.name = "Teatro alla Scala"

        self.shows = asyncio.run(self.scrape())
    
    async def scrape(self):
        try:
            async with aiohttp.ClientSession() as session:
                shows = await self.get_performances(session)
                return shows
        except Exception as e:
            print("Couldn't create session:", e)
            return []

    async def get_performances(self, session):
        url = 'https://www.teatroallascala.org/en/season/2024-2025/index.html'
        try:
            async with session.get(url) as response:
                soup = bs(await response.text(), 'html.parser')
                ballet_div = soup.find('div', id='ballet')
                if not ballet_div:
                    print("Couldn't get ballet items list")
                    return []
                else:
                    ballet_items = ballet_div.find_all('article', recursive=False)
                    ballet_items_links = [self.domain.rstrip('/') + item.find('a', class_='btn')['href'] for item in ballet_items]
                
                tasks = []
                for link in ballet_items_links:
                    tasks.append(self.get_details(session, link))
                
                # Flatten all lists of shows into a single list
                results = await asyncio.gather(*tasks)
                shows = [show for sublist in results if sublist is not None and len(sublist) > 0 for show in sublist]
                return shows

        except Exception as e:
            print("Couldn't get performances 567:", e)
            return []

    async def get_tickets(self, session, title):
        start_date = datetime.now()
        end_date = (datetime.now() + timedelta(days=30))
        url = 'https://www.teatroallascala.org/web/cache/eventCalendarSalesPrices.aspx?seasonNavId=33&idLang=en-US'
        try:
            async with session.get(url) as response:
                data = (await response.json())['Table']
                tickets = []
                for item in data:
                    event_data = datetime.strptime(item['evtDateOffset'].split(' ')[0], '%d/%m/%Y')
                    if event_data > start_date and event_data < end_date and item['cntTitle'] == title:
                        tickets.append(item)
                return tickets
                
        except Exception as e:
            print("Couldn't get performances 585:", e)
            return []
        
    async def get_cast(self, session, id):
        url = f'https://www.teatroallascala.org/web/cache/getEventCastDate.aspx?evtId=-1&evmId={id}&idLang=en-US'
        try:
            async with session.get(url) as response:
                data = (await response.json())['Table']
                names = []
                for item in data:
                    if item['artName'] == 'THE TEATRO ALLA SCALA BALLET COMPANY':
                        continue
                    if f"{item['artName']} {item['artSurname']}" in names:
                        continue
                    names.append(f"{item['artName']} {item['artSurname']}")
                return ', '.join(names)
        except Exception as e:
            print(f"Couldn't get cast for id {id}:", e)
            return ''

    async def get_details(self, session, url):
        try:
            async with session.get(url) as response:
                soup = bs(await response.text(), 'html.parser')
                title = soup.find('h1').get_text(' ', strip=True)
                description_div = soup.find('div', id='in_brief')
                if not description_div:
                    description = ''
                else:
                    description = description_div.find('div', class_='cnt__body').get_text('', strip=True)
                
                performance_tickets_list = await self.get_tickets(session, title)

                shows = []
                for ticket in performance_tickets_list:
                    prices = []
                    price_soup = bs(ticket['evpTicketPrices'], 'lxml')
                    for zone_tag in price_soup.find_all('zone'):
                        price_tag = zone_tag.find('price')
                        prices.append(int(price_tag['price']))
                    
                    event_id = ticket['evmId']
                    max_price = max(prices)
                    min_price = min(prices)

                    date = datetime.strptime(ticket['evtDateOffset'].split(' ')[0], '%d/%m/%Y').strftime('%Y.%m.%d')

                    lead = soup.find('div', id='lead')
                    image = self.domain.rstrip('/') + lead.find('img')['src']

                    names = await self.get_cast(session, event_id)

                    show = {
                        "Название": title,
                        "Ссылка": url,
                        "Описание": description,
                        "Дата": date,
                        "Имена": names,
                        "Самый дорогой билет": max_price,
                        "Самый дешевый билет": min_price,
                        "Изображение": image,
                    }
                    
                    shows.append(show)

                return shows

        except Exception as e:
            print("Couldn't get performance details:", e)
            return None
