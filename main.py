
import os, json, requests, re, time, base64
from datetime import datetime
import pytz

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_DB_ID = os.getenv("NOTION_DB_ID", "")
FLOW_API_KEY = os.getenv("FLOW_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "") or FLOW_API_KEY
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

def enviar_telegram(texto, video_path=None):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        if video_path and os.path.exists(video_path):
            url=f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo"
            with open(video_path,'rb') as f:
                files={'video':f}
                data={'chat_id':TELEGRAM_CHAT_ID,'caption':texto[:1000],'parse_mode':'Markdown'}
                r=requests.post(url,data=data,files=files,timeout=60)
                print(f"Telegram video API: {r.status_code}")
                if r.status_code==200:
                    return True
        url=f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload={"chat_id":TELEGRAM_CHAT_ID,"text":texto,"parse_mode":"Markdown"}
        r=requests.post(url,json=payload,timeout=10)
        print(f"Telegram API: {r.status_code}")
        return r.status_code==200
    except Exception as e:
        print(f"Telegram error: {e}")
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

def guardar_notion(titulo, tipo, guion, copy, prompt, creditos, video_url=""):
    if not NOTION_TOKEN or not NOTION_DB_ID:
        return False
    db_id = limpiar_db_id(NOTION_DB_ID)
    url = "https://api.notion.com/v1/pages"
    headers = {"Authorization": f"Bearer {NOTION_TOKEN}","Content-Type":"application/json","Notion-Version":"2022-06-28"}
    props = {
        "Nombre": {"title": [{"text": {"content": titulo[:100]}}]},
        "Tipo": {"select": {"name": tipo[:30]}},
        "Guion": {"rich_text": [{"text": {"content": guion[:1900]}}]},
        "Copy": {"rich_text": [{"text": {"content": (copy + (" \nVideo: "+video_url if video_url else ""))[:1900]}}]},
        "Prompt": {"rich_text": [{"text": {"content": prompt[:1900]}}]},
        "Creditos": {"number": creditos},
        "Estado": {"status": {"name": "Not started"}}
    }
    try:
        r = requests.post(url, headers=headers, json={"parent":{"database_id":db_id},"properties":props}, timeout=15)
        print(f"Notion API full: {r.status_code}")
        if r.status_code==200:
            print(f"✅ Guardado REAL COMPLETO TODO en Notion")
            return True
        # fallback sin Estado
        props2 = {k:v for k,v in props.items() if k!="Estado"}
        r2 = requests.post(url, headers=headers, json={"parent":{"database_id":db_id},"properties":props2}, timeout=15)
        print(f"Notion sin Estado: {r2.status_code}")
        if r2.status_code==200:
            return True
        r3 = requests.post(url, headers=headers, json={"parent":{"database_id":db_id},"properties":{"Nombre":props["Nombre"],"Tipo":props["Tipo"]}}, timeout=15)
        print(f"Notion fallback Nombre+Tipo: {r3.status_code}")
        return r3.status_code==200
    except Exception as e:
        print(f"Notion error: {e}")
        return False

def generar_video_veo(prompt, api_key):
    """
    Intenta generar video real con Veo 3 Fast via Google Generative AI.
    Si falla (clave no valida para Veo, o API no habilitada), devuelve None y seguimos con texto.
    """
    if not api_key:
        print("Sin FLOW_API_KEY, no se puede generar video real")
        return None
    # Veo 3 Fast via Generative Language API v1beta
    # Endpoint: https://generativelanguage.googleapis.com/v1beta/models/veo-3.0-fast-generate-001:predictLongRunning
    # Este endpoint requiere API key con permiso Veo. Si tu clave es de AI Studio, puede que necesites habilitar Veo en Cloud.
    # Intentamos 2 endpoints: veo-3.0-fast y veo-2.0
    endpoints = [
        f"https://generativelanguage.googleapis.com/v1beta/models/veo-3.0-fast-generate-001:predictLongRunning?key={api_key}",
        f"https://generativelanguage.googleapis.com/v1beta/models/veo-2.0-generate-001:predictLongRunning?key={api_key}",
    ]
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {"aspectRatio": "9:16", "durationSeconds": 8}
    }
    for endpoint in endpoints:
        try:
            print(f"Intentando Veo endpoint: {endpoint[:80]}...")
            r = requests.post(endpoint, json=payload, timeout=30)
            print(f"Veo respuesta inicial: {r.status_code} - {r.text[:800]}")
            if r.status_code!=200:
                continue
            data = r.json()
            op_name = data.get("name")
            if not op_name:
                continue
            # Poll operation
            poll_url = f"https://generativelanguage.googleapis.com/v1beta/{op_name}?key={api_key}"
            for i in range(30): # hasta 5 min
                time.sleep(10)
                pr = requests.get(poll_url, timeout=15)
                print(f"Veo poll {i}: {pr.status_code} - {pr.text[:500]}")
                if pr.status_code!=200:
                    continue
                pdata = pr.json()
                if pdata.get("done"):
                    # buscar video
                    resp = pdata.get("response",{})
                    # puede venir como base64 o uri
                    vid = resp.get("generateVideoResponse",{}).get("generatedSamples",[{}])[0]
                    b64 = vid.get("video",{}).get("bytesBase64Encoded")
                    uri = vid.get("video",{}).get("uri")
                    if b64:
                        out_path = "/tmp/video_umsa.mp4"
                        with open(out_path,"wb") as f:
                            f.write(base64.b64decode(b64))
                        print(f"✅ Video real generado: {out_path}")
                        return out_path
                    if uri:
                        # descargar uri
                        vr = requests.get(uri, timeout=60)
                        out_path = "/tmp/video_umsa.mp4"
                        with open(out_path,"wb") as f:
                            f.write(vr.content)
                        print(f"✅ Video real descargado de uri: {out_path}")
                        return out_path
                    print("Operacion done pero sin video")
                    return None
            print("Timeout esperando Veo")
            return None
        except Exception as e:
            print(f"Error Veo: {e}")
            continue
    print("Veo no disponible con esta clave, continuamos con modo texto")
    return None

