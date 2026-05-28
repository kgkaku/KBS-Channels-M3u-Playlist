import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import time
import os

def get_korean_proxies():
    """Collecting Proxy from proxydb.net""
    url = 'http://proxydb.net/?country=KR'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f" Failed to fetch proxies: {e}")
        return []
    
    proxies = []
    
    for row in soup.select('table tr'):
        cols = row.find_all('td')
        if len(cols) >= 2:
            ip = cols[0].text.strip()
            port_raw = cols[1].text.strip()
            
            if port_raw.isdigit():
                port_str = str(port_raw)
                if len(port_str) >= 5:
                    port = port_str[2:]
                elif len(port_str) >= 4:
                    port = port_str[1:]
                else:
                    port = port_str
                
                proxy = f'http://{ip}:{port}'
                proxies.append(proxy)
    
    return proxies

def test_kbs_with_proxy(proxy):
    """Proxy Test for KBS API"""
    url = 'https://cfpwwwapi.kbs.co.kr/api/v1/landing/live/channel_code/11'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://onair.kbs.co.kr/',
    }
    
    try:
        r = requests.get(url, headers=headers, 
                        proxies={'http': proxy, 'https': proxy}, 
                        timeout=10)
        
        if r.status_code == 200:
            data = r.json()
            return data.get('ret') == 0 and data.get('channel_item')
        return False
    except:
        return False

def find_working_proxy(proxies):
    """Finding Working Proxy"""
    print("\n Testing proxies with KBS API...")
    
    for proxy in proxies:
        print(f"   Testing {proxy}...", end=' ')
        if test_kbs_with_proxy(proxy):
            print(" WORKING!")
            return proxy
        else:
            print(" Failed")
    
    return None

def load_channel_codes():
    """channel_code.txt ফাইল থেকে চ্যানেল লোড করা"""
    channels = {}
    
    if os.path.exists('channel_code.txt'):
        with open('channel_code.txt', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        name_part, code_part = line.split('=', 1)
                        name = name_part.strip()
                        code = code_part.strip()
                        channels[code] = name
                    else:
                        code = line
                        channels[code] = f"Channel_{code}"
    else:
        default_channels = {
            '11': 'KBS1',
            '12': 'KBS2',
            '14': 'KBS World',
            'N91': 'KBS Drama',
            'N92': 'KBS Joy',
            'N93': 'KBS Life',
            'N96': 'KBS Kids',
        }
        channels = default_channels
        save_channel_codes(channels)
    
    return channels

def save_channel_codes(channels):
    """Saving channel_code.txt"""
    with open('channel_code.txt', 'w', encoding='utf-8') as f:
        f.write("# KBS Channel Codes\n")
        f.write("# Format: CHANNEL_NAME = CODE\n\n")
        
        for code, name in channels.items():
            f.write(f"{name} = {code}\n")

def fetch_channel_data(proxy, channels):
    """Fetching All Channels"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://onair.kbs.co.kr/',
        'Accept': 'application/json',
    }
    
    proxies = {'http': proxy, 'https': proxy}
    channel_data = []
    active_count = 0
    
    print("\n Fetching channel data...")
    
    for code, name in channels.items():
        url = f'https://cfpwwwapi.kbs.co.kr/api/v1/landing/live/channel_code/{code}'
        
        try:
            r = requests.get(url, headers=headers, proxies=proxies, timeout=15)
            
            if r.status_code == 200:
                data = r.json()
                
                service_url = None
                for item in data.get('channel_item', []):
                    if item.get('media_type') == 'tv':
                        service_url = item.get('service_url')
                        break
                
                logo_url = data.get('channelMaster', {}).get('image_path_channel_logo', '')
                
                cookie_str = ""
                if service_url and '?' in service_url:
                    cookie_str = service_url.split('?')[1]
                
                if service_url:
                    channel_data.append({
                        'name': name,
                        'code': code,
                        'service_url': service_url.split('?')[0],
                        'logo': logo_url,
                        'cookie': cookie_str,
                        'user_agent': headers['User-Agent'],
                        'active': True
                    })
                    active_count += 1
                    print(f'    {name} ({code})')
                else:
                    print(f'    {name} ({code}) - No stream')
            else:
                print(f'    {name} ({code}) - HTTP {r.status_code}')
                
        except Exception as e:
            print(f'    {name} ({code}) - Error')
        
        time.sleep(0.3)
    
    return channel_data, active_count

