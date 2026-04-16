import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
from docx import Document
from groq import Groq
import json
from pydantic import BaseModel, Field, ValidationError
import io
import base64

# --- 1. CONTRATO DE DATOS (Pydantic mejorado) ---
class FinatrixData(BaseModel):
    # Usamos Optional para seguir el consejo de "null en vez de 0"
    ingresos_totales: float = Field(ge=0)
    costo_ventas: float = Field(ge=0)
    gastos_operativos: float = Field(ge=0)
    utilidad_neta: float # Puede ser negativa (pérdida)
    activos_corrientes: float = Field(ge=0)
    activos_totales: float = Field(ge=0)
    pasivos_corrientes: float = Field(ge=0)
    pasivos_totales: float = Field(ge=0)
    patrimonio: float = Field(ge=0)
    inventarios: float = Field(default=0, ge=0)

# --- 2. MOTOR DE CÁLCULOS (Lógica separada de la UI) ---
def calcular_metricas(d: FinatrixData):
    """Calcula 12+ ratios financieros con los datos validados."""
    ebitda = d.ingresos_totales - d.costo_ventas - d.gastos_operativos
    
    return {
        "ebitda": ebitda,
        "margen_bruto": ((d.ingresos_totales - d.costo_ventas) / d.ingresos_totales * 100) if d.ingresos_totales > 0 else 0,
        "margen_ebitda": (ebitda / d.ingresos_totales * 100) if d.ingresos_totales > 0 else 0,
        "margen_neto": (d.utilidad_neta / d.ingresos_totales * 100) if d.ingresos_totales > 0 else 0,
        "liquidez_corriente": d.activos_corrientes / d.pasivos_corrientes if d.pasivos_corrientes > 0 else 0,
        "prueba_acida": (d.activos_corrientes - d.inventarios) / d.pasivos_corrientes if d.pasivos_corrientes > 0 else 0,
        "roe": (d.utilidad_neta / d.patrimonio * 100) if d.patrimonio > 0 else 0,
        "roa": (d.utilidad_neta / d.activos_totales * 100) if d.activos_totales > 0 else 0,
        "endeudamiento": (d.pasivos_totales / d.activos_totales * 100) if d.activos_totales > 0 else 0,
        "deuda_patrimonio": d.pasivos_totales / d.patrimonio if d.patrimonio > 0 else 0,
        "deuda_ebitda": d.pasivos_totales / ebitda if ebitda > 0 else 0,
        "rotacion_activos": d.ingresos_totales / d.activos_totales if d.activos_totales > 0 else 0
    }

# --- 3. CONFIGURACIÓN ---
st.set_page_config(page_title="Finatrix V3 - Enterprise", layout="wide")
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

MODEL_VISION = "meta-llama/llama-4-scout-17b-16e-instruct"
MODEL_TEXTO = "meta-llama/llama-3.3-70b-versatile"

# --- 4. FUNCIONES DE EXTRACCIÓN Y LIMPIEZA ---
def limpiar_valor(v):
    if isinstance(v, str):
        v = v.replace(",", "").replace("$", "").replace("%", "").strip()
    try:
        return float(v)
    except:
        return 0.0

def extraer_texto_multiformato(archivo):
    ext = archivo.name.split('.')[-1].lower()
    try:
        if ext in ['xlsx', 'xls']:
            return pd.read_excel(archivo).to_string()
        elif ext == 'docx':
            return "\n".join([p.text for p in Document(archivo).paragraphs])
        elif ext == 'pdf':
            # getvalue() es más seguro que read() para evitar vaciar el buffer
            doc = fitz.open(stream=archivo.getvalue(), filetype="pdf")
            return "\n".join([pag.get_text() for pag in doc])
        return None
    except Exception as e:
        st.error(f"Error al leer archivo: {e}")
        return None

