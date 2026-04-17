import streamlit as st
import pandas as pd
from groq import Groq
import google.generativeai as genai
import json
import pdfplumber
from docx import Document
import re
import requests
from io import BytesIO

# ==================== CONFIGURACIÓN ====================
st.set_page_config(page_title="Finatrix Elite Pro", layout="wide", page_icon="🛡️")

# ==================== FUNCIONES DE LECTURA ====================
@st.cache_data(show_spinner=False)
def leer_archivo(file):
    """Lee archivos PDF, XLSX, DOCX"""
    try:
        ext = file.name.split('.')[-1].lower()
        
        if ext == 'pdf':
            with pdfplumber.open(BytesIO(file.read())) as pdf:
                texto = "\n".join([p.extract_text() or "" for p in pdf.pages[:20]])  # Solo 20 páginas
                return texto[:30000]
                
        elif ext == 'xlsx':
            df = pd.read_excel(BytesIO(file.read()))
            return df.head(100).to_csv(index=False)[:30000]
            
        elif ext == 'docx':
            doc = Document(BytesIO(file.read()))
            texto = "\n".join([p.text for p in doc.paragraphs[:200]])  # Solo 200 párrafos
            return texto[:30000]
            
        return ""
    except Exception as e:
        st.error(f"Error leyendo archivo: {str(e)}")
        return ""

# ==================== FUNCIONES DE IA ====================
def analizar_groq(texto, api_key):
    """Groq Llama 3.3 70B"""
    try:
        client = Groq(api_key=api_key)
        prompt = f"""Eres CFO experto. Analiza:

{texto[:10000]}

SOLO devuelve JSON:
{{"score":85,"resumen_ejecutivo":"texto","m":{{"eva":12345,"wacc":0.12}},"diagnostico_pilares":{{"rentabilidad":"ok","liquidez":"ok","solvencia":"ok","creacion_valor":"ok"}},"semaforo":{{"verde":["a"],"amarillo":["b"],"rojo":["c"]}},"plan_90_dias":["1","2","3"]}}"""
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=2000
        )
        
        return json.loads(response.choices[0].message.content), "✅ Groq"
    except Exception as e:
        return None, f"❌ Groq: {str(e)[:100]}"

def analizar_gemini(texto, api_key):
    """Google Gemini 1.5 Flash"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""CFO Senior analiza:

{texto[:20000]}

JSON puro:
{{"score":90,"resumen_ejecutivo":"texto","m":{{"eva":0,"wacc":0.1}},"diagnostico_pilares":{{"rentabilidad":"","liquidez":"","solvencia":"","creacion_valor":""}},"semaforo":{{"verde":[],"amarillo":[],"rojo":[]}},"plan_90_dias":[]}}"""

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                max_output_tokens=2000
            )
        )
        
        texto_limpio = response.text.strip()
        texto_limpio = re.sub(r'```json\s*|\s*```', '', texto_limpio)
        
        match = re.search(r'\{.*\}', texto_limpio, re.DOTALL)
        if match:
            return json.loads(match.group(0)), "✅ Gemini"
        return None, "❌ Gemini: Sin JSON"
            
    except Exception as e:
        return None, f"❌ Gemini: {str(e)[:100]}"

def analizar_llama_meta(texto):
    """Meta Llama 3.1 405B via Hugging Face"""
    try:
        API_URL = "https://api-inference.huggingface.co/models/meta-llama/Llama-3.1-405B-Instruct"
        
        # Usa token de Streamlit Secrets o variable de entorno
        hf_token = st.secrets.get("HF_TOKEN", "")
        if not hf_token:
            return None, "❌ Llama Meta: Falta HF_TOKEN"
        
        headers = {"Authorization": f"Bearer {hf_token}"}
        
        prompt = f"""Analiza como CFO:

{texto[:8000]}

Devuelve SOLO JSON:
{{"score":75,"resumen_ejecutivo":"analisis","m":{{"eva":0,"wacc":0.1}},"diagnostico_pilares":{{"rentabilidad":"","liquidez":"","solvencia":"","creacion_valor":""}},"semaforo":{{"verde":[],"amarillo":[],"rojo":[]}},"plan_90_dias":[]}}"""

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 2000,
                "temperature": 0.3,
                "return_full_text": False
            }
        }
        
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            resultado = response.json()
            texto_respuesta = resultado[0]['generated_text'] if isinstance(resultado, list) else resultado.get('generated_text', '')
            
            texto_limpio = re.sub(r'```json\s*|\s*```', '', texto_respuesta)
            match = re.search(r'\{.*\}', texto_limpio, re.DOTALL)
            if match:
                return json.loads(match.group(0)), "✅ Llama Meta 405B"
        
        return None, f"❌ Llama Meta: {response.status_code}"
            
    except Exception as e:
        return None, f"❌ Llama Meta: {str(e)[:100]}"

