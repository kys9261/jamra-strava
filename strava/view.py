from django.shortcuts import render
import json

def index(request):
    with open('./jsonData/7858298.json') as jsonFile:
        return render(request, 'strava/index.html', {'segment': json.load(jsonFile)})
