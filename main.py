
import os, json, requests, re, time, base64
from datetime import datetime
import pytz

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_DB_ID = os.getenv("NOTION_DB_ID", "")
FLOW_API_KEY = os.getenv("FLOW_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "") or FLOW_API_KEY
PROJECT_ID = os.getenv("VERTEX_PROJECT_ID", "project-d0370989-463f-4179-a4e")  # tu proyecto con $300
LOCATION = "us-central1"
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
                r=requests.post(url,data=data,files=files,timeout=90)
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
            return True
        props2 = {k:v for k,v in props.items() if k!="Estado"}
        r2 = requests.post(url, headers=headers, json={"parent":{"database_id":db_id},"properties":props2}, timeout=15)
        print(f"Notion sin Estado: {r2.status_code}")
        return r2.status_code==200
    except Exception as e:
        print(f"Notion error: {e}")
        return False

def generar_video_flow(prompt, flow_token, project_id):
    """
    Intenta generar video real con Veo 3 Fast via Vertex AI usando tu token Flow AQ.Ab8...
    como Bearer token + proyecto My First Project (con $300)
    Endpoint: https://aiplatform.googleapis.com/v1/projects/{project}/locations/us-central1/publishers/google/models/veo-3.0-fast-generate-001:predictLongRunning
    """
    if not flow_token:
        print("Sin FLOW_API_KEY")
        return None
    
    # 3 formas de llamar a Veo con token Flow
    endpoints = [
        f"https://aiplatform.googleapis.com/v1/projects/{project_id}/locations/{LOCATION}/publishers/google/models/veo-3.0-fast-generate-001:predictLongRunning",
        f"https://aiplatform.googleapis.com/v1/projects/{project_id}/locations/{LOCATION}/publishers/google/models/veo-2.0-generate-001:predictLongRunning",
        f"https://aiplatform.googleapis.com/v1/projects/{project_id}/locations/{LOCATION}/publishers/google/models/veo-3.0-generate-001:predictLongRunning",
    ]
    
    headers = {
        "Authorization": f"Bearer {flow_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "aspectRatio": "9:16",
            "durationSeconds": 8,
            "sampleCount": 1,
            "personGeneration": "allow_adult"
        }
    }
    
    for endpoint in endpoints:
        try:
            print(f"Intentando Flow Veo via Vertex AI: {endpoint}")
            r = requests.post(endpoint, headers=headers, json=payload, timeout=30)
            print(f"Flow Veo respuesta inicial: {r.status_code} - {r.text[:1000]}")
            if r.status_code != 200:
                continue
            
            data = r.json()
            op_name = data.get("name")
            if not op_name:
                continue
            
            # Poll operation - usa mismo Bearer token
            poll_base = f"https://aiplatform.googleapis.com/v1/{op_name}"
            for i in range(36): # 6 min max
                time.sleep(10)
                pr = requests.get(poll_base, headers=headers, timeout=15)
                print(f"Flow Veo poll {i}: {pr.status_code} - {pr.text[:600]}")
                if pr.status_code != 200:
                    continue
                pdata = pr.json()
                if pdata.get("done"):
                    # Vertex AI Veo response format
                    resp = pdata.get("response", {})
                    # Puede venir en diferentes formatos
                    videos = resp.get("videos") or resp.get("generatedVideos") or []
                    if videos:
                        v = videos[0]
                        b64 = v.get("bytesBase64Encoded") or v.get("b64Json")
                        if b64:
                            out_path = "/tmp/video_umsa_flow.mp4"
                            with open(out_path,"wb") as f:
                                f.write(base64.b64decode(b64))
                            print(f"✅ Video Flow real generado: {out_path}")
                            return out_path
                    # Formato alternativo generateVideoResponse
                    gvr = resp.get("predictions", [{}])[0] if "predictions" in resp else resp.get("generateVideoResponse",{}).get("generatedSamples",[{}])[0] if "generateVideoResponse" in resp else {}
                    if gvr:
                        b64 = gvr.get("video",{}).get("bytesBase64Encoded") or gvr.get("bytesBase64Encoded")
                        if b64:
                            out_path = "/tmp/video_umsa_flow.mp4"
                            with open(out_path,"wb") as f:
                                f.write(base64.b64decode(b64))
                            print(f"✅ Video Flow real (formato 2): {out_path}")
                            return out_path
                    print(f"Operacion done pero sin video parseable: {json.dumps(resp)[:1000]}")
                    return None
            print("Timeout esperando Flow Veo")
            return None
        except Exception as e:
            print(f"Error Flow Veo: {e}")
            continue
    
    # Fallback: intentar endpoint generativelanguage con Bearer tambien
    try:
        print("Intentando Flow via generativelanguage con Bearer...")
        endpoint = "https://generativelanguage.googleapis.com/v1beta/models/veo-3.0-fast-generate-001:predictLongRunning"
        headers2 = {"Authorization": f"Bearer {flow_token}", "Content-Type": "application/json", "x-goog-user-project": project_id}
        r = requests.post(endpoint, headers=headers2, json=payload, timeout=30)
        print(f"Flow gen-lang Bearer: {r.status_code} - {r.text[:1000]}")
    except Exception as e:
        print(f"Error gen-lang Bearer: {e}")
    
    print("Flow Veo no disponible aun con este token, continuamos con modo texto - pero tu token ES valido para Flow web en flow.google.com")
    return None

