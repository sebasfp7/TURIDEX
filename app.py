import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
from docx import Document
from groq import Groq
import json
from pydantic import BaseModel, Field
from typing import Optional
import io
import base64

# --- 1. CONTRATO DE DATOS (Pydantic con Opcionales para Auditoría Real) ---
class FinatrixData(BaseModel):
    ingresos_totales: Optional[float] = Field(default=None, ge=0)
    costo_ventas: Optional[float] = Field(default=None, ge=0)
    gastos_operativos: Optional[float] = Field(default=None, ge=0)
    utilidad_neta: Optional[float] = Field(default=None)
    activos_corrientes: Optional[float] = Field(default=None, ge=0)
    activos_totales: Optional[float] = Field(default=None, ge=0)
    pasivos_corrientes: Optional[float] = Field(default=None, ge=0)
    pasivos_totales: Optional[float] = Field(default=None, ge=0)
    patrimonio: Optional[float] = Field(default=None, ge=0)
    inventarios: Optional[float] = Field(default=0, ge=0)

# --- 2. MOTOR DE CÁLCULOS Y SCORE PROPIETARIO ---
def calcular_metricas(d: FinatrixData):
    # Lógica de limpieza: si es None, tratar como 0 para el cálculo, pero avisar
    def v(val): return val if val is not None else 0.0
    
    ing = v(d.ingresos_totales)
    ebitda = ing - v(d.costo_ventas) - v(d.gastos_operativos)
    
    r = {
        "ebitda": ebitda,
        "margen_ebitda": (ebitda / ing * 100) if ing > 0 else 0,
        "liquidez_corriente": v(d.activos_corrientes) / v(d.pasivos_corrientes) if v(d.pasivos_corrientes) > 0 else 0,
        "roe": (v(d.utilidad_neta) / v(d.patrimonio) * 100) if v(d.patrimonio) > 0 else 0,
        "endeudamiento": (v(d.pasivos_totales) / v(d.activos_totales) * 100) if v(d.activos_totales) > 0 else 0,
        "deuda_ebitda": v(d.pasivos_totales) / ebitda if ebitda > 0 else None,
        "prueba_acida": (v(d.activos_corrientes) - v(d.inventarios)) / v(d.pasivos_corrientes) if v(d.pasivos_corrientes) > 0 else 0
    }
    
    # FINATRIX SCORE™ (0-100)
    score = 0
    score += min(30, r['liquidez_corriente'] * 15)
    score += min(30, r['margen_ebitda'] * 1.5)
    score += min(20, max(0, 100 - r['endeudamiento']))
    score += min(20, max(0, r['roe']))
    r["finatrix_score"] = int(min(100, max(0, score)))
    return r

# --- 3. CONFIGURACIÓN ---
st.set_page_config(page_title="Finatrix V4 Elite", layout="wide", page_icon="🛡️")

# Manejo robusto de API Key (Opinión 1, punto 8)
api_key = st.secrets.get("GROQ_API_KEY")
if not api_key:
    st.error("🔑 Error: Falta GROQ_API_KEY en Secrets.")
    st.stop()
client = Groq(api_key=api_key)

MODEL_VISION = "meta-llama/llama-4-scout-17b-16e-instruct"
MODEL_TEXTO = "meta-llama/llama-3.3-70b-versatile"

# --- 4. EXTRACCIÓN Y LIMPIEZA ---
def limpiar_valor(v):
    if v is None: return None
    if isinstance(v, str):
        v = v.replace(",", "").replace("$", "").replace("%", "").strip()
        if v.lower() in ["null", "n/a", "", "-"]: return None
    try: return float(v)
    except: return None

def extraer_texto(archivo):
    ext = archivo.name.split('.')[-1].lower()
    # Usamos getbuffer() para evitar errores de atributo (Opinión 1, punto 1)
    buf = archivo.getbuffer()
    if ext in ['xlsx', 'xls']: return pd.read_excel(buf).to_string()
    if ext == 'docx': return "\n".join([p.text for p in Document(io.BytesIO(buf)).paragraphs])
    if ext == 'pdf':
        doc = fitz.open(stream=buf, filetype="pdf")
        return "\n".join([pag.get_text() for pag in doc])
    return None