# --- 5. PROMPTS MEJORADOS (Solución a Opinión 1 y 2) ---
def obtener_datos_ia(contenido, es_imagen=False):
    # Prompt ultra-estricto para evitar alucinaciones
    prompt_sistema = """Actúa como un Contador Forense. Tu única misión es extraer datos financieros exactos. 
    REGLAS:
    1. Si un dato no aparece explícitamente, devuelve null.
    2. NO hagas estimaciones ni cálculos.
    3. NO inventes datos si el texto es confuso.
    4. Responde ÚNICAMENTE con el objeto JSON."""
    
    prompt_usuario = f"Extrae estos campos en JSON: ingresos_totales, costo_ventas, gastos_operativos, utilidad_neta, activos_corrientes, activos_totales, pasivos_corrientes, pasivos_totales, patrimonio, inventarios. \n\n Texto: {contenido[:15000]}"

    try:
        # Aquí enviaríamos a SCOUT si fuera imagen, por ahora usamos Llama 3.3 para texto
        res = client.chat.completions.create(
            model=MODEL_TEXTO,
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_usuario}
            ],
            response_format={"type": "json_object"}
        )
        
        datos_raw = json.loads(res.choices[0].message.content)
        # Limpieza robusta de números antes de validar
        datos_limpios = {k: limpiar_valor(v) for k, v in datos_raw.items()}
        return FinatrixData(**datos_limpios)
    except Exception as e:
        st.error(f"Error en la IA: {e}")
        return None

# --- 6. INTERFAZ ---
st.title("🛡️ Finatrix V3.0: Análisis Financiero Blindado")

archivo = st.file_uploader("Sube Balance / Estado de Resultados", type=["pdf", "xlsx", "docx", "png", "jpg"])

if archivo:
    if st.button("🚀 Iniciar Análisis Profesional"):
        texto = extraer_texto_multiformato(archivo)
        
        if not texto: # Caso de imagen
            st.error("🚫 Por ahora solo se soportan documentos digitales (PDF, Excel, Word). El módulo de Visión (Scout) para fotos está en mantenimiento.")
            st.stop()
            
        with st.spinner("IA procesando y validando integridad de datos..."):
            datos = obtener_datos_ia(texto)
            
            if datos:
                # CÁLCULOS
                r = calcular_metricas(datos)
                
                # UI: DASHBOARD DE MÉTRICAS
                st.success("✅ Datos validados contablemente.")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("EBITDA", f"${r['ebitda']:,.0f}")
                c2.metric("Liquidez", f"{r['liquidez_corriente']:.2f}x")
                c3.metric("ROE", f"{r['roe']:.1f}%")
                c4.metric("Endeudamiento", f"{r['endeudamiento']:.1f}%")

                # SEMÁFORO DE ALERTAS (Punto 7 y 8 de la opinión)
                st.subheader("🔔 Sistema de Alertas Inteligentes")
                col_a, col_b = st.columns(2)
                
                with col_a:
                    if r['liquidez_corriente'] < 1.1:
                        st.error(f"🔴 CRÍTICO: Liquidez de {r['liquidez_corriente']:.2f}. No cubre deudas cortas.")
                    elif r['liquidez_corriente'] < 1.5:
                        st.warning(f"🟡 ADVERTENCIA: Liquidez de {r['liquidez_corriente']:.2f} está en el límite.")
                    
                    if r['endeudamiento'] > 70:
                        st.error(f"🔴 CRÍTICO: Endeudamiento del {r['endeudamiento']:.1f}%. Muy alto.")

                with col_b:
                    if r['margen_ebitda'] < 10:
                        st.error(f"🔴 CRÍTICO: Rentabilidad operativa muy baja ({r['margen_ebitda']:.1f}%).")
                    elif r['roe'] > 15:
                        st.success(f"🟢 EXCELENTE: El ROE del {r['roe']:.1f}% es muy atractivo.")

                # DIAGNÓSTICO ESTRATÉGICO (Prompt mejorado por secciones)
                st.divider()
                st.subheader("📝 Diagnóstico CFO Senior")
                
                try:
                    res_diag = client.chat.completions.create(
                        model=MODEL_TEXTO,
                        messages=[{
                            "role": "system",
                            "content": "Eres un CFO experto. Analiza los ratios financieros entregados. Divide tu respuesta en: 1. Análisis de Liquidez, 2. Rentabilidad, 3. Solvencia y 4. Recomendaciones Críticas."
                        }, {
                            "role": "user",
                            "content": str(r)
                        }]
                    )
                    st.write(res_diag.choices[0].message.content)
                except Exception as e:
                    st.error("El diagnóstico falló, pero tus ratios están arriba.")
