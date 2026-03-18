import urllib.request
import urllib.parse
import json
import time

SERVER    = 'shelly-250-eu.shelly.cloud'
AUTH_KEY  = 'M2VlZTBhdWlk2D26BA2F71672AB690CC662F9B1625AA2BC73193C0068B6080F753BC90E1BB9985EF661104219B03'
DEVICE_ID = 'ece334ea1068'
SEUIL     = 4000
INTERVALLE = 120  # vérification toutes les 2 minutes

BOT_TOKEN = '8734430508:AAGQn0nRwwfAuOIbBOeCqGylFzar8_m3Zxw'
CHAT_ID   = '1474520275'

alerte_envoyee = False

def envoyer_telegram(message):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    data = urllib.parse.urlencode({'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'HTML'}).encode()
    req = urllib.request.Request(url, data=data)
    urllib.request.urlopen(req, timeout=10)

def get_surplus():
    url = f'https://{SERVER}/device/status'
    data = urllib.parse.urlencode({'auth_key': AUTH_KEY, 'id': DEVICE_ID}).encode()
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(req, timeout=10) as r:
        result = json.loads(r.read())
    if not result.get('isok'):
        raise Exception('API error')
    status = result['data']['device_status']
    grid = status['em1:0']['act_power']
    return max(0, round(-grid))

def main():
    global alerte_envoyee
    print('Surveillance surplus solaire démarrée...')
    envoyer_telegram('✅ Surveillance surplus solaire démarrée !')

    while True:
        try:
            surplus = get_surplus()
            appareils = surplus // 2000
            print(f'Surplus actuel : {surplus}W ({appareils} appareils)')

            if surplus >= SEUIL and not alerte_envoyee:
                msg = (
                    f'☀️ <b>Surplus solaire disponible !</b>\n\n'
                    f'⚡ Surplus : <b>{surplus} W</b>\n'
                    f'🔌 Vous pouvez allumer <b>{appareils} appareils</b>\n\n'
                    f'Profitez-en !'
                )
                envoyer_telegram(msg)
                alerte_envoyee = True
                print(f'Alerte envoyée : {surplus}W')

            elif surplus < SEUIL and alerte_envoyee:
                envoyer_telegram(f'🔴 Surplus redescendu sous {SEUIL}W ({surplus}W)')
                alerte_envoyee = False
                print('Alerte réinitialisée')

        except Exception as e:
            print(f'Erreur : {e}')

        time.sleep(INTERVALLE)

if __name__ == '__main__':
    main()
