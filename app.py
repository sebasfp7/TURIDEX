import streamlit as st
import pandas as pd
from groq import Groq
import google.generativeai as genai
import anthropic
import openai
import json
import pdfplumber
from docx import Document
import re
from io import BytesIO

# ==================== CONFIGURACIÓN DE PÁGINA ====================
st.set_page_config(page_title="Finatrix Elite Pro", layout="wide", page_icon="🛡️")

# ==================== LECTURA DE ARCHIVOS ====================
def leer_archivo(file):
    """Lee archivos PDF, XLSX, DOCX y extrae texto"""
    try:
        ext = file.name.split('.')[-1].lower()
        
        if ext == 'pdf':
            with pdfplumber.open(file) as pdf:
                texto = "\n".join([p.extract_text() or "" for p in pdf.pages])
                return texto[:50000]  # Aumentado para Gemini
                
        elif ext == 'xlsx':
            df = pd.read_excel(file)
            return df.to_csv(index=False)[:50000]
            
        elif ext == 'docx':
            doc = Document(file)
            texto = "\n".join([p.text for p in doc.paragraphs])
            return texto[:50000]
            
        else:
            st.error(f"Formato {ext} no soportado")
            return ""
    except Exception as e:
        st.error(f"Error leyendo archivo: {str(e)}")
        return ""

# ==================== FUNCIONES DE IA ====================
def analizar_groq(texto, api_key):
    """Groq Llama 3.3 70B - Velocidad extrema"""
    try:
        client = Groq(api_key=api_key)
        prompt = f"""Eres un CFO Senior experto en auditoría financiera. Analiza estos datos:

{texto}

Responde SOLO en formato JSON válido con esta estructura exacta:
{{
  "score": 85,
  "resumen_ejecutivo": "texto aquí",
  "m": {{"eva": 123456, "wacc": 0.12}},
  "diagnostico_pilares": {{
    "rentabilidad": "análisis",
    "liquidez": "análisis",
    "solvencia": "análisis",
    "creacion_valor": "análisis"
  }},
  "semaforo": {{"verde": ["punto1"], "amarillo": ["punto2"], "rojo": ["punto3"]}},
  "plan_90_dias": ["accion1", "accion2", "accion3"]
}}"""
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        resultado = json.loads(response.choices[0].message.content)
        return resultado, "✅ Groq Llama 3.3 70B"
        
    except Exception as e:
        return None, f"❌ Groq falló: {str(e)}"

def analizar_gemini(texto, api_key):
    """Google Gemini 1.5 Flash - Contexto masivo"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""Actúa como CFO Senior. Analiza estos estados financieros:

{texto}

Devuelve SOLO un objeto JSON válido con:
- score (0-100)
- resumen_ejecutivo
- m: {{eva, wacc}}
- diagnostico_pilares: {{rentabilidad, liquidez, solvencia, creacion_valor}}
- semaforo: {{verde:[], amarillo:[], rojo:[]}}
- plan_90_dias: []

Sin markdown, sin explicaciones extra."""

        response = model.generate_content(prompt)
        texto_respuesta = response.text.strip()
        
        # Limpieza de markdown
        texto_respuesta = re.sub(r'```json\s*', '', texto_respuesta)
        texto_respuesta = re.sub(r'```\s*', '', texto_respuesta)
        
        # Buscar JSON
        match = re.search(r'\{.*\}', texto_respuesta, re.DOTALL)
        if match:
            resultado = json.loads(match.group(0))
            return resultado, "✅ Google Gemini 1.5 Flash"
        else:
            return None, "❌ Gemini no devolvió JSON válido"
            
    except Exception as e:
        return None, f"❌ Gemini falló: {str(e)}"

