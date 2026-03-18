import urllib.request
import urllib.parse
import json
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

SERVER    = 'shelly-250-eu.shelly.cloud'
AUTH_KEY  = 'M2VlZTBhdWlk2D26BA2F71672AB690CC662F9B1625AA2BC73193C0068B6080F753BC90E1BB9985EF661104219B03'
DEVICE_ID = 'ece334ea1068'

EMAIL_TO     = 'Hamid-13@live.fr'
EMAIL_FROM   = 'f26013251@gmail.com'
EMAIL_PASS   = 'jfxyeovvdtusjusm'
SMTP_SERVER  = 'smtp.gmail.com'
SMTP_PORT    = 587

TARIF_HP     = 0.1661
PUISSANCE_KWC = 9.5

def get_device_status():
    url  = f'https://{SERVER}/device/status'
    data = urllib.parse.urlencode({'auth_key': AUTH_KEY, 'id': DEVICE_ID}).encode()
    req  = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(req, timeout=10) as r:
        result = json.loads(r.read())
    if not result.get('isok'):
        raise Exception('API Shelly error')
    return result['data']['device_status']

def get_energie():
    status = get_device_status()
    return {
        'pv':      round(status['em1data:0']['total_act_energy'], 2),
        'injecte': round(status['em1data:1']['total_act_ret_energy'], 2),
        'soutire': round(status['em1data:1']['total_act_energy'], 2),
    }

def calculer_rapport(e_debut, e_fin):
    pv          = round(e_fin['pv'] - e_debut['pv'], 2)
    injecte     = round(e_fin['injecte'] - e_debut['injecte'], 2)
    soutire     = round(e_fin['soutire'] - e_debut['soutire'], 2)
    autoconso   = round(max(0, pv - injecte), 2)
    consommation= round(autoconso + soutire, 2)

    taux_autoconso = round((autoconso / pv * 100) if pv > 0 else 0, 1)
    taux_autoprod  = round((autoconso / consommation * 100) if consommation > 0 else 0, 1)

    economies_autoconso = round(autoconso * TARIF_HP, 2)
    economies_injection = round(injecte * 0.13, 2)
    economies_total     = round(economies_autoconso + economies_injection, 2)

    return {
        'pv': pv, 'autoconso': autoconso, 'injecte': injecte,
        'soutire': soutire, 'consommation': consommation,
        'taux_autoconso': taux_autoconso, 'taux_autoprod': taux_autoprod,
        'economies_autoconso': economies_autoconso,
        'economies_injection': economies_injection,
        'economies_total': economies_total,
    }

def formater_email(r, date_str):
    if r['pv'] > 0:
        ratio = r['pv'] / PUISSANCE_KWC
        if ratio > 4:    perf = '🌞 Excellente journée solaire'
        elif ratio > 2:  perf = '⛅ Bonne journée solaire'
        else:            perf = '☁️ Journée peu ensoleillée'
    else:
        perf = '🌙 Pas de production'

    def row(icon, label, val, color='#f0f2f7'):
        return f"""
        <tr>
          <td style="padding:10px 0;border-bottom:1px solid #1d2332;color:#888;font-size:15px;">{icon} {label}</td>
          <td align="right" style="padding:10px 0;border-bottom:1px solid #1d2332;font-weight:bold;color:{color};font-size:15px;">{val}</td>
        </tr>"""

    html = f"""
<html><body style="margin:0;padding:0;background:#f0f0f0;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f0f0;padding:30px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#0e1117;border-radius:16px;overflow:hidden;">
  <tr><td style="padding:30px 30px 10px;">
    <h1 style="color:#f0c040;font-size:26px;margin:0;">☀️ Rapport Solaire</h1>
    <p style="color:#888;margin:6px 0 24px;">{date_str} &nbsp;·&nbsp; {perf}</p>
    <table width="100%" cellpadding="0" cellspacing="0">
      {row('⚡', 'Production PV', f'{r["pv"]} kWh', '#f0c040')}
      {row('🏠', 'Consommation totale', f'{r["consommation"]} kWh')}
      {row('♻️', 'Autoconsommation', f'{r["autoconso"]} kWh', '#4ade80')}
      {row('↑', 'Injecté réseau', f'{r["injecte"]} kWh')}
      {row('↓', 'Soutiré réseau', f'{r["soutire"]} kWh')}
      {row('📊', 'Taux autoconsommation', f'{r["taux_autoconso"]}%', '#f0c040')}
      {row('📊', 'Taux autoproduction', f'{r["taux_autoprod"]}%', '#f0c040')}
    </table>
  </td></tr>
  <tr><td style="padding:20px 30px 30px;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#1d2332;border-radius:12px;">
      <tr><td style="padding:20px;">
        <p style="color:#888;font-size:13px;margin:0 0 8px;">💰 Économies du jour</p>
        <p style="color:#4ade80;font-size:36px;font-weight:bold;margin:0;">{r['economies_total']} €</p>
        <p style="color:#666;font-size:12px;margin:8px 0 0;">
          Autoconso : {r['economies_autoconso']} € &nbsp;·&nbsp; Injection : {r['economies_injection']} €
        </p>
        <p style="color:#444;font-size:11px;margin:4px 0 0;">
          Tarif HP 0,1661 €/kWh · Revente injection 0,13 €/kWh
        </p>
      </td></tr>
    </table>
  </td></tr>
</table>
</td></tr>
</table>
</body></html>"""
    return html

def envoyer_email(sujet, html):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = sujet
    msg['From']    = EMAIL_FROM
    msg['To']      = EMAIL_TO
    msg.attach(MIMEText(html, 'html'))
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
        s.starttls()
        s.login(EMAIL_FROM, EMAIL_PASS)
        s.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())

def attendre_20h():
    now   = datetime.utcnow() + timedelta(hours=1)
    cible = now.replace(hour=20, minute=0, second=0, microsecond=0)
    if now >= cible:
        cible += timedelta(days=1)
    attente = (cible - (datetime.utcnow() + timedelta(hours=1))).total_seconds()
    print(f'Prochain rapport à 20h00 — attente {int(attente//3600)}h{int((attente%3600)//60)}m')
    time.sleep(attente)

def main():
    print('Rapport solaire démarré')
    e_debut = get_energie()
    print(f'Energie de référence : {e_debut}')

    while True:
        attendre_20h()
        try:
            print('Récupération des données fin de journée...')
            e_fin = get_energie()
            r = calculer_rapport(e_debut, e_fin)
            date_str = (datetime.utcnow() + timedelta(hours=1)).strftime('%A %d %B %Y').capitalize()
            html  = formater_email(r, date_str)
            sujet = f'☀️ Solaire {(datetime.utcnow()+timedelta(hours=1)).strftime("%d/%m")} — {r["pv"]} kWh · {r["economies_total"]}€ économisés'
            envoyer_email(sujet, html)
            print(f'Rapport envoyé : {r}')
            e_debut = get_energie()
        except Exception as e:
            print(f'Erreur rapport : {e}')

if __name__ == '__main__':
    main()
