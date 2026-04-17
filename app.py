import streamlit as st
import pandas as pd
from docx import Document
from groq import Groq
import json
import hashlib
import plotly.graph_objects as go
import re

# Fallback para PDF: pdfplumber > fitz
try:
    import pdfplumber
    PDF_ENGINE = "pdfplumber"
except ModuleNotFoundError:
    import fitz
    PDF_ENGINE = "fitz"

# Fallback para markdown: tabulate > to_string
try:
    import tabulate
    HAS_TABULATE = True
except ModuleNotFoundError:
    HAS_TABULATE = False

# ==================== CONFIGURACIÓN ====================
st.set_page_config(page_title="Finatrix Auditor v3.1", layout="wide")

if 'analisis' not in st.session_state:
    st.session_state.analisis = None
if 'cache' not in st.session_state:
    st.session_state.cache = {}

# ==================== UTILIDADES LÓGICAS ====================
def safe_div(n, d):
    if n is None or d == 0:
        return None
    return n / d

def limpiar_texto_para_ia(texto):
    """NUEVO: Quita caracteres que rompen el JSON de Groq"""
    # Quita caracteres de control y emojis
    texto = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', '', texto)
    # Limita longitud para no exceder tokens
    return texto[:24000]

def validar_balance(d):
    activos, pasivos, patrimonio = d.get('activos_totales'), d.get('pasivos_totales'), d.get('patrimonio')
    if None in [activos, pasivos, patrimonio]:
        return None
    diferencia = abs(activos - (pasivos + patrimonio))
    tolerancia = activos * 0.01 if activos > 0 else 0
    if diferencia > tolerancia:
        return f"ALERTA: Balance no cuadra. Diferencia: ${diferencia:,.0f}. Activo={activos:,.0f}, Pasivo+Patrimonio={pasivos+patrimonio:,.0f}"
    return None

def motor_dupont(utilidad, ingresos, activos, patrimonio):
    margen_neto = safe_div(utilidad, ingresos)
    rotacion_activos = safe_div(ingresos, activos)
    apalancamiento = safe_div(activos, patrimonio)
    roe_calculado = None
    if None not in [margen_neto, rotacion_activos, apalancamiento]:
        roe_calculado = margen_neto * rotacion_activos * apalancamiento
    return {
        "margen_neto": margen_neto,
        "rotacion_activos": rotacion_activos,
        "apalancamiento": apalancamiento,
        "roe_dupont": roe_calculado
    }

def clasificar_empresa(margen, ingresos, eva):
    if ingresos == 0 or ingresos is None:
        return "Empresa sin operación registrada", "⚪"
    if margen is not None and margen < 0:
        return "Empresa en fase de pérdidas", "🔴"
    if eva is not None and eva > 0:
        return "Generadora de valor (EVA+)", "🟢"
    return "Empresa operativa estable", "🟡"

def df_to_text(df):
    df = df.fillna('')
    if HAS_TABULATE:
        return df.to_markdown(index=False)
    else:
        return df.to_string(index=False)

# ==================== EXTRACCIÓN CON FALLBACK ====================
def extraer_texto_pro(archivo):
    tipo = archivo.type
    if tipo == "application/pdf":
        texto = ""
        if PDF_ENGINE == "pdfplumber":
            with pdfplumber.open(archivo) as pdf:
                for page in pdf.pages:
                    texto += page.extract_text() or ""
                    tablas = page.extract_tables()
                    for t in tablas:
                        if t:
                            df_tabla = pd.DataFrame(t[1:], columns=t[0]).fillna('')
                            texto += "\n" + df_to_text(df_tabla)
        else:
            doc = fitz.open(stream=archivo.read(), filetype="pdf")
            texto = "\n".join([page.get_text() for page in doc])
        return texto
    elif "spreadsheet" in tipo:
        xls = pd.ExcelFile(archivo)
        texto_full = ""
        for sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet)
            if not df.dropna(how='all').empty:
                texto_full += f"\n### HOJA: {sheet} ###\n{df_to_text(df)}\n"
        return texto_full
    elif "word" in tipo:
        doc = Document(archivo)
        return "\n".join([p.text for p in doc.paragraphs])
    return ""

