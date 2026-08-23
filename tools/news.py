import requests, xml.etree.ElementTree as ET

def get_news(query='technology', limit=8):
    url='https://news.google.com/rss/search'
    xml=requests.get(url, params={'q':query,'hl':'en-US','gl':'US','ceid':'US:en'}, timeout=8).text
    root=ET.fromstring(xml); out=[]
    for item in root.findall('./channel/item')[:limit]:
        out.append({'title':item.findtext('title',''),'url':item.findtext('link',''),'published':item.findtext('pubDate',''),'source':item.findtext('source','')})
    return out
