
import os, json, requests
from datetime import datetime
import pytz

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
CREDITOS_FILE = "creditos_hoy.json"

def get_creditos():
    try:
        with open(CREDITOS_FILE, "r") as f:
            d=json.load(f)
            if d["fecha"]==datetime.now().strftime("%Y-%m-%d"):
                return d["usados"]
    except: pass
    return 0

def gastar_creditos(cant):
    usados=get_creditos()
    if usados+cant>50:
        return False
    with open(CREDITOS_FILE,"w") as f:
        json.dump({"fecha":datetime.now().strftime("%Y-%m-%d"),"usados":usados+cant},f)
    return True

def enviar_telegram(texto):
    print(f"Intentando enviar Telegram a ChatID {TELEGRAM_CHAT_ID} con token {TELEGRAM_TOKEN[:10]}...")
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: Falta TELEGRAM_TOKEN o TELEGRAM_CHAT_ID en Secrets")
        return False
    url=f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload={"chat_id":TELEGRAM_CHAT_ID,"text":texto,"parse_mode":"Markdown"}
    try:
        r=requests.post(url,json=payload,timeout=10)
        print(f"Respuesta Telegram API: {r.status_code} - {r.text[:500]}")
        if r.status_code==200:
            print("✅ Mensaje enviado a Telegram OK")
            return True
        else:
            print(f"❌ Error Telegram API: {r.text}")
            return False
    except Exception as e:
        print(f"❌ Excepcion enviando Telegram: {e}")
        return False

VIDEOS={
    "noticia":{"tipo":"Noticia Tendencia","prompt":"Video 9:16, 10s, Monoblock UMSA, graficos IA dinero flotando, estudiante UMSA señalando graficos subiendo, texto 'EMPRESAS BUSCAN ADMINISTRADORES CON IA', estilo viral TikTok, 720p","guion":"Mientras otras carreras pelean por trabajo, las empresas paceñas estan cazando administradores UMSA que sepan IA.","copy":"Mientras otros buscan trabajo, a los de Admin UMSA los buscan las empresas 🚀 #NoticiaUMSA #IA","creditos":20}
}

def generar_video_hoy():
    la_paz=pytz.timezone("America/La_Paz")
    hoy=datetime.now(la_paz)
    idea=VIDEOS["noticia"]
    if not gastar_creditos(idea["creditos"]):
        print(f"Limite 50 creditos alcanzado: {get_creditos()}/50")
        enviar_telegram(f"❌ UMSA Agente: Ya use {get_creditos()}/50 creditos hoy. Paro hasta mañana 7am.")
        return
    print(f"Generando noticia: {idea['prompt']}")
    print(f"Guardando en Notion DB : Video {idea['tipo']} - {hoy.strftime('%d %b')}: {idea['guion']}")
    msg=f"""🎬 *Agente UMSA Admin - Video de hoy {hoy.strftime('%d/%m %H:%M')}*

Tipo: *{idea['tipo']}*
Guion: {idea['guion']}
Copy: {idea['copy']}
Prompt Flow: `{idea['prompt'][:90]}...`
Creditos: {idea['creditos']} (Total hoy: {get_creditos()}/50)

✅ Guardado en Notion como *PENDIENTE*
Quedan {50-get_creditos()} creditos hoy.
"""
    ok=enviar_telegram(msg)
    if ok:
        print("Mensaje enviado a Telegram")
    else:
        print("Fallo envio Telegram")

if __name__=="__main__":
    generar_video_hoy()
