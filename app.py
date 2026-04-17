import streamlit as st
import pandas as pd
import pdfplumber
from docx import Document
from groq import Groq
import json
import io
import hashlib
import plotly.graph_objects as go

# ==================== CONFIGURACIÓN DE PÁGINA ====================
st.set_page_config(page_title="Finatrix Auditor v3.1", layout="wide")

if 'analisis' not in st.session_state:
    st.session_state.analisis = None
if 'cache' not in st.session_state:
    st.session_state.cache = {}

# ==================== UTILIDADES LÓGICAS ====================
def safe_div(n, d):
    """Evita divisiones por cero y propaga el None si el dato falta."""
    if n is None or d == 0:
        return None
    return n / d

def validar_balance(d):
    """NUEVO: Valida que Activo = Pasivo + Patrimonio. Tolerancia 1%"""
    activos = d.get('activos_totales')
    pasivos = d.get('pasivos_totales')
    patrimonio = d.get('patrimonio')

    if None in [activos, pasivos, patrimonio]:
        return None # No hay datos suficientes para validar

    diferencia = abs(activos - (pasivos + patrimonio))
    tolerancia = activos * 0.01 if activos > 0 else 0

    if diferencia > tolerancia:
        return f"ALERTA: Balance no cuadra. Diferencia: ${diferencia:,.0f}. Activo={activos:,.0f}, Pasivo+Patrimonio={pasivos+patrimonio:,.0f}"
    return None

def motor_dupont(utilidad, ingresos, activos, patrimonio):
    """NUEVO: Descompone ROE en 3 palancas: Margen x Rotación x Apalancamiento"""
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

# ==================== EXTRACCIÓN MEJORADA ====================
def extraer_texto_pro(archivo):
    tipo = archivo.type
    if tipo == "application/pdf":
        texto = ""
        with pdfplumber.open(archivo) as pdf:
            for page in pdf.pages:
                texto += page.extract_text() or ""
                tablas = page.extract_tables()
                for t in tablas:
                    # MEJORA: fillna('') evita que la IA vea 'nan'
                    df_tabla = pd.DataFrame(t[1:], columns=t[0]).fillna('')
                    texto += "\n" + df_tabla.to_markdown(index=False)
        return texto
    elif "spreadsheet" in tipo:
        xls = pd.ExcelFile(archivo)
        texto_full = ""
        for sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet)
            if not df.dropna(how='all').empty:
                texto_full += f"\n### HOJA: {sheet} ###\n{df.fillna('').to_markdown(index=False)}\n"
        return texto_full
    return ""

# ==================== PROMPT QUIRÚRGICO ====================
def obtener_prompt_auditor(texto):
    return f"""
    Actúa como un Auditor Financiero Forense. Extrae los datos del último año disponible.
    REGLA: Si una celda está vacía o no existe, usa null. NO USES 0.

    Busca: ingresos, ebitda, utilidad_neta, activos_corrientes, activos_totales,
    pasivos_corrientes, pasivos_totales, patrimonio, eva, wacc.

    Responde en JSON:
    {{
      "estado_proceso": "OK" | "ARCHIVO_INVALIDO" | "DATOS_INCOMPLETOS",
      "datos": {{... }},
      "hallazgo_clave": "Breve nota técnica sobre la calidad de los datos"
    }}
    TEXTO: {texto[:25000]}
    """