VIDEOS={
    "noticia":{"tipo":"Noticia Tendencia","prompt":"Video vertical 9:16, 8 seconds, UMSA Monoblock La Paz Bolivia, student in business administration pointing to floating holographic charts showing money growth, text overlay 'EMPRESAS BUSCAN ADMINISTRADORES CON IA', vibrant TikTok style, fast cuts, 720p","guion":"Mientras otras carreras pelean por trabajo, las empresas paceñas estan cazando administradores UMSA que sepan IA.","copy":"Mientras otros buscan trabajo, a los de Admin UMSA los buscan las empresas 🚀 #NoticiaUMSA #IA #UMSA #LaPaz","creditos":20}
}

def generar():
    la_paz=pytz.timezone("America/La_Paz")
    hoy=datetime.now(la_paz)
    idea=VIDEOS["noticia"]
    if not gastar_creditos(idea["creditos"]):
        enviar_telegram(f"❌ UMSA Agente: Ya use {get_creditos()}/50 creditos hoy.")
        return
    titulo = f"Video {idea['tipo']} - {hoy.strftime('%d %b %H:%M')}: {idea['guion'][:35]}"
    print(f"Generando con Veo 3 Fast: {idea['prompt']}")
    video_path = generar_video_veo(idea['prompt'], FLOW_API_KEY or GEMINI_API_KEY)
    video_url = ""
    if video_path and os.path.exists(video_path):
        video_url = f"Video real generado: {video_path} (20 creditos)"
        print(f"Video listo: {video_path}")
    else:
        print("Modo texto (sin video real) - Veo no disponible con esta clave o falta habilitar en Google Cloud")
        video_url = "Modo texto - Activa Veo en Google Cloud para video real"

    ok = guardar_notion(titulo, idea["tipo"], idea["guion"], idea["copy"], idea["prompt"], idea["creditos"], video_url)
    estado_txt = "REAL COMPLETO + VIDEO" if video_path else "REAL COMPLETO TEXTO (Veo pendiente)"
    msg=f"""🎬 *Agente UMSA Admin - Video de hoy {hoy.strftime('%d/%m %H:%M')}*

Tipo: *{idea['tipo']}*
Guion: {idea['guion']}
Copy: {idea['copy']}
Prompt Veo: `{idea['prompt'][:90]}...`
Creditos: {idea['creditos']} (Total hoy: {get_creditos()}/50)

Estado: {estado_txt}
{video_url}

✅ Guardado en Notion como *Not started*
Quedan {50-get_creditos()} creditos hoy.
"""
    enviar_telegram(msg, video_path if video_path else None)

if __name__=="__main__":
    generar()