def create_json_m3u(channel_data):
    """JSON M3U Format"""
    json_m3u = []
    for ch in channel_data:
        if ch['active']:
            json_m3u.append({
                "name": ch['name'],
                "link": ch['service_url'],
                "logo": ch['logo'],
                "cookie": ch['cookie'],
                "user_agent": ch['user_agent']
            })
    return json_m3u

def create_extvlcopt_m3u(channel_data, active_count):
    """EXTVLCOPT M3U Format"""
    now = datetime.now()
    
    m3u = '#EXTM3U\n'
    m3u += f'# Playlist created by @kgkaku\n'
    m3u += f'# Generated on: {now.strftime("%Y-%m-%d")} at {now.strftime("%H:%M:%S")}\n'
    m3u += f'# Total: {len(channel_data)} | Active: {active_count}\n\n'
    
    for ch in channel_data:
        if ch['active']:
            m3u += f'#EXTINF:-1 tvg-id="{ch["code"]}" tvg-name="{ch["name"]}" tvg-logo="{ch["logo"]}" group-title="KBS",{ch["name"]}\n'
            m3u += f'#EXTVLCOPT:http-user-agent={ch["user_agent"]}\n'
            m3u += f'#EXTHTTP:{{"cookie":"{ch["cookie"]}"}}\n'
            m3u += f'{ch["service_url"]}?{ch["cookie"]}\n\n'
    
    return m3u

def create_kbs_data_json(channel_data, proxy_used):
    """kbs-data.json Format"""
    return {
        'generated_at': datetime.now().isoformat(),
        'proxy_used': proxy_used,
        'total_channels': len(channel_data),
        'active_channels': sum(1 for ch in channel_data if ch['active']),
        'channels': channel_data
    }

def main():
    print("=" * 70)
    print(" KBS STREAM FETCHER - GitHub Actions")
    print("=" * 70)
    
    # লোড চ্যানেল কোড
    print("\n Loading channel codes...")
    channels = load_channel_codes()
    print(f"   Total: {len(channels)} channels")
    
    # প্রক্সি সংগ্রহ
    print("\n Fetching Korean proxies...")
    proxies = get_korean_proxies()
    print(f"   Found {len(proxies)} proxies")
    
    if not proxies:
        print(" No proxies found!")
        return
    
    # কাজ করা প্রক্সি খোঁজা
    working_proxy = find_working_proxy(proxies)
    
    if not working_proxy:
        print(" No working proxy found!")
        return
    
    print(f"\n Using proxy: {working_proxy}")
    
    # ডাটা সংগ্রহ
    channel_data, active_count = fetch_channel_data(working_proxy, channels)
    
    if not channel_data:
        print("❌ No channel data!")
        return
    
    # ফাইল তৈরি
    print("\n Creating output files...")
    
    json_m3u = create_json_m3u(channel_data)
    with open('kbs-nsplayer.m3u', 'w', encoding='utf-8') as f:
        json.dump(json_m3u, f, indent=2, ensure_ascii=False)
    
    extvlcopt_m3u = create_extvlcopt_m3u(channel_data, active_count)
    with open('kbs-extvlcopt.m3u', 'w', encoding='utf-8') as f:
        f.write(extvlcopt_m3u)
    
    kbs_data = create_kbs_data_json(channel_data, working_proxy)
    with open('kbs-data.json', 'w', encoding='utf-8') as f:
        json.dump(kbs_data, f, indent=2, ensure_ascii=False)
    
    # channel_code.txt আপডেট (নতুন চ্যানেল থাকলে)
    save_channel_codes(channels)
    
    print("\n" + "=" * 70)
    print(" SUCCESS!")
    print("=" * 70)
    print(f"\n Active channels: {active_count}/{len(channel_data)}")
    
    print("\n Active Channels:")
    for ch in channel_data:
        if ch['active']:
            print(f"   • {ch['name']} ({ch['code']})")

if __name__ == "__main__":
    main()