def analizar_claude(texto, api_key):
    """Anthropic Claude 3.5 Sonnet - Razonamiento profundo"""
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        prompt = f"""Analiza como CFO experto estos estados financieros:

{texto}

Responde ÚNICAMENTE con JSON válido:
{{
  "score": número,
  "resumen_ejecutivo": "texto",
  "m": {{"eva": número, "wacc": decimal}},
  "diagnostico_pilares": {{"rentabilidad": "texto", "liquidez": "texto", "solvencia": "texto", "creacion_valor": "texto"}},
  "semaforo": {{"verde": [], "amarillo": [], "rojo": []}},
  "plan_90_dias": []
}}"""

        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        
        texto_respuesta = message.content[0].text.strip()
        texto_respuesta = re.sub(r'```json\s*', '', texto_respuesta)
        texto_respuesta = re.sub(r'```\s*', '', texto_respuesta)
        
        match = re.search(r'\{.*\}', texto_respuesta, re.DOTALL)
        if match:
            resultado = json.loads(match.group(0))
            return resultado, "✅ Claude 3.5 Sonnet"
        else:
            return None, "❌ Claude no devolvió JSON válido"
            
    except Exception as e:
        return None, f"❌ Claude falló: {str(e)}"

def analizar_openai(texto, api_key):
    """OpenAI GPT-4o mini - Multimodal"""
    try:
        openai.api_key = api_key
        
        prompt = f"""Como CFO Senior, analiza:

{texto}

Devuelve JSON estricto:
{{
  "score": int,
  "resumen_ejecutivo": str,
  "m": {{"eva": float, "wacc": float}},
  "diagnostico_pilares": {{"rentabilidad": str, "liquidez": str, "solvencia": str, "creacion_valor": str}},
  "semaforo": {{"verde": list, "amarillo": list, "rojo": list}},
  "plan_90_dias": list
}}"""

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        resultado = json.loads(response.choices[0].message.content)
        return resultado, "✅ OpenAI GPT-4o mini"
        
    except Exception as e:
        return None, f"❌ OpenAI falló: {str(e)}"

# ==================== INTERFAZ PRINCIPAL ====================
st.title("🛡️ Finatrix Elite | Auditoría Inteligente con 4 IAs")

# ==================== SIDEBAR CON LLAVES ====================
with st.sidebar:
    st.header("🔑 Configuración de APIs")
    
    st.subheader("1️⃣ Groq (Prioridad)")
    api_groq = st.text_input(
        "Groq API Key", 
        value=st.secrets.get("GROQ_KEY", ""),
        type="password",
        help="Obtén tu key en: https://console.groq.com"
    )
    
    st.subheader("2️⃣ Google Gemini")
    api_gemini = st.text_input(
        "Gemini API Key",
        value=st.secrets.get("GEMINI_KEY", ""),
        type="password",
        help="Obtén tu key en: https://aistudio.google.com/app/apikey"
    )
    
    st.subheader("3️⃣ Anthropic Claude")
    api_claude = st.text_input(
        "Claude API Key",
        value=st.secrets.get("CLAUDE_KEY", ""),
        type="password",
        help="Obtén tu key en: https://console.anthropic.com"
    )
    
    st.subheader("4️⃣ OpenAI")
    api_openai = st.text_input(
        "OpenAI API Key",
        value=st.secrets.get("OPENAI_KEY", ""),
        type="password",
        help="Obtén tu key en: https://platform.openai.com/api-keys"
    )
    
    st.divider()
    st.info("💡 **Orden de prioridad:**\n1. Groq (más rápido)\n2. Gemini (más contexto)\n3. Claude (mejor razonamiento)\n4. OpenAI (multimodal)")

# ==================== SUBIDA DE ARCHIVO ====================
archivo = st.file_uploader(
    "📁 Subir Estados Financieros",
    type=["pdf", "xlsx", "docx"],
    help="Formatos soportados: Excel, Word, PDF"
)

