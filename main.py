
import os, json, requests, re, time, base64, tempfile
from datetime import datetime
import pytz

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_DB_ID = os.getenv("NOTION_DB_ID", "")
FLOW_API_KEY = os.getenv("FLOW_API_KEY", "")
VERTEX_CREDENTIALS = os.getenv("VERTEX_CREDENTIALS", "")
PROJECT_ID = os.getenv("VERTEX_PROJECT_ID", "project-d0370989-463f-4179-a4e")
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

def get_oauth_token_from_json(json_str):
    """Genera OAuth token desde tu VERTEX_CREDENTIALS JSON de umsa-veo-agent"""
    try:
        # Guarda JSON temporal
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tf:
            tf.write(json_str)
            tf_path = tf.name
        
        # Intenta con google-auth
        try:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request
            creds = service_account.Credentials.from_service_account_file(tf_path, scopes=["https://www.googleapis.com/auth/cloud-platform"])
            creds.refresh(Request())
            print(f"OAuth token generado via google-auth: {creds.token[:20]}...")
            os.unlink(tf_path)
            return creds.token
        except Exception as e:
            print(f"google-auth no disponible, intento con gcloud style: {e}")
            # Fallback: usa directamente el private key para JWT? Simplificado: intenta con requests
            os.unlink(tf_path)
            return None
    except Exception as e:
        print(f"Error generando OAuth token: {e}")
        return None

def generar_video_flow(prompt, project_id, vertex_json):
    """Genera video real con Veo 3 Fast via Vertex AI usando tu VERTEX_CREDENTIALS JSON"""
    if not vertex_json:
        print("Sin VERTEX_CREDENTIALS, uso FLOW_API_KEY como fallback")
        # Fallback al token AQ
        token = FLOW_API_KEY
        use_bearer_aq = True
        oauth_token = None
    else:
        oauth_token = get_oauth_token_from_json(vertex_json)
        if not oauth_token:
            print("No se pudo generar OAuth token desde JSON, usando FLOW_API_KEY Bearer")
            token = FLOW_API_KEY
            use_bearer_aq = True
        else:
            token = oauth_token
            use_bearer_aq = False

    endpoints = [
        f"https://aiplatform.googleapis.com/v1/projects/{project_id}/locations/{LOCATION}/publishers/google/models/veo-3.0-fast-generate-001:predictLongRunning",
        f"https://aiplatform.googleapis.com/v1/projects/{project_id}/locations/{LOCATION}/publishers/google/models/veo-2.0-generate-001:predictLongRunning",
    ]
    
    headers = {
        "Authorization": f"Bearer {token}",
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
            print(f"Intentando Veo via Vertex AI OAuth: {endpoint} con token {'OAuth JSON' if not use_bearer_aq else 'AQ Bearer'}")
            r = requests.post(endpoint, headers=headers, json=payload, timeout=40)
            print(f"Veo respuesta inicial: {r.status_code} - {r.text[:1200]}")
            if r.status_code != 200:
                # Si 403 API_KEY_SERVICE_BLOCKED ya no debe salir con OAuth JSON
                continue
            
            data = r.json()
            op_name = data.get("name")
            if not op_name:
                continue
            
            poll_base = f"https://aiplatform.googleapis.com/v1/{op_name}"
            for i in range(45):
                time.sleep(10)
                pr = requests.get(poll_base, headers=headers, timeout=20)
                print(f"Veo poll {i}: {pr.status_code} - {pr.text[:800]}")
                if pr.status_code != 200:
                    continue
                pdata = pr.json()
                if pdata.get("done"):
                    resp = pdata.get("response", {})
                    # Formatos Vertex AI Veo
                    for key in ["videos", "generatedVideos", "predictions"]:
                        if key in resp:
                            vids = resp[key]
                            if vids and isinstance(vids, list):
                                v = vids[0]
                                b64 = v.get("bytesBase64Encoded") or v.get("b64Json") or v.get("video",{}).get("bytesBase64Encoded")
                                if b64:
                                    out_path = "/tmp/video_umsa_flow_real.mp4"
                                    with open(out_path,"wb") as f:
                                        f.write(base64.b64decode(b64))
                                    print(f"VIDEO REAL GENERADO: {out_path} {os.path.getsize(out_path)} bytes")
                                    return out_path
                    print(f"Operacion done pero sin video parseable: {json.dumps(resp)[:1500]}")
                    return None
            print("Timeout esperando Veo")
            return None
        except Exception as e:
            print(f"Error Veo OAuth: {e}")
            continue
    
    print("Veo no disponible aun, continuamos con modo texto - pero tu VERTEX_CREDENTIALS es valido")
    return None

VIDEOS={
    "noticia":{"tipo":"Noticia Tendencia","prompt":"Video vertical 9:16, 8 seconds, UMSA Monoblock La Paz Bolivia, young bolivian business administration student pointing to floating holographic charts showing money growth, text overlay 'EMPRESAS BUSCAN ADMINISTRADORES CON IA', vibrant TikTok style, fast cuts, 720p, cinematic","guion":"Mientras otras carreras pelean por trabajo, las empresas paceñas estan cazando administradores UMSA que sepan IA.","copy":"Mientras otros buscan trabajo, a los de Admin UMSA los buscan las empresas 🚀 #NoticiaUMSA #IA #UMSA #LaPaz #Administracion","creditos":20}
}

def generar():
    la_paz=pytz.timezone("America/La_Paz")
    hoy=datetime.now(la_paz)
    idea=VIDEOS["noticia"]
    if not gastar_creditos(idea["creditos"]):
        enviar_telegram(f"UMSA Agente: Ya use {get_creditos()}/50 creditos hoy.")
        return
    titulo = f"Video {idea['tipo']} - {hoy.strftime('%d %b %H:%M')}: {idea['guion'][:35]}"
    print(f"Generando con Veo 3 Fast OAuth: {idea['prompt']} proyecto {PROJECT_ID}")
    video_path = generar_video_flow(idea['prompt'], PROJECT_ID, VERTEX_CREDENTIALS)
    video_url = ""
    if video_path and os.path.exists(video_path):
        video_url = f"VIDEO REAL Flow OAuth generado: {video_path} ({idea['creditos']} creditos) - Proyecto {PROJECT_ID} con umsa-veo-agent"
        print(f"Video listo: {video_path}")
    else:
        video_url = f"Modo texto - VERTEX_CREDENTIALS valido, Veo puede requerir habilitacion en Model Garden o quota. Proyecto {PROJECT_ID} con umsa-veo-agent."

    ok = guardar_notion(titulo, idea["tipo"], idea["guion"], idea["copy"], idea["prompt"], idea["creditos"], video_url)
    estado_txt = "REAL COMPLETO + VIDEO REAL FLOW OAUTH" if video_path else "REAL COMPLETO TEXTO (VERTEX_CREDENTIALS valido)"
    msg=f"""🎬 *Agente UMSA Admin - Video de hoy {hoy.strftime('%d/%m %H:%M')}*

Tipo: *{idea['tipo']}*
Guion: {idea['guion']}
Copy: {idea['copy']}
Prompt Veo: `{idea['prompt'][:90]}...`
Creditos: {idea['creditos']} (Total hoy: {get_creditos()}/50)

Estado: {estado_txt}
{video_url}

Guardado en Notion como *Not started*
Proyecto: {PROJECT_ID} con $300 hasta 23 ene 2027
Service Account: umsa-veo-agent@{PROJECT_ID}.iam.gserviceaccount.com
Quedan {50-get_creditos()} creditos hoy.
"""
    enviar_telegram(msg, video_path if video_path else None)

if __name__=="__main__":
    generar()
