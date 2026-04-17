import streamlit as st
import pandas as pd
from groq import Groq
import google.generativeai as genai
import json
import pdfplumber
from docx import Document
import re
from io import BytesIO

# ==================== CONFIGURACIÓN ====================
st.set_page_config(
    page_title="Finatrix Elite Pro", 
    layout="wide",
    page_icon="🛡️",
    initial_sidebar_state="expanded"
)

# ==================== FUNCIONES DE LECTURA ====================
def leer_archivo(file):
    """Lee y extrae texto de archivos PDF, Excel o Word"""
    try:
        file_bytes = file.read()
        ext = file.name.split('.')[-1].lower()
        
        if ext == 'pdf':
            with pdfplumber.open(BytesIO(file_bytes)) as pdf:
                texto = ""
                for i, page in enumerate(pdf.pages):
                    if i >= 15:  # Máximo 15 páginas
                        break
                    texto += page.extract_text() or ""
                return texto[:25000]
        
        elif ext == 'xlsx':
            df = pd.read_excel(BytesIO(file_bytes))
            return df.head(80).to_csv(index=False)[:25000]
        
        elif ext == 'docx':
            doc = Document(BytesIO(file_bytes))
            texto = "\n".join([p.text for p in doc.paragraphs[:150]])
            return texto[:25000]
        
        return ""
    
    except Exception as e:
        st.error(f"❌ Error al leer archivo: {str(e)}")
        return ""

# ==================== FUNCIONES DE IA ====================
def analizar_con_groq(texto, api_key):
    """Análisis con Groq Llama 3.3 70B"""
    try:
        client = Groq(api_key=api_key)
        
        prompt = f"""Eres un CFO experto en auditoría financiera. Analiza estos datos:

{texto}

Devuelve ÚNICAMENTE un objeto JSON válido con esta estructura:
{{
  "score": 85,
  "resumen_ejecutivo": "Resumen breve del estado financiero",
  "m": {{"eva": 150000, "wacc": 0.12}},
  "diagnostico_pilares": {{
    "rentabilidad": "Análisis de rentabilidad",
    "liquidez": "Análisis de liquidez",
    "solvencia": "Análisis de solvencia",
    "creacion_valor": "Análisis de creación de valor"
  }},
  "semaforo": {{
    "verde": ["Punto fuerte 1", "Punto fuerte 2"],
    "amarillo": ["Área de atención 1"],
    "rojo": ["Riesgo crítico 1"]
  }},
  "plan_90_dias": ["Acción 1", "Acción 2", "Acción 3"]
}}

NO agregues texto adicional, SOLO el JSON."""

        respuesta = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=3000
        )
        
        resultado = json.loads(respuesta.choices[0].message.content)
        return resultado, "✅ Groq Llama 3.3 70B"
    
    except Exception as e:
        return None, f"❌ Error Groq: {str(e)[:150]}"

def analizar_con_gemini(texto, api_key):
    """Análisis con Google Gemini 1.5 Flash"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""Actúa como CFO Senior especializado en auditoría. Analiza:

{texto}

Devuelve SOLO un objeto JSON (sin markdown, sin explicaciones):
{{
  "score": 90,
  "resumen_ejecutivo": "texto",
  "m": {{"eva": 200000, "wacc": 0.10}},
  "diagnostico_pilares": {{
    "rentabilidad": "análisis",
    "liquidez": "análisis",
    "solvencia": "análisis",
    "creacion_valor": "análisis"
  }},
  "semaforo": {{
    "verde": ["item1"],
    "amarillo": ["item2"],
    "rojo": ["item3"]
  }},
  "plan_90_dias": ["accion1", "accion2", "accion3"]
}}"""

        respuesta = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=3000
            )
        )
        
        texto_respuesta = respuesta.text.strip()
        # Limpiar markdown
        texto_respuesta = re.sub(r'```json\s*', '', texto_respuesta)
        texto_respuesta = re.sub(r'```\s*', '', texto_respuesta)
        
        # Extraer JSON
        match = re.search(r'\{.*\}', texto_respuesta, re.DOTALL)
        if match:
            resultado = json.loads(match.group(0))
            return resultado, "✅ Google Gemini 1.5 Flash"
        else:
            return None, "❌ Gemini no devolvió JSON válido"
    
    except Exception as e:
        return None, f"❌ Error Gemini: {str(e)[:150]}"

# ==================== INTERFAZ PRINCIPAL ====================
st.title("🛡️ Finatrix Elite | Auditoría Financiera con IA")
st.markdown("**Análisis profesional de estados financieros en segundos**")

# ==================== SIDEBAR ====================
with st.sidebar:
    st.header("🔑 Configuración de APIs")
    
    st.markdown("### Groq (Recomendado)")
    api_groq = st.text_input(
        "Groq API Key",
        type="password",
        help="Obtén tu key en: https://console.groq.com",
        key="groq_input"
    )
    if api_groq:
        st.success("✅ Groq configurado")
    
    st.markdown("### Google Gemini (Respaldo)")
    api_gemini = st.text_input(
        "Gemini API Key",
        type="password",
        help="Obtén tu key en: https://aistudio.google.com/apikey",
        key="gemini_input"
    )
    if api_gemini:
        st.success("✅ Gemini configurado")
    
    st.divider()
    
    if not api_groq and not api_gemini:
        st.warning("⚠️ Configura al menos una API Key para continuar")
    
    st.info("""
    **Orden de prioridad:**
    1. Groq (más rápido)
    2. Gemini (mayor contexto)
    """)

# ==================== SUBIDA DE ARCHIVO ====================
st.subheader("📁 Sube tu documento financiero")

