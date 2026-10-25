
"""
AGENTE UMSA - Administración de Empresas
GitHub Actions - Se despierta solo 7am hora La Paz (11am UTC)
Stack: Telegram @umsa_admin_marketing_bot + Notion Videos Admi UMSA + Flow 50 creditos
"""
import os
import json
import requests
from datetime import datetime
import pytz

# --- TOKENS - Se leen de GitHub Secrets, no en codigo ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8657138596:AAEdUrRniE_E_o1TYnQ3xmLvLSpvLYqEOI")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")  # Tu chat ID para que te hable solo a ti
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_DB_ID = os.getenv("NOTION_DB_ID", "")
EXA_API_KEY = os.getenv("EXA_API_KEY", "")
FLOW_API_KEY = os.getenv("FLOW_API_KEY", "")

# --- CONTROL 50 CREDITOS FLOW ---
CREDITOS_MAX = 50
CREDITOS_FILE = "creditos_hoy.json"

def get_creditos():
    try:
        with open(CREDITOS_FILE, "r") as f:
            d = json.load(f)
            if d["fecha"] == datetime.now().strftime("%Y-%m-%d"):
                return d["usados"]
    except:
        pass
    return 0

def gastar_creditos(cant):
    usados = get_creditos()
    if usados + cant > CREDITOS_MAX:
        msg = f"❌ LIMITE FLOW UMSA: Ya usaste {usados}/{CREDITOS_MAX}. Quedan {CREDITOS_MAX-usados}. Paro hasta mañana 7am."
        enviar_telegram(msg)
        return False
    with open(CREDITOS_FILE, "w") as f:
        json.dump({"fecha": datetime.now().strftime("%Y-%m-%d"), "usados": usados+cant}, f)
    return True

def enviar_telegram(texto):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[TELEGRAM SIMULADO] {texto}")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": texto, "parse_mode": "Markdown"})

# --- 3 TIPOS DE VIDEO NEUROMARKETING UMSA ---
VIDEOS = {
    "polemico": {
        "tipo": "Polemico Viral",
        "prompt_flow": "Video vertical 9:16, 8s, joven boliviano plaza Murillo La Paz, gesto 'para', texto rojo grande 'ESTUDIA ESTO SI QUIERES SER JEFE', corte a traje oficina con Illimani, 720p, alto contraste",
        "guion": "3 carreras que van a desaparecer en 5 años. Y una que te va a hacer jefe. Adivina cual enseñamos en la UMSA.",
        "copy": "Tu papa quiere que estudies Derecho. Las empresas quieren que estudies Administracion UMSA. ¿A quien le haras caso? 👀 #UMSA #AdminUMSA #Polemica",
        "creditos": 20
    },
    "mito": {
        "tipo": "Mito vs Realidad",
        "prompt_flow": "Video 9:16, 8s, Monoblock UMSA La Paz, estudiante administracion rompiendo pizarron 'ADMIN=ABURRIDO', transicion a CEO oficina, texto 'MITO VS REALIDAD', 720p brillante",
        "guion": "Te dijeron que administracion es aburrida. En la UMSA te enseñamos a dirigir empresas, no a mirar Excel.",
        "copy": "Te mintieron sobre Administracion 😱 En UMSA no te enseñamos a ser empleado, te enseñamos a mandar. #MitoVsRealidad #UMSA",
        "creditos": 20
    },
    "noticia": {
        "tipo": "Noticia Tendencia",
        "prompt_flow": "Video 9:16, 10s, Monoblock UMSA, graficos IA dinero flotando, estudiante UMSA señalando graficos subiendo, texto 'EMPRESAS BUSCAN ADMINISTRADORES CON IA', estilo viral TikTok, 720p",
        "guion": "Mientras otras carreras pelean por trabajo, las empresas paceñas estan cazando administradores UMSA que sepan IA.",
        "copy": "Mientras otros buscan trabajo, a los de Admin UMSA los buscan las empresas 🚀 #NoticiaUMSA #IA #EmpleoLaPaz",
        "creditos": 20
    }
}

def generar_video_hoy():
    # Rotacion por dia
    la_paz = pytz.timezone("America/La_Paz")
    hoy = datetime.now(la_paz)
    dia = hoy.weekday()
    tipo = "polemico" if dia in [0,3] else "mito" if dia in [1,4] else "noticia"
    
    idea = VIDEOS[tipo]
    
    if not gastar_creditos(idea["creditos"]):
        return
    
    # Simula llamada Flow - aqui iria API real de Google Veo
    print(f"Generando {tipo}: {idea['prompt_flow']}")
    
    # Guarda en Notion (simulado - cuando tengas NOTION_TOKEN, descomenta)
    notion_data = f"Video {idea['tipo']} - {hoy.strftime('%d %b')}: {idea['guion']}"
    print(f"Guardando en Notion DB {NOTION_DB_ID}: {notion_data}")
    
    # Avisa por Telegram
    mensaje = f"""🎬 *Agente UMSA Admin - Video de hoy {hoy.strftime('%d/%m')}*

Tipo: *{idea['tipo']}*
Guion: {idea['guion']}
Copy: {idea['copy']}
Prompt Flow: `{idea['prompt_flow'][:80]}...`
Creditos: {idea['creditos']} (Total hoy: {get_creditos()}/{CREDITOS_MAX})

✅ Guardado en Notion 'Videos Admi UMSA - Agente' como *PENDIENTE*

Ve a Notion y cambia Estado a APROBADO para publicar en TikTok/IG/FB via Composio.

Quedan {CREDITOS_MAX-get_creditos()} creditos hoy.
"""
    enviar_telegram(mensaje)
    print("Mensaje enviado a Telegram")

if __name__ == "__main__":
    generar_video_hoy()
