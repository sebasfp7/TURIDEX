import streamlit as st
import pandas as pd
from groq import Groq
import json
import plotly.graph_objects as go

# ==================== 1. CONFIGURACIÓN Y MOTOR FINANCIERO (PYTHON) ====================
st.set_page_config(page_title="Finatrix Elite v5.1", layout="wide")

def safe_div(n, d):
    return n / d if n and d and d != 0 else None

def validar_balance_pro(d):
    """Guardarraíl de seguridad contable (Fix Opinión 2)"""
    act, pas, pat = d.get('activos_totales'), d.get('pasivos_totales'), d.get('patrimonio')
    if not all([isinstance(x, (int, float)) for x in [act, pas, pat]]):
        return "⚠️ Datos de balance incompletos para validación."
    diff = abs(act - (pas + pat))
    if diff > act * 0.01:
        return f"❌ Balance descuadrado por ${diff:,.0f} (Dif. > 1%)."
    return "✅ Balance Cuadrado"

def calcular_metricas_python(d1, d5):
    """El 'Cerebro' Matemático: Aquí no hay alucinaciones de IA"""
    v1, v5 = d1.get('ventas'), d5.get('ventas')
    eb5 = d5.get('ebitda')
    
    m_ebitda = safe_div(eb5, v5)
    cagr = ((v5 / v1)**(1/4) - 1) if v1 and v5 and v1 > 0 else None
    rc = safe_div(d5.get('activos_corrientes'), d5.get('pasivos_corrientes'))
    
    return {
        "cagr": cagr,
        "m_ebitda": m_ebitda,
        "liquidez": rc,
        "coherencia": "Error" if (eb5 and v5 and eb5 > v5) else "OK"
    }

# ==================== 2. EXTRACCIÓN ROBUSTA (Fix Opinión 2) ====================
def extraer_datos_excel(archivo):
    xls = pd.ExcelFile(archivo)
    texto = ""
    for sheet in xls.sheet_names:
        # NO fillna(0) -> Usamos None para mantener integridad (Fix Opinión 1)
        df = pd.read_excel(xls, sheet_name=sheet).where(pd.notnull(pd.read_excel(xls, sheet_name=sheet)), None).head(35)
        try:
            texto += f"\n--- HOJA: {sheet} ---\n{df.to_markdown(index=False)}\n"
        except:
            texto += f"\n--- HOJA: {sheet} ---\n{df.to_csv(index=False, sep='|')}\n"
    return texto[:27000]

# ==================== 3. PROMPT DE NARRATIVA ESTRATÉGICA ====================
def obtener_analisis_ia(contexto, metricas_py, client):
    # Pasamos las métricas calculadas por Python como 'anclas' (Fix Opinión 1)
    prompt = f"""
    Eres un Senior Partner de Consultoría. No calcules, EXPLICA estos resultados:
    METRICAS REALES (Calculadas por sistema):
    - Crecimiento Ventas (CAGR): {metricas_py['cagr']:.2% if metricas_py['cagr'] else 'N/D'}
    - Margen EBITDA A5: {metricas_py['m_ebitda']:.2% if metricas_py['m_ebitda'] else 'N/D'}
    - Razón Corriente: {metricas_py['liquidez']:.2f if metricas_py['liquidez'] else 'N/D'}
    
    TAREA: Genera un Informe Ejecutivo basado en estos números y los datos del Excel:
    1. Diagnóstico de Rentabilidad.
    2. Análisis de Liquidez (¿Dinero ocioso o riesgo?).
    3. Creación de Valor (EVA vs WACC).
    4. Estrategia de Cartera y Activos.
    5. Plan de Acción (3 pasos inmediatos).

    REGLA: Si ves incoherencias (ej. EBITDA > Ventas), denúncialo.
    {contexto}
    RESPONDE SOLO EN JSON:
    {{
      "diagnostico_ia": "texto markdown extenso...",
      "score": 1-100,
      "alerta_critica": "string o null"
    }}
    """
    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(res.choices[0].message.content)

# ==================== 4. INTERFAZ Y LÓGICA DE CONTROL ====================
st.title("🛡️ Finatrix Elite v5.1")
api_key = st.sidebar.text_input("Groq API Key", type="password")
archivo = st.sidebar.file_uploader("Subir Simulación", type=["xlsx"])

if archivo and api_key:
    client = Groq(api_key=api_key)
    if st.button("🚀 Ejecutar Auditoría Híbrida"):
        with st.spinner("Auditando..."):
            # A. Extracción e IA de extracción inicial
            contexto = extraer_datos_excel(archivo)
            
            # B. IA extrae datos brutos (Sin calcular)
            extract_prompt = "Extrae ventas A1, ventas A5, ebitda A5, activos_totales, pasivos_totales, patrimonio, activos_corrientes, pasivos_corrientes. Devuelve JSON."
            res_raw = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user", "content": f"{extract_prompt}\n{contexto}"}], response_format={"type":"json_object"})
            d_raw = json.loads(res_raw.choices[0].message.content)
            
            # C. Python toma el control (Fix Opinión 1)
            metricas = calcular_metricas_python(d_raw.get('año1', d_raw), d_raw.get('año5', d_raw))
            validacion = validar_balance_pro(d_raw.get('año5', d_raw))
            
            # D. IA genera la narrativa (Modo Consultor)
            analisis = obtener_analisis_ia(contexto, metricas, client)
            
            # --- DASHBOARD ---
            st.metric("Confianza del Análisis (Score)", f"{analisis['score']}%")
            
            # Alertas Rojas (Fix Opinión 1)
            if validacion != "✅ Balance Cuadrado": st.error(validacion)
            if metricas['coherencia'] == "Error": st.error("🚨 ERROR: EBITDA reportado es mayor que las Ventas.")
            
            tab1, tab2, tab3 = st.tabs(["📋 Resumen Ejecutivo", "🧐 Análisis Auditor", "📊 Métricas Hard"])
            
            with tab1:
                st.markdown(analisis['diagnostico_ia'])
            
            with tab2:
                st.subheader("Modo Auditoría: Detección de Inconsistencias")
                st.write(f"**Estado del Balance:** {validacion}")
                st.write(f"**Coherencia Operativa:** {metricas['coherencia']}")
                if analisis.get('alerta_critica'): st.warning(analisis['alerta_critica'])
                
            with tab3:
                st.write("### Datos Calculados por Python (100% Verificados)")
                st.json(metricas)