# --- 5. MODELOS IA (Visión y Texto) ---
def obtener_datos_ia(contenido, es_imagen=False):
    prompt_sys = "Actúa como Contador Forense. Extrae datos financieros en JSON. Si no existe, devuelve null. No inventes."
    prompt_usr = f"Extrae: ingresos_totales, costo_ventas, gastos_operativos, utilidad_neta, activos_corrientes, activos_totales, pasivos_corrientes, pasivos_totales, patrimonio, inventarios. Texto: {contenido[:12000]}"

    try:
        if es_imagen:
            # MÓDULO SCOUT ACTIVADO (Opinión 3, punto 4)
            b64 = base64.b64encode(contenido).decode()
            res = client.chat.completions.create(
                model=MODEL_VISION,
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": prompt_usr},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]}],
                response_format={"type": "json_object"}
            )
        else:
            res = client.chat.completions.create(
                model=MODEL_TEXTO,
                messages=[{"role": "system", "content": prompt_sys}, {"role": "user", "content": prompt_usr}],
                response_format={"type": "json_object"}
            )
        
        datos_raw = json.loads(res.choices[0].message.content)
        datos_limpios = {k: limpiar_valor(v) for k, v in datos_raw.items()}
        return FinatrixData(**datos_limpios)
    except Exception as e:
        st.error(f"Fallo en IA: {e}")
        return None

# --- 6. UI PRINCIPAL ---
st.title("🛡️ Finatrix V4.0 Elite")
archivo = st.file_uploader("Sube documento o imagen", type=["pdf", "xlsx", "docx", "png", "jpg"])

if archivo:
    if st.button("🚀 Iniciar Análisis"):
        # Lógica de detección de imagen
        es_img = archivo.type.startswith('image')
        contenido = archivo.getbuffer() if es_img else extraer_texto(archivo)
        
        with st.spinner("Procesando..."):
            datos = obtener_datos_ia(contenido, es_imagen=es_img)
            
            if datos:
                # INTEGRIDAD CONTABLE (Opinión 2, punto 3)
                cuadra = abs((datos.activos_totales or 0) - ((datos.pasivos_totales or 0) + (datos.patrimonio or 0))) < 10
                if not cuadra: st.warning("⚠️ El balance parece no cuadrar (Activos ≠ Pasivos + Pat).")

                r = calcular_metricas(datos)
                
                # DASHBOARD
                c1, c2, c3 = st.columns([1,2,1])
                c1.metric("FINATRIX SCORE™", f"{r['finatrix_score']}/100")
                c2.subheader(f"Salud: {'🔴 Crítica' if r['finatrix_score'] < 40 else '🟡 Regular' if r['finatrix_score'] < 70 else '🟢 Excelente'}")
                
                st.divider()
                # RATIOS EN COLUMNAS
                cols = st.columns(4)
                cols[0].metric("Liquidez", f"{r['liquidez_corriente']:.2f}x")
                cols[1].metric("Margen EBITDA", f"{r['margen_ebitda']:.1f}%")
                cols[2].metric("ROE", f"{r['roe']:.1f}%")
                cols[3].metric("Endeudamiento", f"{r['endeudamiento']:.1f}%")

                # EXPORTACIÓN (Opinión 1, punto 3)
                df_exp = pd.DataFrame(list(r.items()), columns=["Métrica", "Valor"])
                csv = df_exp.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Descargar Reporte CSV", csv, "finatrix_report.csv", "text/csv")

                # DIAGNÓSTICO CFO
                st.info("💡 Diagnóstico Estratégico:")
                diag = client.chat.completions.create(
                    model=MODEL_TEXTO,
                    messages=[{"role": "user", "content": f"Analiza estos ratios financieros y da recomendaciones cortas: {r}"}]
                )
                st.write(diag.choices[0].message.content)
