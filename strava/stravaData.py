from datetime import datetime
import requests
from bs4 import BeautifulSoup as bs
import json

STRAVA_DOMAIN = "https://www.strava.com"
GET_MEMBERS_URL = "https://www.strava.com/clubs/519477/members"
SEGMENT_IDS = [7858298]
DATA = {"7858298": {"name": "", "list": {}}}


def getFastTime(session, effortId):
    header = {
        'x-requested-with': 'XMLHttpRequest'
    }
    effortRes = session.get(STRAVA_DOMAIN + "/segment_efforts/" + effortId, headers=header)
    jsonData = json.loads(effortRes.text)
    return jsonData['overall_time']


def getActivityPage(session, links, member_info):
    fastestTime = ""
    for link in links:
        activityPage = session.get(STRAVA_DOMAIN + link)
        startNum = activityPage.text.index("segmentEfforts().reset(")
        endNum = activityPage.text.index(",\"hidden_efforts", startNum)
        data = activityPage.text[startNum + 23:endNum] + "}"
        jsonData = json.loads(data)["efforts"]

        for d in jsonData:
            if d["segment_id"] in SEGMENT_IDS:  # 하오고개일때
                DATA[str(d["segment_id"])]["name"] = d["name"]
                effortId = d["id"]
                fastestTime = getFastTime(session, effortId)
                member_info['fastTime'] = fastestTime
                member_info['fastSec'] = int(fastestTime.split(':')[0]*60)+int(fastestTime.split(':')[1])
                if fastestTime != '':
                    m_key = member_info["link"].replace("/athletes/", "")
                    DATA[str(d["segment_id"])]["list"][m_key] = member_info
                    break
        if fastestTime != '':
            break


def getMebmerPage(session, member_info):
    memberPage = session.get(STRAVA_DOMAIN + member_info['link'])
    soup = bs(memberPage.text, 'html.parser')
    activity_single = soup.find_all(class_='activity')
    activity_group = soup.find_all(class_='group-activity')

    activitys = []
    for activity in activity_single:
        if (activity.find(class_='entry-body').find(class_='icon-ride') != None) & (
                activity.find(class_='activity-map') != None):
            activityId = activity.attrs['id'].split("-")[1]
            activitys.append("/activities/" + activityId)

    for activity in activity_group:
        activitys.append(activity.find('ul').find('li').find(class_='entry-body').find('a').attrs['href'])

    getActivityPage(session, activitys, member_info)


def getMembers(session):
    members = session.get(GET_MEMBERS_URL)
    soup = bs(members.text, 'html.parser')
    members = soup.select('.list-athletes li')

    for member in members:
        member_info = {}
        member_info['name'] = member.find(class_='text-headline').find('a').text
        member_info['profile_img'] = member.find(class_='avatar-img').attrs['src']
        member_info['link'] = member.find(class_='text-headline').find('a').attrs['href']
        getMebmerPage(session, member_info)


def compareRecord(param, param1):
    p = param.split(':')
    p1 = param1.split(':')

    if int(p[0]) > int(p1[0]):  ## 새 기록에서 더 빠른 분을 기록
        return True
    elif int(p[0]) == int(p1[0]):  ## 분은 동일
        if int(p[1]) > int(p1[1]):  ## 새 기록에서 더 빠른 초를 기록
            return True
    return False


def generateJSONfile():
    for keys in DATA.keys():
        with open('./jsonData/'+keys + '.json') as json_file:
            jsf = json.load(json_file)
            new_record = DATA[keys]['list']

            for recordKey in jsf[keys]['list'].keys():
                if recordKey in new_record:
                    if compareRecord(jsf[keys]['list'][recordKey]['fastTime'], new_record[recordKey]['fastTime']):
                        jsf[keys]['list'][recordKey]['fastTime'] = new_record[recordKey]['fastTime']

            # 신규 유저 데이터 처리
            for newKey in new_record.keys():
                if newKey in jsf[keys]['list']:
                    continue
                else:
                    jsf[keys]['list'][newKey] = new_record[newKey]
            
            #정렬 
            sortValues = sorted(jsf[keys]['list'].values(), key=lambda e: (e['fastSec']))
            sortedData = {}
            for value in sortValues:
                sortedData[value['link'].replace("/athletes/","")] = value

            jsf[keys]['list'] = sortedData
            jsf[keys]['fetch_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open('./jsonData/'+keys + '.json', 'w') as outfile:
                json.dump(jsf, outfile)


def login():
    LOGIN_INFO = {
        'email': '',
        'password': ''
    }

    session = requests.Session()
    first_page = session.get(STRAVA_DOMAIN + '/login')
    html = first_page.text
    soup = bs(html, 'html.parser')
    utf8 = soup.find('input', {'name': 'utf8'})
    auth_token = soup.find('input', {'name': 'authenticity_token'})

    LOGIN_INFO = {**LOGIN_INFO, **{'utf8': utf8['value'], 'authenticity_token': auth_token['value']}}

    session.post(STRAVA_DOMAIN + '/session', data=LOGIN_INFO)
    getMembers(session)
    generateJSONfile()

login()