def analizar_deepseek(texto):
    """DeepSeek V3 via API gratuita"""
    try:
        API_URL = "https://api.deepseek.com/v1/chat/completions"
        
        ds_key = st.secrets.get("DEEPSEEK_KEY", "")
        if not ds_key:
            return None, "❌ DeepSeek: Falta API Key"
        
        headers = {
            "Authorization": f"Bearer {ds_key}",
            "Content-Type": "application/json"
        }
        
        prompt = f"""Eres CFO. Analiza:

{texto[:12000]}

JSON estricto:
{{"score":80,"resumen_ejecutivo":"","m":{{"eva":0,"wacc":0.1}},"diagnostico_pilares":{{"rentabilidad":"","liquidez":"","solvencia":"","creacion_valor":""}},"semaforo":{{"verde":[],"amarillo":[],"rojo":[]}},"plan_90_dias":[]}}"""

        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 2000
        }
        
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            resultado = response.json()
            contenido = resultado['choices'][0]['message']['content']
            
            texto_limpio = re.sub(r'```json\s*|\s*```', '', contenido)
            match = re.search(r'\{.*\}', texto_limpio, re.DOTALL)
            if match:
                return json.loads(match.group(0)), "✅ DeepSeek V3"
        
        return None, f"❌ DeepSeek: {response.status_code}"
            
    except Exception as e:
        return None, f"❌ DeepSeek: {str(e)[:100]}"

def analizar_mistral(texto):
    """Mistral Large via API gratuita"""
    try:
        API_URL = "https://api.mistral.ai/v1/chat/completions"
        
        mistral_key = st.secrets.get("MISTRAL_KEY", "")
        if not mistral_key:
            return None, "❌ Mistral: Falta API Key"
        
        headers = {
            "Authorization": f"Bearer {mistral_key}",
            "Content-Type": "application/json"
        }
        
        prompt = f"""CFO experto analiza:

{texto[:15000]}

Solo JSON:
{{"score":88,"resumen_ejecutivo":"","m":{{"eva":0,"wacc":0.1}},"diagnostico_pilares":{{"rentabilidad":"","liquidez":"","solvencia":"","creacion_valor":""}},"semaforo":{{"verde":[],"amarillo":[],"rojo":[]}},"plan_90_dias":[]}}"""

        payload = {
            "model": "mistral-large-latest",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 2000
        }
        
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            resultado = response.json()
            contenido = resultado['choices'][0]['message']['content']
            
            texto_limpio = re.sub(r'```json\s*|\s*```', '', contenido)
            match = re.search(r'\{.*\}', texto_limpio, re.DOTALL)
            if match:
                return json.loads(match.group(0)), "✅ Mistral Large"
        
        return None, f"❌ Mistral: {response.status_code}"
            
    except Exception as e:
        return None, f"❌ Mistral: {str(e)[:100]}"

# ==================== INTERFAZ ====================
st.title("🛡️ Finatrix Elite | 5 IAs en Cascada")

with st.sidebar:
    st.header("🔑 API Keys")
    
    st.subheader("Groq (Prioridad)")
    api_groq = st.text_input("Groq Key", value=st.secrets.get("GROQ_KEY", ""), type="password")
    st.caption("https://console.groq.com")
    
    st.subheader("Gemini (Respaldo)")
    api_gemini = st.text_input("Gemini Key", value=st.secrets.get("GEMINI_KEY", ""), type="password")
    st.caption("https://aistudio.google.com/apikey")
    
    st.subheader("Opcionales")
    with st.expander("Agregar más IAs"):
        hf_token = st.text_input("Hugging Face Token", value=st.secrets.get("HF_TOKEN", ""), type="password")
        st.caption("https://huggingface.co/settings/tokens")
        
        deepseek_key = st.text_input("DeepSeek Key", value=st.secrets.get("DEEPSEEK_KEY", ""), type="password")
        st.caption("https://platform.deepseek.com")
        
        mistral_key = st.text_input("Mistral Key", value=st.secrets.get("MISTRAL_KEY", ""), type="password")
        st.caption("https://console.mistral.ai")
    
    # Guardar en secrets temporalmente
    if hf_token:
        st.secrets["HF_TOKEN"] = hf_token
    if deepseek_key:
        st.secrets["DEEPSEEK_KEY"] = deepseek_key
    if mistral_key:
        st.secrets["MISTRAL_KEY"] = mistral_key