archivo = st.file_uploader(
    "Formatos soportados: Excel (.xlsx), Word (.docx), PDF",
    type=["pdf", "xlsx", "docx"],
    help="El archivo debe contener estados financieros, balances o informes de gestión"
)

# ==================== BOTÓN DE ANÁLISIS ====================
if archivo:
    st.success(f"✅ Archivo cargado: **{archivo.name}**")
    
    if st.button("🚀 Ejecutar Análisis Estratégico", type="primary", use_container_width=True):
        
        # Validar que hay al menos una API configurada
        if not api_groq and not api_gemini:
            st.error("⚠️ **Error:** Debes configurar al menos una API Key en el panel lateral")
            st.stop()
        
        # Paso 1: Leer archivo
        with st.spinner("📖 Extrayendo datos del archivo..."):
            texto_extraido = leer_archivo(archivo)
        
        if not texto_extraido:
            st.error("❌ No se pudo extraer texto del archivo. Verifica que contenga información válida.")
            st.stop()
        
        st.info(f"📊 Texto extraído: {len(texto_extraido)} caracteres")
        
        # Paso 2: Analizar con IAs (cascada)
        datos_analisis = None
        modelo_usado = ""
        
        # Intento 1: Groq
        if api_groq and not datos_analisis:
            with st.spinner("🤖 Analizando con Groq Llama 3.3..."):
                datos_analisis, modelo_usado = analizar_con_groq(texto_extraido, api_groq)
                st.info(modelo_usado)
        
        # Intento 2: Gemini (si Groq falla)
        if api_gemini and not datos_analisis:
            with st.spinner("🧠 Analizando con Google Gemini..."):
                datos_analisis, modelo_usado = analizar_con_gemini(texto_extraido, api_gemini)
                st.info(modelo_usado)
        
        # Validar resultado
        if not datos_analisis:
            st.error("""
            ❌ **No se pudo completar el análisis**
            
            Posibles causas:
            - Las API Keys son inválidas
            - Has excedido el límite de uso gratuito
            - El archivo no contiene datos financieros reconocibles
            
            Verifica tus credenciales y vuelve a intentar.
            """)
            st.stop()
        
        # ==================== VISUALIZACIÓN DE RESULTADOS ====================
        st.success(f"✅ **Análisis completado con:** {modelo_usado}")
        
        st.divider()
        
        # MÉTRICAS PRINCIPALES
        metricas = datos_analisis.get('m', {})
        col1, col2, col3 = st.columns(3)
        
        with col1:
            score = datos_analisis.get('score', 0)
            st.metric(
                label="🎯 Salud Financiera",
                value=f"{score}/100",
                delta="Excelente" if score >= 80 else "Mejorable"
            )
        
        with col2:
            eva = metricas.get('eva', 0)
            st.metric(
                label="💰 EVA (Valor Económico)",
                value=f"${eva:,.0f}",
                delta="Creando valor" if eva > 0 else "Destruyendo valor"
            )
        
        with col3:
            wacc = metricas.get('wacc', 0)
            st.metric(
                label="📊 WACC (Costo Capital)",
                value=f"{wacc:.2%}"
            )
        
        # RESUMEN EJECUTIVO
        st.subheader("📋 Resumen Ejecutivo")
        st.write(datos_analisis.get('resumen_ejecutivo', 'No disponible'))
        
        st.divider()
        
        # DIAGNÓSTICO POR PILARES
        st.subheader("🔍 Diagnóstico Detallado por Pilares")
        diagnostico = datos_analisis.get('diagnostico_pilares', {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 💵 Rentabilidad")
            st.write(diagnostico.get('rentabilidad', 'No disponible'))
            
            st.markdown("#### 💧 Liquidez")
            st.write(diagnostico.get('liquidez', 'No disponible'))
        
        with col2:
            st.markdown("#### 🏦 Solvencia")
            st.write(diagnostico.get('solvencia', 'No disponible'))
            
            st.markdown("#### 📈 Creación de Valor")
            st.write(diagnostico.get('creacion_valor', 'No disponible'))
        
        st.divider()
        
        # SEMÁFORO DE RIESGOS
        st.subheader("🚦 Semáforo de Riesgos")
        semaforo = datos_analisis.get('semaforo', {})
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.success("**✅ VERDE - Fortalezas**")
            for item in semaforo.get('verde', []):
                st.write(f"• {item}")
        
        with col2:
            st.warning("**⚠️ AMARILLO - Atención**")
            for item in semaforo.get('amarillo', []):
                st.write(f"• {item}")
        
        with col3:
            st.error("**🔴 ROJO - Crítico**")
            for item in semaforo.get('rojo', []):
                st.write(f"• {item}")
        
        st.divider()
        
        # PLAN DE ACCIÓN
        st.subheader("📅 Plan de Acción - Próximos 90 Días")
        plan = datos_analisis.get('plan_90_dias', [])
        
        for i, accion in enumerate(plan, 1):
            st.write(f"**{i}.** {accion}")
        
        st.divider()
        
        # DESCARGA DE RESULTADOS
        st.subheader("📥 Exportar Resultados")
        
        json_export = json.dumps(datos_analisis, indent=2, ensure_ascii=False)
        
        st.download_button(
            label="📄 Descargar Análisis Completo (JSON)",
            data=json_export,
            file_name=f"finatrix_analisis_{archivo.name}.json",
            mime="application/json",
            use_container_width=True
        )

else:
    # Mensaje cuando no hay archivo
    st.info("👆 **Sube un archivo en el panel de arriba para comenzar el análisis**")

# ==================== FOOTER ====================
st.divider()
st.caption("🛡️ Finatrix Elite Pro | Powered by Groq + Gemini | Versión 2.0")
