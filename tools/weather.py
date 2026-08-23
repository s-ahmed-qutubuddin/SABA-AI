import requests

def get_weather(city):
    geo = requests.get('https://geocoding-api.open-meteo.com/v1/search', params={'name': city, 'count':1, 'language':'en','format':'json'}, timeout=8).json()
    if not geo.get('results'): raise ValueError(f'Location not found: {city}')
    r=geo['results'][0]
    weather=requests.get('https://api.open-meteo.com/v1/forecast', params={'latitude':r['latitude'],'longitude':r['longitude'],'current':'temperature_2m,apparent_temperature,weather_code,wind_speed_10m','timezone':'auto'}, timeout=8).json()['current']
    return {'city':r['name'],'country':r.get('country'),'temperature_c':weather['temperature_2m'],'feels_like_c':weather['apparent_temperature'],'weather_code':weather['weather_code'],'wind_kmh':weather['wind_speed_10m']}
