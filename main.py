
import os, json, requests
from datetime import datetime
import pytz

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_DB_ID = os.getenv("NOTION_DB_ID", "")
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
    print(f"Intentando enviar Telegram a ChatID {TELEGRAM_CHAT_ID}...")
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: Falta TELEGRAM_TOKEN o TELEGRAM_CHAT_ID")
        return False
    url=f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload={"chat_id":TELEGRAM_CHAT_ID,"text":texto,"parse_mode":"Markdown"}
    try:
        r=requests.post(url,json=payload,timeout=10)
        print(f"Respuesta Telegram API: {r.status_code} - {r.text[:600]}")
        return r.status_code==200
    except Exception as e:
        print(f"Excepcion Telegram: {e}")
        return False

def guardar_notion(titulo, tipo, guion, copy, prompt, creditos_usados):
    if not NOTION_TOKEN or not NOTION_DB_ID:
        print("NOTION_TOKEN o NOTION_DB_ID no configurados, guardando simulado")
        print(f"Guardando en Notion DB simulado: {titulo}")
        return False
    # limpiar ID (quitar URL si pegaron URL completa)
    db_id = NOTION_DB_ID.strip()
    if "notion.com" in db_id:
        # extraer ID del final
        import re
        m = re.search(r'([a-f0-9]{32})', db_id.replace('-',''))
        if m:
            db_id = m.group(1)
    # formatear ID con guiones para API
    if '-' not in db_id and len(db_id)==32:
        db_id = f"{db_id[0:8]}-{db_id[8:12]}-{db_id[12:16]}-{db_id[16:20]}-{db_id[20:]}"
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    data = {
        "parent": {"database_id": db_id},
        "properties": {
            "Nombre": {"title": [{"text": {"content": titulo[:100]}}]},
            "Tipo": {"select": {"name": tipo[:30]}} if True else {},
            "Guion": {"rich_text": [{"text": {"content": guion[:1900]}}]},
            "Copy": {"rich_text": [{"text": {"content": copy[:1900]}}]},
            "Prompt": {"rich_text": [{"text": {"content": prompt[:1900]}}]},
            "Creditos": {"number": creditos_usados},
            "Estado": {"select": {"name": "PENDIENTE"}}
        }
    }
    # intentar con propiedades comunes, si falla probar solo con Nombre
    try:
        r = requests.post(url, headers=headers, json=data, timeout=15)
        print(f"Respuesta Notion API: {r.status_code} - {r.text[:800]}")
        if r.status_code==200:
            print(f"✅ Guardado REAL en Notion: {titulo} - ID {r.json().get('id')}")
            return True
        else:
            # fallback: solo Nombre
            print("Probando fallback solo con Nombre...")
            data2 = {
                "parent": {"database_id": db_id},
                "properties": {"Nombre": {"title": [{"text": {"content": titulo[:100]}}]}}
            }
            r2 = requests.post(url, headers=headers, json=data2, timeout=15)
            print(f"Respuesta Notion fallback: {r2.status_code} - {r2.text[:800]}")
            return r2.status_code==200
    except Exception as e:
        print(f"Excepcion Notion: {e}")
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
    titulo = f"Video {idea['tipo']} - {hoy.strftime('%d %b')}: {idea['guion'][:40]}"
    print(f"Generando noticia: {idea['prompt']}")
    ok_notion = guardar_notion(titulo, idea['tipo'], idea['guion'], idea['copy'], idea['prompt'], idea['creditos'])
    estado_notion = "REAL ✅" if ok_notion else "SIMULADO (revisar token/DB)"
    print(f"Guardando en Notion DB {estado_notion}: {titulo}")
    msg=f"""🎬 *Agente UMSA Admin - Video de hoy {hoy.strftime('%d/%m %H:%M')}*

Tipo: *{idea['tipo']}*
Guion: {idea['guion']}
Copy: {idea['copy']}
Prompt Flow: `{idea['prompt'][:90]}...`
Creditos: {idea['creditos']} (Total hoy: {get_creditos()}/50)

✅ Guardado en Notion {estado_notion} como *PENDIENTE*
Quedan {50-get_creditos()} creditos hoy.
"""
    ok=enviar_telegram(msg)
    if ok:
        print("Mensaje enviado a Telegram")
    else:
        print("Fallo envio Telegram")

if __name__=="__main__":
    generar_video_hoy()