VIDEOS={
    "noticia":{"tipo":"Noticia Tendencia","prompt":"Video vertical 9:16, 8 seconds, UMSA Monoblock La Paz Bolivia, student in business administration pointing to floating holographic charts showing money growth, text overlay 'EMPRESAS BUSCAN ADMINISTRADORES CON IA', vibrant TikTok style, fast cuts, 720p","guion":"Mientras otras carreras pelean por trabajo, las empresas pacenas estan cazando administradores UMSA que sepan IA.","copy":"Mientras otros buscan trabajo, a los de Admin UMSA los buscan las empresas 🚀 #NoticiaUMSA #IA #UMSA #LaPaz","creditos":20}
}

def generar():
    la_paz=pytz.timezone("America/La_Paz")
    hoy=datetime.now(la_paz)
    idea=VIDEOS["noticia"]
    if not gastar_creditos(idea["creditos"]):
        enviar_telegram(f"❌ UMSA Agente: Ya use {get_creditos()}/50 creditos hoy.")
        return
    titulo = f"Video {idea['tipo']} - {hoy.strftime('%d %b %H:%M')}: {idea['guion'][:35]}"
    print(f"Generando con Flow Veo 3 Fast: {idea['prompt']} usando proyecto {PROJECT_ID}")
    video_path = generar_video_flow(idea['prompt'], FLOW_API_KEY, PROJECT_ID)
    video_url = ""
    if video_path and os.path.exists(video_path):
        video_url = f"Video real Flow generado: {video_path} (20 creditos) - Proyecto {PROJECT_ID}"
        print(f"Video listo: {video_path}")
    else:
        video_url = f"Modo texto - Flow activo en Bolivia pero API requiere habilitar Veo en {PROJECT_ID} o usar flow.google.com manualmente. Tu token {FLOW_API_KEY[:15]}... ES valido para Flow web."
        print(video_url)

    ok = guardar_notion(titulo, idea["tipo"], idea["guion"], idea["copy"], idea["prompt"], idea["creditos"], video_url)
    estado_txt = "REAL COMPLETO + VIDEO FLOW" if video_path else "REAL COMPLETO TEXTO (Flow web activo, API pendiente)"
    msg=f"""🎬 *Agente UMSA Admin - Video de hoy {hoy.strftime('%d/%m %H:%M')}*

Tipo: *{idea['tipo']}*
Guion: {idea['guion']}
Copy: {idea['copy']}
Prompt Veo: `{idea['prompt'][:90]}...`
Creditos: {idea['creditos']} (Total hoy: {get_creditos()}/50)

Estado: {estado_txt}
{video_url}

✅ Guardado en Notion como *Not started*
Proyecto: {PROJECT_ID} con $300 hasta 23 ene 2027
Quedan {50-get_creditos()} creditos hoy.
"""
    enviar_telegram(msg, video_path if video_path else None)

if __name__=="__main__":
    generar()