archivo = st.file_uploader("📁 Subir Estados Financieros", type=["pdf", "xlsx", "docx"])

if archivo:
    if st.button("🚀 Analizar", type="primary"):
        
        # Leer archivo
        with st.spinner("📖 Leyendo..."):
            raw_text = leer_archivo(archivo)
        
        if not raw_text:
            st.error("Archivo vacío o corrupto")
            st.stop()
        
        st.success(f"✅ {len(raw_text)} caracteres extraídos")
        
        # Cascada de IAs
        data = None
        modelo = ""
        
        ias = [
            (api_groq, analizar_groq, "Groq"),
            (api_gemini, analizar_gemini, "Gemini"),
            (st.secrets.get("HF_TOKEN"), lambda t: analizar_llama_meta(t), "Llama Meta"),
            (st.secrets.get("DEEPSEEK_KEY"), lambda t: analizar_deepseek(t), "DeepSeek"),
            (st.secrets.get("MISTRAL_KEY"), lambda t: analizar_mistral(t), "Mistral")
        ]
        
        for api_key, funcion, nombre in ias:
            if api_key and not data:
                with st.spinner(f"🤖 Probando {nombre}..."):
                    if nombre in ["Groq", "Gemini"]:
                        data, modelo = funcion(raw_text, api_key)
                    else:
                        data, modelo = funcion(raw_text)
                    
                    st.info(modelo)
                    if data:
                        break
        
        if not data:
            st.error("❌ Ninguna IA funcionó. Verifica tus API Keys.")
            st.stop()
        
        # ==================== VISUALIZACIÓN ====================
        st.success(f"✅ Análisis por: {modelo}")
        
        m = data.get('m', {})
        c1, c2, c3 = st.columns(3)
        c1.metric("🎯 Score", f"{data.get('score', 0)}/100")
        c2.metric("💰 EVA", f"${m.get('eva', 0):,.0f}")
        c3.metric("📊 WACC", f"{m.get('wacc', 0):.2%}")
        
        st.subheader("📋 Resumen")
        st.write(data.get('resumen_ejecutivo', 'N/A'))
        
        st.subheader("🔍 Diagnóstico")
        diag = data.get('diagnostico_pilares', {})
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**💵 Rentabilidad**")
            st.write(diag.get('rentabilidad', 'N/A'))
            st.markdown("**💧 Liquidez**")
            st.write(diag.get('liquidez', 'N/A'))
        with col2:
            st.markdown("**🏦 Solvencia**")
            st.write(diag.get('solvencia', 'N/A'))
            st.markdown("**📈 Creación Valor**")
            st.write(diag.get('creacion_valor', 'N/A'))
        
        st.subheader("🚦 Semáforo")
        sem = data.get('semaforo', {})
        c1, c2, c3 = st.columns(3)
        with c1:
            st.success("✅ Verde")
            for i in sem.get('verde', []): st.write(f"• {i}")
        with c2:
            st.warning("⚠️ Amarillo")
            for i in sem.get('amarillo', []): st.write(f"• {i}")
        with c3:
            st.error("🔴 Rojo")
            for i in sem.get('rojo', []): st.write(f"• {i}")
        
        st.subheader("📅 Plan 90 Días")
        for i, a in enumerate(data.get('plan_90_dias', []), 1):
            st.write(f"{i}. {a}")
        
        st.download_button(
            "📥 Descargar JSON",
            json.dumps(data, indent=2, ensure_ascii=False),
            "analisis.json",
            "application/json"
        )

st.caption("🛡️ Finatrix Elite | Groq + Gemini + Llama + DeepSeek + Mistral")