# ==================== MOTOR DE ANÁLISIS (SIN PUNTOS CIEGOS) ====================
def realizar_analisis_v3(datos_json, client):
    d = datos_json['datos']

    # 1. NUEVO: Validación de Integridad del Balance
    alerta_balance = validar_balance(d)
    if alerta_balance:
        return {"error": alerta_balance}

    # 2. Validación de campos críticos
    errores = []
    campos_criticos = ['ingresos', 'activos_totales', 'patrimonio']
    for campo in campos_criticos:
        if d.get(campo) is None:
            errores.append(campo.replace('_', ' ').title())

    if errores:
        return {"error": f"Datos insuficientes para auditoría. Faltan: {', '.join(errores)}"}

    # 3. Cálculos con Lógica safe_div
    ingresos = d.get('ingresos')
    utilidad = d.get('utilidad_neta')
    activos = d.get('activos_totales')
    pasivos_c = d.get('pasivos_corrientes')
    activos_c = d.get('activos_corrientes')
    patrimonio = d.get('patrimonio')
    eva = d.get('eva')

    m_neto = safe_div(utilidad, ingresos)
    lq_cte = safe_div(activos_c, pasivos_c)
    roe = safe_div(utilidad, patrimonio)
    end_total = safe_div(d.get('pasivos_totales'), activos)

    # 4. NUEVO: Análisis DuPont
    dupont = motor_dupont(utilidad, ingresos, activos, patrimonio)

    # 5. Clasificación y Alertas
    estado, icono = clasificar_empresa(m_neto, ingresos, eva)

    alertas = []
    if lq_cte and lq_cte < 1.1: alertas.append("⚠️ Riesgo de Liquidez Inmediata")
    if end_total and end_total > 0.7: alertas.append("⚠️ Apalancamiento Crítico (>70%)")
    if eva and eva < 0: alertas.append("⚠️ Destrucción de Valor Económico")

    # 6. Score Ponderado mejorado - no binario
    score = 0
    if m_neto is not None: score += min(25, max(0, m_neto * 250)) # 10% margen = 25 pts
    if lq_cte is not None: score += min(25, max(0, (lq_cte - 0.5) * 35.7)) # 1.2 = 25 pts
    if roe is not None: score += min(25, max(0, roe * 166.7)) # 15% ROE = 25 pts
    if eva is not None: score += 25 if eva > 0 else 0
    score = round(score)

    # 7. Diagnóstico CFO con contexto DuPont
    prompt_diag = f"""Como CFO, redacta un informe corto basado en:
    - Estado: {estado}
    - Ratios: Margen {m_neto}, Liquidez {lq_cte}, ROE {roe}, Endeudamiento {end_total}
    - DuPont: Margen={dupont['margen_neto']}, Rotación={dupont['rotacion_activos']}, Apalancamiento={dupont['apalancamiento']}
    - Alertas Técnicas: {alertas}
    Explica qué palanca del ROE debe mejorar la empresa."""

    res_ia = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt_diag}]
    )

    return {
        "score": score,
        "estado": estado,
        "icono": icono,
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
        "diagnostico": res_ia.choices[0].message.content,
        "alertas": alertas
    }

# ==================== UI STREAMLIT ====================
st.title("🛡️ Finatrix Auditor v3.1")
st.markdown("### Sistema de Diagnóstico Financiero con Análisis DuPont")

with st.sidebar:
    key = st.text_input("Groq API Key", type="password")
    archivo = st.file_uploader("Subir Estados Financieros", type=["pdf", "xlsx"])
    st.divider()
    st.caption("v3.1 incluye: Validación de balance, DuPont y radar de salud")

if archivo and key:
    client = Groq(api_key=key)

    # NUEVO: Cache por hash para no pagar doble
    file_hash = hashlib.md5(archivo.getvalue()).hexdigest()

    if st.button("🚀 Ejecutar Análisis Forense"):
        with st.spinner("Extrayendo y validando estructuras..."):

            if file_hash in st.session_state.cache:
                datos_extraidos = st.session_state.cache[file_hash]
                st.info("Usando datos cacheados de análisis previo")
            else:
                texto = extraer_texto_pro(archivo)
                res_json = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": obtener_prompt_auditor(texto)}],
                    response_format={"type": "json_object"}
                )
                datos_extraidos = json.loads(res_json.choices[0].message.content)
                st.session_state.cache[file_hash] = datos_extraidos

            # Análisis Matemático + Diagnóstico
            analisis = realizar_analisis_v3(datos_extraidos, client)

            if "error" in analisis:
                st.error(analisis["error"])
            else:
                st.session_state.analisis = analisis
                st.success("Análisis completado.")

# ==================== DASHBOARD DE RESULTADOS ====================
if st.session_state.analisis:
    res = st.session_state.analisis

    col1, col2, col3 = st.columns(3)
    col1.metric("SCORE", f"{res['score']}/100")
    col2.metric("ESTADO", res['estado'], res['icono'])

    # NUEVO: Gráfico radar de salud financiera
    with col3:
        valores_radar = []
        labels_radar = []

        m_neto_val = float(res['ratios']['Margen Neto'].replace('%','')) if res['ratios']['Margen Neto']!= "N/A" else 0
        liq_val = float(res['ratios']['Liquidez'].replace('x','')) if res['ratios']['Liquidez']!= "N/A" else 0
        roe_val = float(res['ratios']['ROE'].replace('%','')) if res['ratios']['ROE']!= "N/A" else 0
        end_val = float(res['ratios']['Endeudamiento'].replace('%','')) if res['ratios']['Endeudamiento']!= "N/A" else 100

        # Normalizar a escala 0-100 para el radar
        valores_radar = [
            min(100, max(0, m_neto_val * 5)), # 20% margen = 100
            min(100, max(0, liq_val * 50)), # 2.0x liquidez = 100
            min(100, max(0, roe_val * 5)), # 20% ROE = 100
            min(100, max(0, 100 - end_val)) # 0% endeudamiento = 100
        ]
        labels_radar = ['Rentabilidad','Liquidez','ROE','Solvencia']

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=valores_radar,
            theta=labels_radar,
            fill='toself',
            name='Empresa'
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=False,
            height=250,
            margin=dict(l=20, r=20, t=20, b=20)
        )
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
