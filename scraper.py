from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
import requests
import json
import time

load_dotenv()

def camelCase(string):
    if not string:
        return ""
    
    split = string.split()
    res = [split[0].lower()]
    res.extend([word.capitalize() for word in split[1:]])
    
    return "".join(res)

def getEventResults(url):
    print("Getting Results...")
    resultArr = []
    html = requests.get(url)
    soup = BeautifulSoup(html.text.encode('utf-8'), 'html.parser')
    
    resultTable = soup.find('table', class_='resultsarchive-table')
    
    infos = [ele for ele in resultTable.thead.tr.stripped_strings]
    # resultArr.append(infos)
    
    for child in resultTable.tbody.children:
        if child != "\n":
            data = []
            for ch in child.children:
                joined = " ".join(ch.stripped_strings)
                if joined:
                    data.append(joined)
            
            while len(data) < len(infos):
                end = data.pop()
                data.append("")
                data.append(end)
                
            result = {}
            for ind, res in enumerate(data):
                result[infos[ind].lower()] = res
                
            resultArr.append(result)
    
    return resultArr
   
    
def getEventDetails(containerDiv, completed=False):
    title = containerDiv.find('p', class_='f1-timetable--title')
    time = containerDiv.parent['data-start-time'].split("T")
    gmtOff = containerDiv.parent['data-gmt-offset']
    event = {
        "title" : title.string,
        "date" : time[0],
        "time" : time[1],
        "gmtOff": gmtOff
    }
    
    if completed:
        resultLink = containerDiv.find('a')['href']
        result = getEventResults(resultLink)
        event['results'] = result
        
    return event


def getCircuit(url):
    print("Getting Circuit details...")
    html = requests.get(url)
    soup = BeautifulSoup(html.text.encode('utf-8'), 'html.parser')
    
    flag = soup.find('span', class_='f1-flag--wrapper')
    trackName = flag.next_sibling.next_sibling.string
    
    stats = soup.find_all('div', class_='f1-stat')
    
    circuit = {"trackName": trackName}
    for stat in stats:
        contents = [content for content in stat.stripped_strings]
        circuit[camelCase(contents[0])] = " ".join(contents[1:])
    
    return circuit
    
    
def isTrackMap(alt):
    return alt and 'carbon.png' in alt

def getRace(url, round_):
    html = requests.get(url)

    soup = BeautifulSoup(html.text.encode('utf-8'), 'html.parser')

    raceLocation = soup.find('h1', class_='race-location').contents[0]
    raceName = soup.find('h2', class_='f1--s').string
    trackMapImg = soup.find('img', alt=isTrackMap)['data-src']

    upcoming = soup.find_all('div', class_='upcoming')
    completed = soup.find_all('div', class_='completed')

    events = []
    for eventDiv in upcoming:
        events.append(getEventDetails(eventDiv))
        
    for eventDiv in completed:
        events.append(getEventDetails(eventDiv, completed=True))
    
    splitUrl = url.split(".")
    splitUrl.pop()
    circuit = getCircuit(".".join(splitUrl) + "/Circuit.html")
    
    
    return{
            "round": round_,
            "raceName" : raceName, 
            "raceLocation": raceLocation, 
            "events": events[::-1], 
            "trackMap": trackMapImg,
            "circuit": circuit
        }


def getStanding(url):
    html = requests.get(url)
    soup = BeautifulSoup(html.text.encode('utf-8'), 'html.parser')
    
    standingsTable = soup.find('table', class_='resultsarchive-table')
    
    infos = [info.lower() for info in standingsTable.thead.stripped_strings]
    
    standings = []
    for child in standingsTable.tbody.children:
        if child != "\n":
            data = []
            for ch in child.children:
                joined = " ".join(ch.stripped_strings)
                if joined:
                    data.append(joined)
                
            result = {}
            for ind, res in enumerate(data):
                result[infos[ind]] = res
                
            standings.append(result)
            
    return standings


def getStandings(year):
    driversUrl = f"https://www.formula1.com/en/results.html/{str(year)}/drivers.html"
    teamsUrl = f"https://www.formula1.com/en/results.html/{str(year)}/team.html"

    return {"drivers": getStanding(driversUrl), "teams": getStanding(teamsUrl)}


def motherShip(year):
    url = f"https://www.formula1.com/en/racing/{str(year)}.html"
    html = requests.get(url)
    soup = BeautifulSoup(html.text.encode('utf-8'), 'html.parser')
    
    raceUrls = soup.find_all('a', class_='event-item-wrapper event-item-link')
    rounds = len(raceUrls) - 1
    print(rounds)

    races = []
    
    start = time.time()
    for round_, raceUrl in enumerate(raceUrls[1:]):
        print(round_ + 1, "Scraping... ",raceUrl['href'])
        races.append(getRace("https://www.formula1.com" + raceUrl['href'], round_ + 1))
    
    jsonUrl = os.getenv("SCHEDULE_DB_API_URL")
    
    retries = 0
    status = 0
    theJson = json.dumps({"season": year, "rounds": rounds, "races": races}, indent=4, ensure_ascii=False).encode('utf-8')
    # print("The result",theJson.encode('utf-8'))
    while status != 200 and retries < 10:
        print("posting to db...")
        # file_path = r"seasonSchedule.json"
        # with open(file_path, "w") as outfile:
        #     outfile.write(theJson)
            
        try:
            res = requests.post(jsonUrl, theJson)
            status = res.status_code
        except:
            pass
        
        retries += 1
    
    print("Season Schedule", retries, status, res.text)
    
    print("Getting Standings...")
    jsonUrl = os.getenv("STANDINGS_DB_API_URL")
    
    res = requests.post(jsonUrl, json.dumps(getStandings(year), indent=4, ensure_ascii=False))
    
    print("Season Standings", res)
    
    end = time.time()
    
    print(f"Scrape ended in {round(end - start)} seconds.")
    
motherShip(2023)