# ==================== BOTÓN DE ANÁLISIS ====================
if archivo and st.button("🚀 Ejecutar Análisis Estratégico", type="primary"):
    
    with st.spinner("📖 Leyendo archivo..."):
        raw_text = leer_archivo(archivo)
    
    if not raw_text:
        st.error("No se pudo extraer texto del archivo")
        st.stop()
    
    st.success(f"✅ Archivo leído: {len(raw_text)} caracteres extraídos")
    
    # ==================== CASCADA DE IAs ====================
    data = None
    modelo_usado = ""
    
    # Intento 1: Groq
    if api_groq and not data:
        with st.spinner("🤖 Analizando con Groq Llama 3.3..."):
            data, modelo_usado = analizar_groq(raw_text, api_groq)
            st.info(modelo_usado)
    
    # Intento 2: Gemini
    if api_gemini and not data:
        with st.spinner("🧠 Analizando con Google Gemini..."):
            data, modelo_usado = analizar_gemini(raw_text, api_gemini)
            st.info(modelo_usado)
    
    # Intento 3: Claude
    if api_claude and not data:
        with st.spinner("🎯 Analizando con Claude 3.5..."):
            data, modelo_usado = analizar_claude(raw_text, api_claude)
            st.info(modelo_usado)
    
    # Intento 4: OpenAI
    if api_openai and not data:
        with st.spinner("⚡ Analizando con GPT-4o mini..."):
            data, modelo_usado = analizar_openai(raw_text, api_openai)
            st.info(modelo_usado)
    
    # ==================== VALIDACIÓN ====================
    if not data:
        st.error("❌ Ninguna IA pudo procesar el archivo. Verifica:")
        st.write("- Las API Keys estén correctas")
        st.write("- Tengas saldo/créditos disponibles")
        st.write("- El archivo contenga datos financieros válidos")
        st.stop()
    
    # ==================== RENDERIZADO VISUAL ====================
    st.success(f"✅ Análisis completado con: {modelo_usado}")
    
    # Métricas principales
    m = data.get('m', {})
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "🎯 Salud Financiera",
            f"{data.get('score', 0)}/100",
            delta=None
        )
    
    with col2:
        eva = m.get('eva', 0)
        st.metric(
            "💰 EVA",
            f"${eva:,.0f}",
            delta="Creando valor" if eva > 0 else "Destruyendo valor",
            delta_color="normal" if eva > 0 else "inverse"
        )
    
    with col3:
        wacc = m.get('wacc', 0)
        st.metric(
            "📊 WACC",
            f"{wacc:.2%}",
            delta=None
        )
    
    # Resumen ejecutivo
    st.subheader("📋 Resumen Ejecutivo")
    st.write(data.get('resumen_ejecutivo', 'No disponible'))
    
    # Diagnóstico por pilares
    st.subheader("🔍 Diagnóstico por Pilares")
    diag = data.get('diagnostico_pilares', {})
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**💵 Rentabilidad**")
        st.write(diag.get('rentabilidad', 'No disponible'))
        
        st.markdown("**💧 Liquidez**")
        st.write(diag.get('liquidez', 'No disponible'))
    
    with col2:
        st.markdown("**🏦 Solvencia**")
        st.write(diag.get('solvencia', 'No disponible'))
        
        st.markdown("**📈 Creación de Valor**")
        st.write(diag.get('creacion_valor', 'No disponible'))
    
    # Semáforo
    st.subheader("🚦 Semáforo de Riesgos")
    semaforo = data.get('semaforo', {})
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.success("**✅ Verde (Bien)**")
        for item in semaforo.get('verde', []):
            st.write(f"• {item}")
    
    with col2:
        st.warning("**⚠️ Amarillo (Alerta)**")
        for item in semaforo.get('amarillo', []):
            st.write(f"• {item}")
    
    with col3:
        st.error("**🔴 Rojo (Crítico)**")
        for item in semaforo.get('rojo', []):
            st.write(f"• {item}")
    
    # Plan 90 días
    st.subheader("📅 Plan de Acción 90 Días")
    plan = data.get('plan_90_dias', [])
    for i, accion in enumerate(plan, 1):
        st.write(f"{i}. {accion}")
    
    # Descargar JSON
    st.divider()
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    st.download_button(
        label="📥 Descargar Análisis Completo (JSON)",
        data=json_str,
        file_name="analisis_finatrix.json",
        mime="application/json"
    )

# ==================== FOOTER ====================
st.divider()
st.caption("🛡️ Finatrix Elite Pro | Powered by Groq + Gemini + Claude + OpenAI")