# ==================== PROMPT CORREGIDO ====================
def obtener_prompt_auditor(texto):
    # NUEVO: Limpia texto y asegura que diga "JSON" varias veces
    texto_limpio = limpiar_texto_para_ia(texto)
    return f"""
    Eres un Auditor Financiero Forense. Debes devolver SOLO un objeto JSON válido.
    Tu respuesta DEBE ser JSON. No agregues texto antes o después del JSON.

    REGLA: Si una celda está vacía o no existe, usa null. NO USES 0.
    Busca: ingresos, ebitda, utilidad_neta, activos_corrientes, activos_totales,
    pasivos_corrientes, pasivos_totales, patrimonio, eva, wacc.

    El formato de tu respuesta debe ser JSON con esta estructura exacta:
    {{
      "estado_proceso": "OK",
      "datos": {{
        "ingresos": 12345.0,
        "ebitda": null,
        "utilidad_neta": 1234.0,
        "activos_corrientes": null,
        "activos_totales": 50000.0,
        "pasivos_corrientes": null,
        "pasivos_totales": 20000.0,
        "patrimonio": 30000.0,
        "eva": 500.0,
        "wacc": 0.11
      }},
      "hallazgo_clave": "texto"
    }}

    Si no encuentras datos usa "ARCHIVO_INVALIDO" en estado_proceso.
    TEXTO FINANCIERO:
    {texto_limpio}
    """

# ==================== MOTOR DE ANÁLISIS ====================
def realizar_analisis_v3(datos_json, client):
    d = datos_json['datos']

    alerta_balance = validar_balance(d)
    if alerta_balance:
        return {"error": alerta_balance}

    errores = []
    for campo in ['ingresos', 'activos_totales', 'patrimonio']:
        if d.get(campo) is None:
            errores.append(campo.replace('_', ' ').title())
    if errores:
        return {"error": f"Datos insuficientes para auditoría. Faltan: {', '.join(errores)}"}

    ingresos, utilidad = d.get('ingresos'), d.get('utilidad_neta')
    activos, patrimonio = d.get('activos_totales'), d.get('patrimonio')
    activos_c, pasivos_c = d.get('activos_corrientes'), d.get('pasivos_corrientes')
    eva = d.get('eva')

    m_neto = safe_div(utilidad, ingresos)
    lq_cte = safe_div(activos_c, pasivos_c)
    roe = safe_div(utilidad, patrimonio)
    end_total = safe_div(d.get('pasivos_totales'), activos)

    dupont = motor_dupont(utilidad, ingresos, activos, patrimonio)
    estado, icono = clasificar_empresa(m_neto, ingresos, eva)

    alertas = []
    if lq_cte and lq_cte < 1.1: alertas.append("⚠️ Riesgo de Liquidez Inmediata")
    if end_total and end_total > 0.7: alertas.append("⚠️ Apalancamiento Crítico (>70%)")
    if eva and eva < 0: alertas.append("⚠️ Destrucción de Valor Económico")

    score = 0
    if m_neto is not None: score += min(25, max(0, m_neto * 250))
    if lq_cte is not None: score += min(25, max(0, (lq_cte - 0.5) * 35.7))
    if roe is not None: score += min(25, max(0, roe * 166.7))
    if eva is not None: score += 25 if eva > 0 else 0
    score = round(score)

    prompt_diag = f"""Como CFO, redacta un informe corto en formato JSON. Devuelve solo JSON:
    {{
      "informe": "texto del informe"
    }}
    Basado en: Estado={estado}, Margen={m_neto}, Liquidez={lq_cte}, ROE={roe}, Endeudamiento={end_total}, DuPont={dupont}, Alertas={alertas}"""

    try:
        res_ia = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt_diag}],
            response_format={"type": "json_object"}
        )
        diagnostico_json = json.loads(res_ia.choices[0].message.content)
        diagnostico_texto = diagnostico_json.get('informe', 'No se pudo generar informe')
    except:
        diagnostico_texto = "Error generando diagnóstico con IA. Revisar datos manualmente."

    return {
        "score": score, "estado": estado, "icono": icono,
        "ratios": {
            "Margen Neto": f"{m_neto*100:.2f}%" if m_neto is not None else "N/A",
            "Liquidez": f"{lq_cte:.2f}x" if lq_cte is not None else "N/A",
            "ROE": f"{roe*100:.2f}%" if roe is not None else "N/A",
            "Endeudamiento": f"{end_total*100:.2f}%" if end_total is not None else "N/A"
        },
        "dupont": {
            "Margen Neto": f"{dupont['margen_neto']*100:.2f}%" if dupont['margen_neto'] is not None else "N/A",
            "Rotación Activos": f"{dupont['rotacion_activos']:.2f}x" if dupont['rotacion_activos'] is not None else "N/A",
            "Apalancamiento": f"{dupont['apalancamiento']:.2f}x" if dupont['apalancamiento'] is not None else "N/A",
            "ROE DuPont": f"{dupont['roe_dupont']*100:.2f}%" if dupont['roe_dupont'] is not None else "N/A"
        },
        "diagnostico": diagnostico_texto,
        "alertas": alertas
    }

