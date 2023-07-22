# Used to update the schedule and results of a single grand prix

import requests
from bs4 import BeautifulSoup
from scraper import getRace, getStandings
import json
import os

def getSpecificRace(year: int):
    print('Loading Race Calendar...')
    url = f"https://www.formula1.com/en/racing/{str(year)}.html"
    html: requests.Response = requests.get(url)
    soup = BeautifulSoup(html.text.encode('utf-8'), 'html.parser')
    
    print(html.encoding)
    
    raceUrls = soup.find_all('a', class_='event-item-wrapper event-item-link')
    raceUrls = list(map(lambda x: x['href'], raceUrls))
    
    for ind, raceUrl in enumerate(raceUrls):
        splitt = raceUrl.split("/")
        print(ind, splitt[-1].split(".")[0], end=' | ')
    
    print()
    print("Pick a race and enter the number: ")
    raceInd = int(input())
    
    print("Getting", raceUrls[raceInd].split("/")[-1].split(".")[0])
    race = getRace("https://www.formula1.com" + raceUrls[raceInd], raceInd + 1)
    
    
    prevScheduleHtml = requests.get(os.getenv("SCHEDULE_DB_API_URL") or "") 
    seasonSchedule = json.loads(prevScheduleHtml.text.encode(prevScheduleHtml.encoding or 'utf-8'))
    
    seasonSchedule['races'][raceInd-1] = race
    
    jsonn = json.dumps(seasonSchedule, indent=4, ensure_ascii=False)
    
    encoded = jsonn.encode(prevScheduleHtml.encoding or 'utf-8')
    
    statusCode = 0
    retries = 0
    while retries < 5 and statusCode != 200:
        try:
            result: requests.Response = requests.post(os.getenv("SCHEDULE_DB_API_URL") or '', encoded)
            statusCode = result.status_code
            print(result.status_code, len(result.text) > 10)
            break
        except:
            retries += 1
            print("Error posting to db")
            print("Retrying...")
            
    
    print("Update Standings? (y/n)")
    updateStandings = input()
    
    if updateStandings.lower() == 'y':
        
        print("Getting Standings...")
        jsonUrl = os.getenv("STANDINGS_DB_API_URL") or ""
        standings = json.dumps(getStandings(year), indent=4, ensure_ascii=False).encode(html.encoding or 'utf-8')
        
        statusCode = 0
        retries = 0
        while retries < 5 and statusCode != 200:
            try:
                result: requests.Response = requests.post(jsonUrl, standings)
                statusCode = result.status_code
                print(result.status_code, len(result.text) > 10)
                break
            except:
                retries += 1
                print("Error posting to db")
                print("Retrying...")
    

if __name__ == "__main__":
    getSpecificRace(2023)