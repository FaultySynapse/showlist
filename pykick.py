from aiohttp import ClientSession
from datetime import date, timedelta
from dataclasses import dataclass
from typing import List
from html.parser import HTMLParser
import re
import asyncio


DATE_FORMATE = "%m%%2F%d%%2F%Y"
BASE_URL = "https://www.songkick.com"
GEUSS_PATTERN = r"\/concerts\/\d+-([0-9a-z\-]+)-at-([0-9a-z\-]+)"
re_geuss = re.compile(GEUSS_PATTERN)

@dataclass
class Show:
    artist: str
    location: str 

class ParseEvent(HTMLParser):
    def __init__(self, *, convert_charrefs = True):
        super().__init__(convert_charrefs=convert_charrefs)
        self.in_artist = False
        self.in_venue = True
        self.artists = []
        self.location = None
    
    def handle_starttag(self, tag, attrs):
        for attr in attrs:
            if attr[0] == "data-analytics-label":
                self.in_artist = (attr[1] == "headliners")
                self.in_venue = (attr[1] == "venue_name")
    
    def handle_endtag(self, tag):
        self.in_artist = False
        self.in_venue = False
    
    def handle_data(self, data):
        if self.in_artist:
            self.artists.append(data)
        elif self.in_venue:
            self.location = data
    
    def get_shows(self) -> List[Show]:
        return [Show(artist=artist, location=self.location) for artist in self.artists]

class ParseListing(HTMLParser):
    def __init__(self, *, convert_charrefs = True):
        super().__init__(convert_charrefs=convert_charrefs)
        self.listings = []
    
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attrs = dict(attrs)
            link = attrs.get("href") 
            if attrs.get("class") == "event-link" and link is not None:
                self.listings.append(link)
    
    def get_events(self) -> List[str]:
        return self.listings

class SFShows:

    def __init__(self, start = None, days = None):
        if start is None:
            start = date.today() + timedelta(days=20)
        
        if days is None:
            days = 2
        
        self.start = start
        self.end = start + timedelta(days=2)
        self.s = ClientSession()
    
    async def get_list_page(self, page):
        r = await self.s.get(
            url=BASE_URL + "/metro-areas/26330-us-sf-bay-area",
            params={
                "filters[minDate]":self.start.strftime(DATE_FORMATE),
                "filters[maxDate]":self.end.strftime(DATE_FORMATE),
                "page":str(page),
            },
            timeout=1,
        )

        if r.status != 200:
            raise Exception(f"code {r.status}")

        parser = ParseListing() 
        parser.feed(await r.text())
        return parser.get_events()
    
    async def get_all_event(self, limit = 500):
        events = []
        page = 1
        next_page = await self.get_list_page(page)
        while len(next_page) and len(events) < limit:
            for link in next_page:
                yield link
            page += 1
            next_page = await self.get_list_page(page)
    
    async def get_details(self, link:str) -> List[Show]:
        r = await self.s.get(
            url=BASE_URL + link,
        )

        if r.status != 200:
            raise Exception(f"code {r.status}")
        
        parser = ParseEvent() 
        parser.feed(await r.text())
        return parser.get_shows()
    
    def geuss_details(self, link:str) -> Show:
        match = re_geuss.match(link)
        if match is None :
            return None
        
        return Show(
            match.group(1).replace("-"," "),
            match.group(2).replace("-"," "),
        )
    
    async def all_shows(self, limit = 500):
        async for link in self.get_all_event(limit=limit):
            yield asyncio.create_task(self.get_details(link=link))

        
async def make_play_list():
    spider = SFShows()
    shows = await asyncio.gather(*[show async for show in spider.all_shows()])
    print(shows)

asyncio.run(make_play_list())


