import streamlit as st
from groq import Groq
import base64
from PIL import Image
import io
import json
import plotly.graph_objects as go
from database import calcular_ratios_financieros

# Configuración Profesional
st.set_page_config(page_title="FINATRIX IA - Analista Financiero", layout="wide")

# Estilo "Bloomberg/Fintech"
st.markdown("""
<style>
    .reportview-container { background: #0e1117; }
    .metric-card { background: #1a1c24; padding: 20px; border-radius: 10px; border-left: 5px solid #00ff00; }
    .stProgress > div > div > div > div { background-color: #00ff00; }
</style>
""", unsafe_allow_html=True)

SELECTED_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

st.title("📊 FINATRIX IA")
st.subheader("Análisis Inteligente de Estados Financieros")

# --- Lógica de Procesamiento ---
def procesar_finanzas(image_bytes):
    b64 = base64.b64encode(image_bytes).decode()
    
    with st.status("🚀 Iniciando Auditoría IA...", expanded=True) as status:
        # PASO 1: OCR y Extracción de Datos
        status.update(label="👁️ Extrayendo datos numéricos de la imagen...")
        prompt_ocr = """Analiza esta imagen financiera. Extrae los siguientes valores numéricos: 
        ingresos_totales, costo_ventas, gastos_operativos, activos_totales, pasivos_totales.
        Responde SOLO con un JSON válido."""
        
        res1 = client.chat.completions.create(
            model=SELECTED_MODEL,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": prompt_ocr},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
            ]}],
            temperature=0,
            response_format={"type": "json_object"}
        )
        datos_raw = json.loads(res1.choices[0].message.content)
        
        # PASO 2: Interpretación de Negocio
        status.update(label="🧠 Generando diagnóstico financiero...")
        ratios = calcular_ratios_financieros(datos_raw)
        
        prompt_diag = f"Actúa como un CFO senior. Analiza estos ratios: {ratios}. Dame un resumen ejecutivo de 3 párrafos sobre la salud de esta empresa y recomendaciones."
        res2 = client.chat.completions.create(
            model=SELECTED_MODEL,
            messages=[{"role": "user", "content": prompt_diag}],
            temperature=0.7
        )
        diagnostico = res2.choices[0].message.content
        
        status.update(label="✅ Análisis Completo", state="complete")
        return datos_raw, ratios, diagnostico

# --- Interfaz de Usuario ---
archivo = st.file_uploader("Suba captura de balance o estado de resultados", type=["png", "jpg", "jpeg"])

if archivo:
    col1, col2 = st.columns([1, 2])
    with col1:
        img = Image.open(archivo)
        st.image(img, caption="Documento Analizado")
        
    if st.button("🔍 ANALIZAR AHORA", type="primary"):
        datos, ratios, diag = procesar_finanzas(archivo.getvalue())
        
        with col2:
            st.markdown("### 📈 Ratios Clave")
            c1, c2, c3 = st.columns(3)
            c1.metric("Margen EBITDA", f"{ratios['margen_ebitda']}%")
            c2.metric("Ratio Solvencia", f"{ratios['ratio_solvencia']}x")
            c3.metric("Salud", ratios['salud_general'])
            
            st.markdown("### 📝 Diagnóstico Ejecutivo")
            st.info(diag)
            
            # Gráfico de Radar para visualizar salud
            fig = go.Figure(data=go.Scatterpolar(
              r=[ratios['margen_bruto'], ratios['margen_ebitda'], ratios['ratio_solvencia']*10, 50],
              theta=['Margen Bruto','Margen EBITDA','Solvencia (x10)','Eficiencia'],
              fill='toself'
            ))
            st.plotly_chart(fig)
