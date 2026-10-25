
import os, json, requests, re
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
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    url=f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload={"chat_id":TELEGRAM_CHAT_ID,"text":texto,"parse_mode":"Markdown"}
    try:
        r=requests.post(url,json=payload,timeout=10)
        print(f"Telegram API: {r.status_code}")
        return r.status_code==200
    except Exception as e:
        print(f"Excepcion Telegram: {e}")
        return False

def limpiar_db_id(db_id):
    db_id = db_id.strip()
    if "notion.com" in db_id:
        m = re.search(r'([a-f0-9]{32})', db_id.replace('-','').lower())
        if m:
            db_id = m.group(1)
    if '-' not in db_id and len(db_id)==32:
        db_id = f"{db_id[0:8]}-{db_id[8:12]}-{db_id[12:16]}-{db_id[16:20]}-{db_id[20:]}"
    return db_id

def guardar_notion(titulo, tipo, guion, copy, prompt, creditos):
    if not NOTION_TOKEN or not NOTION_DB_ID:
        print("Falta NOTION_TOKEN o NOTION_DB_ID")
        return False
    db_id = limpiar_db_id(NOTION_DB_ID)
    url = "https://api.notion.com/v1/pages"
    headers = {"Authorization": f"Bearer {NOTION_TOKEN}","Content-Type":"application/json","Notion-Version":"2022-06-28"}
    
    # USAMOS NOMBRES EN ESPAÑOL EXACTO COMO LOS TIENES EN TU NOTION:
    # Nombre, Tipo, Guion, Copiar, Inmediato, Créditos, Estado
    data = {
        "parent": {"database_id": db_id},
        "properties": {
            "Nombre": {"title": [{"text": {"content": titulo[:100]}}]},
            "Tipo": {"select": {"name": tipo[:30]}},
            "Guion": {"rich_text": [{"text": {"content": guion[:1900]}}]},
            "Copiar": {"rich_text": [{"text": {"content": copy[:1900]}}]},
            "Inmediato": {"rich_text": [{"text": {"content": prompt[:1900]}}]},
            "Créditos": {"number": creditos},
            "Estado": {"status": {"name": "No ha comenzado"}}
        }
    }
    try:
        r = requests.post(url, headers=headers, json=data, timeout=15)
        print(f"Notion API ES: {r.status_code} - {r.text[:1200]}")
        if r.status_code==200:
            print(f"✅ Guardado REAL COMPLETO en Notion ES: {titulo}")
            return True
        # Si Estado falla como status, probar como select PENDIENTE
        if "Estado" in r.text:
            print("Probando Estado como select PENDIENTE...")
            data["properties"]["Estado"] = {"select": {"name": "PENDIENTE"}}
            r2 = requests.post(url, headers=headers, json=data, timeout=15)
            print(f"Notion retry Estado select: {r2.status_code} - {r2.text[:800]}")
            if r2.status_code==200:
                return True
        # Fallback sin acento Creditos
        print("Probando fallback sin acento Creditos...")
        data2 = {
            "parent": {"database_id": db_id},
            "properties": {
                "Nombre": {"title": [{"text": {"content": titulo[:100]}}]},
                "Tipo": {"select": {"name": tipo[:30]}},
                "Guion": {"rich_text": [{"text": {"content": guion[:1900]}}]},
                "Copiar": {"rich_text": [{"text": {"content": copy[:1900]}}]},
                "Inmediato": {"rich_text": [{"text": {"content": prompt[:1900]}}]},
                "Creditos": {"number": creditos}
            }
        }
        r3 = requests.post(url, headers=headers, json=data2, timeout=15)
        print(f"Notion fallback sin acento: {r3.status_code} - {r3.text[:800]}")
        if r3.status_code==200:
            return True
        # Ultimo fallback solo Nombre
        data3 = {"parent": {"database_id": db_id},"properties": {"Nombre": {"title": [{"text": {"content": titulo[:100]}}]}}}
        r4 = requests.post(url, headers=headers, json=data3, timeout=15)
        print(f"Notion fallback solo Nombre: {r4.status_code}")
        return r4.status_code==200
    except Exception as e:
        print(f"Excepcion Notion: {e}")
        return False

VIDEOS={
    "noticia":{"tipo":"Noticia Tendencia","prompt":"Video 9:16, 10s, Monoblock UMSA, graficos IA dinero flotando, estudiante UMSA señalando graficos subiendo, texto 'EMPRESAS BUSCAN ADMINISTRADORES CON IA', estilo viral TikTok, 720p","guion":"Mientras otras carreras pelean por trabajo, las empresas paceñas estan cazando administradores UMSA que sepan IA.","copy":"Mientras otros buscan trabajo, a los de Admin UMSA los buscan las empresas 🚀 #NoticiaUMSA #IA","creditos":20}
}

def generar():
    la_paz=pytz.timezone("America/La_Paz")
    hoy=datetime.now(la_paz)
    idea=VIDEOS["noticia"]
    if not gastar_creditos(idea["creditos"]):
        enviar_telegram(f"❌ UMSA Agente: Ya use {get_creditos()}/50 creditos hoy.")
        return
    titulo = f"Video {idea['tipo']} - {hoy.strftime('%d %b')}: {idea['guion'][:40]}"
    ok = guardar_notion(titulo, idea["tipo"], idea["guion"], idea["copy"], idea["prompt"], idea["creditos"])
    estado_txt = "REAL COMPLETO ES ✅" if ok else "FALLO"
    msg=f"""🎬 *Agente UMSA Admin - Video de hoy {hoy.strftime('%d/%m %H:%M')}*

Tipo: *{idea['tipo']}*
Guion: {idea['guion']}
Copy: {idea['copy']}
Creditos: {idea['creditos']} (Total: {get_creditos()}/50)

✅ Guardado en Notion {estado_txt} como *No ha comenzado*
Quedan {50-get_creditos()} creditos hoy.
"""
    enviar_telegram(msg)

if __name__=="__main__":
    generar()
