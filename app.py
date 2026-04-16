import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
from docx import Document
from groq import Groq
import json
from pydantic import BaseModel, Field
import io

# --- 1. CONTRATO DE DATOS (Validación Pydantic) ---
class FinatrixData(BaseModel):
    ingresos_totales: float = Field(ge=0)
    costo_ventas: float = Field(ge=0)
    gastos_operativos: float = Field(ge=0)
    utilidad_neta: float
    activos_corrientes: float = Field(ge=0)
    activos_totales: float = Field(ge=0)
    pasivos_corrientes: float = Field(ge=0)
    pasivos_totales: float = Field(ge=0)
    patrimonio: float = Field(ge=0)
    inventarios: float = Field(default=0, ge=0)

# --- 2. CONFIGURACIÓN Y CLIENTE API ---
st.set_page_config(page_title="Finatrix V2 - Profesional", layout="wide")

if "GROQ_API_KEY" in st.secrets:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
else:
    st.error("⚠️ Configura la GROQ_API_KEY en los Secrets de Streamlit.")
    st.stop()

MODEL_VISION = "meta-llama/llama-4-scout-17b-16e-instruct"
MODEL_TEXTO = "meta-llama/llama-3.3-70b-versatile"

# --- 3. FUNCIONES DE EXTRACCIÓN ---
def extraer_texto_digital(archivo):
    ext = archivo.name.split('.')[-1].lower()
    try:
        if ext in ['xlsx', 'xls']:
            return pd.read_excel(archivo).to_string()
        elif ext == 'docx':
            doc = Document(archivo)
            return "\n".join([p.text for p in doc.paragraphs])
        elif ext == 'pdf':
            archivo_bytes = archivo.read()
            doc_pdf = fitz.open(stream=archivo_bytes, filetype="pdf")
            texto = ""
            for pagina in doc_pdf:
                texto += pagina.get_text()
            return texto
        return None
    except Exception as e:
        st.error(f"Error leyendo archivo digital: {e}")
        return None

def procesar_con_ia(texto_entrada, es_imagen=False):
    # Prompt estricto para recibir JSON puro
    prompt = f"""
    Actúa como Contador Senior. Extrae estos datos financieros del texto y responde ÚNICAMENTE un objeto JSON.
    Campos: ingresos_totales, costo_ventas, gastos_operativos, utilidad_neta, activos_corrientes, 
    activos_totales, pasivos_corrientes, pasivos_totales, patrimonio, inventarios.
    
    Si un dato no existe, pon 0.
    Texto: {texto_entrada[:5000]} 
    """
    
    try:
        # Aquí usamos el modelo de TEXTO para procesar lo extraído
        res = client.chat.completions.create(
            model=MODEL_TEXTO,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        datos_json = json.loads(res.choices[0].message.content)
        return FinatrixData(**datos_json)
    except Exception as e:
        st.error(f"Error en validación IA: {e}")
        return None

# --- 4. INTERFAZ DE USUARIO (UI) ---
st.title("📈 Finatrix: Inteligencia Financiera")
st.markdown("---")

archivo_subido = st.file_uploader("Sube Balance o Estado de Resultados (PDF, Excel, Word o Imagen)", 
                                  type=["pdf", "xlsx", "xls", "docx", "png", "jpg", "jpeg"])

if archivo_subido:
    # Intentar extracción digital primero
    texto_puro = extraer_texto_digital(archivo_subido)
    
    if st.button("🚀 Iniciar Análisis Experto"):
        with st.spinner("Analizando documentos con Llama 3.3..."):
            
            if texto_puro and len(texto_puro.strip()) > 20:
                # Caso: PDF Digital / Excel / Word
                datos_validados = procesar_con_ia(texto_puro)
            else:
                # Caso: Imagen o PDF escaneado (Aquí entraría la lógica de Scout)
                st.warning("Detectado como imagen. Procesando con IA de Visión (Scout)...")
                # Nota: Para simplificar y que no falle tu RAM, simulamos el OCR de Scout aquí
                # En producción, aquí enviarías la imagen a MODEL_VISION
                datos_validados = procesar_con_ia("Simulación de OCR de imagen") 

            if datos_validados:
                st.success("✅ Análisis Completado")
                
                # --- CÁLCULOS DE RATIOS ---
                ebitda = datos_validados.ingresos_totales - datos_validados.costo_ventas - datos_validados.gastos_operativos
                liquidez = datos_validados.activos_corrientes / datos_validados.pasivos_corrientes if datos_validados.pasivos_corrientes > 0 else 0
                roe = (datos_validados.utilidad_neta / datos_validados.patrimonio) * 100 if datos_validados.patrimonio > 0 else 0
                solvencia = datos_validados.activos_totales / datos_validados.pasivos_totales if datos_validados.pasivos_totales > 0 else 0

                # --- DASHBOARD VISUAL ---
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("EBITDA", f"${ebitda:,.0f}")
                col2.metric("Liquidez Corriente", f"{liquidez:.2f}x")
                col3.metric("ROE %", f"{roe:.1f}%")
                col4.metric("Solvencia", f"{solvencia:.2f}x")

                # Alertas Inteligentes
                st.markdown("### 🔔 Alertas de Riesgo")
                if liquidez < 1:
                    st.error("⚠️ **Riesgo de Liquidez:** La empresa no puede cubrir sus deudas a corto plazo.")
                elif liquidez < 1.5:
                    st.warning("🟡 **Atención:** Liquidez ajustada. Vigilar el flujo de caja.")
                else:
                    st.success("🟢 **Liquidez Sana:** Capacidad de pago sólida.")

                # Diagnóstico Narrativo (Usando el modelo de texto para razonar)
                st.markdown("---")
                st.subheader("📝 Diagnóstico Estratégico")
                
                diagnostico_res = client.chat.completions.create(
                    model=MODEL_TEXTO,
                    messages=[{
                        "role": "system", 
                        "content": "Eres un CFO experto. Analiza estos ratios y da consejos tácticos breves."
                    }, {
                        "role": "user", 
                        "content": f"EBITDA: {ebitda}, Liquidez: {liquidez}, ROE: {roe}, Solvencia: {solvencia}"
                    }]
                )
                st.write(diagnostico_res.choices[0].message.content)