# ==================== UI STREAMLIT ====================
st.title("🛡️ Finatrix Auditor v3.1")
st.markdown("### Diagnóstico con validación de balance + Análisis DuPont")

with st.sidebar:
    key = st.text_input("Groq API Key", type="password")
    archivo = st.file_uploader("Subir Estados Financieros", type=["pdf", "xlsx", "docx"])
    st.caption(f"PDF: {PDF_ENGINE} | Markdown: {'tabulate' if HAS_TABULATE else 'to_string'}")

if archivo and key:
    client = Groq(api_key=key)
    file_hash = hashlib.md5(archivo.getvalue()).hexdigest()

    if st.button("🚀 Ejecutar Análisis Forense"):
        with st.spinner("Extrayendo y validando estructuras..."):
            try:
                if file_hash in st.session_state.cache:
                    datos_extraidos = st.session_state.cache[file_hash]
                    st.info("Usando datos cacheados")
                else:
                    texto = extraer_texto_pro(archivo)
                    if not texto.strip():
                        st.error("No se pudo extraer texto del archivo")
                        st.stop()

                    # NUEVO: Try/except específico para Groq
                    res_json = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": obtener_prompt_auditor(texto)}],
                        response_format={"type": "json_object"}
                    )
                    datos_extraidos = json.loads(res_json.choices[0].message.content)
                    st.session_state.cache[file_hash] = datos_extraidos

                analisis = realizar_analisis_v3(datos_extraidos, client)

                if "error" in analisis:
                    st.error(analisis["error"])
                else:
                    st.session_state.analisis = analisis
                    st.success("Análisis completado.")

            except Exception as e:
                st.error(f"Error de Groq: {str(e)}")
                st.info("Causas comunes: 1) API Key inválida 2) Archivo muy grande 3) Contenido no financiero")

# ==================== DASHBOARD ====================
if st.session_state.analisis:
    res = st.session_state.analisis
    col1, col2, col3 = st.columns(3)
    col1.metric("SCORE", f"{res['score']}/100")
    col2.metric("ESTADO", res['estado'], res['icono'])

    with col3:
        m_neto_val = float(res['ratios']['Margen Neto'].replace('%','')) if res['ratios']['Margen Neto']!= "N/A" else 0
        liq_val = float(res['ratios']['Liquidez'].replace('x','')) if res['ratios']['Liquidez']!= "N/A" else 0
        roe_val = float(res['ratios']['ROE'].replace('%','')) if res['ratios']['ROE']!= "N/A" else 0
        end_val = float(res['ratios']['Endeudamiento'].replace('%','')) if res['ratios']['Endeudamiento']!= "N/A" else 100

        valores_radar = [
            min(100, max(0, m_neto_val * 5)),
            min(100, max(0, liq_val * 50)),
            min(100, max(0, roe_val * 5)),
            min(100, max(0, 100 - end_val))
        ]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=valores_radar, theta=['Rentabilidad','Liquidez','ROE','Solvencia'], fill='toself'))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False, height=250, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)

    tab1, tab2, tab3 = st.tabs(["📊 Ratios", "🔬 Análisis DuPont", "🧠 Informe CFO"])

    with tab1:
        st.table(pd.DataFrame([res['ratios']]))
    with tab2:
        st.caption("Descomposición del ROE: Margen × Rotación × Apalancamiento")
        st.table(pd.DataFrame([res['dupont']]))
    with tab3:
        if res['alertas']:
            st.warning("### Alertas de Auditoría\n" + "\n".join(res['alertas']))
        st.markdown(res['diagnostico'])
