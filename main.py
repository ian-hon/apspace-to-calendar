from hashlib import sha256
import os.path
import requests

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

CALENDAR_ID = '8dcec3c140098c8aff7afed11605727ae8b4eeef6522c88ae0c41a8f2ed1ebd7@group.calendar.google.com'
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# https://s3-ap-southeast-1.amazonaws.com/open-ws/weektimetable
# https://calendar.google.com/calendar/u/0?cid=OGRjZWMzYzE0MDA5OGM4YWZmN2FmZWQxMTYwNTcyN2FlOGI0ZWVlZjY1MjJjODhhZTBjNDFhOGYyZWQxZWJkN0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t

# region auth-related
creds = None

if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)

if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
    with open("token.json", "w") as token:
        token.write(creds.to_json())
# endregion

# apiit has bad security lol
response = requests.get('https://s3-ap-southeast-1.amazonaws.com/open-ws/weektimetable')

if response.status_code != 200:
    print('backend unreachable')

# sample output
{
    'INTAKE': 'UCDF2408ICT(SE)',
    'MODID': 'AICT015-4-1-DBM-L-1',
    'MODULE_NAME': 'Database Management',
    'DAY': 'MON',
    'LOCATION': 'APU CAMPUS',
    'ROOM': 'Auditorium 4 @ Level 3',
    'LECTID': 'YGM',
    'NAME': 'YOGESWARI A/P MUTHUSAMY',
    'SAMACCOUNTNAME': 'yogeswari.muthusamy',
    'DATESTAMP': '06-JAN-25',
    'DATESTAMP_ISO': '2025-01-06',
    'TIME_FROM': '08:30 AM',
    'TIME_TO': '10:30 AM',
    'TIME_FROM_ISO': '2025-01-06T08:30:00+08:00',
    'TIME_TO_ISO': '2025-01-06T10:30:00+08:00',
    'GROUPING': 'G1',
    'CLASS_CODE': 'APP___AICT015-4-1-DBM-L-1___2025-01-06',
    'COLOR': 'yellow'
}

# online : ROOM starts with 'ONLM'
available = [i for i in response.json() if (i['INTAKE'] == 'UCDF2408ICT(SE)') and (i['GROUPING'] == 'G1')] # sorry g2

try:
    service = build("calendar", "v3", credentials=creds)
    
    current = service.events().list(
        calendarId=CALENDAR_ID,
        singleEvents=True,
        orderBy="startTime",
    ).execute().get("items", [])
    
    for e in available:
        key = str(sha256(f"{e['CLASS_CODE']}___{e['TIME_FROM_ISO']}".encode('utf-8')).hexdigest())
        if len([i for i in current if i['description'] == key]) >= 1:
            print(f"\t{e['CLASS_CODE']} already exists")
            continue
        print(f'{e['MODULE_NAME']} at {e['TIME_FROM_ISO']} added')
        
        service.events().insert(
            calendarId=CALENDAR_ID,
            body={
                'summary': e['MODULE_NAME'] + ['', ' (Online)'][e['ROOM'][0:4] == 'ONLM'],
                'description': key,
                'location': e['ROOM'],
                'start': {
                    'dateTime': e['TIME_FROM_ISO'],
                    'timeZone': 'Asia/Kuching',
                },
                'end': {
                    'dateTime': e['TIME_TO_ISO'],
                    'timeZone': 'Asia/Kuching',
                }
            }
        ).execute()

except HttpError as error:
    print(f"http err: {error}")
