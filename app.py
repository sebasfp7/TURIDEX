import streamlit as st
import pandas as pd
from groq import Groq
import json
import plotly.graph_objects as go
import io
from xhtml2pdf import pisa

# ==================== 1. MOTOR FINANCIERO Y FORMATEO ====================
st.set_page_config(page_title="Finatrix Elite v6.1", layout="wide")

def safe_format(valor, tipo='num'):
    if not isinstance(valor, (int, float)): return "N/D"
    if tipo == 'pct': return f"{valor:.2%}"
    if tipo == 'x': return f"{valor:.2f}x"
    return f"${valor:,.0f}"

def safe_div(n, d):
    if n is None or d is None or d == 0: return None
    return n / d

def calcular_metricas_python(d_a1, d_a5):
    v1, v5, eb5 = d_a1.get('ventas'), d_a5.get('ventas'), d_a5.get('ebitda')
    cagr = ((v5 / v1)**(1/4) - 1) if v1 and v5 and v1 > 0 and v5 > 0 else None
    return {
        "cagr": cagr,
        "m_ebitda": safe_div(eb5, v5),
        "liquidez": safe_div(d_a5.get('activos_corrientes'), d_a5.get('pasivos_corrientes')),
        "incoherencia": True if (eb5 and v5 and eb5 > v5) else False,
        "eva": d_a5.get('eva'),
        "wacc": d_a5.get('wacc')
    }

def validar_balance_pro(d):
    act, pas, pat = d.get('activos_totales'), d.get('pasivos_totales'), d.get('patrimonio')
    if not all(isinstance(x, (int, float)) for x in [act, pas, pat]):
        return "⚠️ Datos de balance insuficientes."
    diff = abs(act - (pas + pat))
    return f"❌ Descuadre: ${diff:,.0f}" if diff > act * 0.01 else "✅ Balance Cuadrado"

# ==================== 2. EXTRACCIÓN Y NARRATIVA ====================
def extraer_datos_excel(archivo):
    xls = pd.ExcelFile(archivo)
    texto = ""
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet).head(35)
        df_clean = df.where(pd.notnull(df), None)
        texto += f"\n--- HOJA: {sheet} ---\n{df_clean.to_csv(index=False, sep='|')}\n"
    if len(texto) > 26000:
        st.sidebar.warning("⚠️ Datos truncados para optimizar análisis.")
        return texto[:26000] + "\n[TRUNCADO]"
    return texto

def obtener_analisis_ia(contexto, m, client):
    c_txt, e_txt = safe_format(m['cagr'], 'pct'), safe_format(m['m_ebitda'], 'pct')
    l_txt, w_txt, ev_txt = safe_format(m['liquidez'], 'x'), safe_format(m['wacc'], 'pct'), safe_format(m['eva'])
    prompt = f"""Eres Senior Partner. Explica: CAGR: {c_txt}, EBITDA: {e_txt}, Liq: {l_txt}, WACC: {w_txt}, EVA: {ev_txt}. 
    Analiza Rentabilidad y Riesgos. Excel: {contexto}. RESPONDE SOLO JSON: {{ "diagnostico": "markdown...", "score": 0-100 }}"""
    res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user", "content":prompt}], response_format={"type":"json_object"})
    return json.loads(res.choices[0].message.content)

# ==================== 3. FLUJO PRINCIPAL ====================
st.sidebar.header("⚙️ Finatrix Elite v6.1")
api_key = st.sidebar.text_input("Groq API Key", type="password")
archivo = st.sidebar.file_uploader("Subir Simulación", type=["xlsx"])

if not api_key: st.info("🔑 Ingresa tu API Key para comenzar.")
elif archivo:
    client = Groq(api_key=api_key)
    if st.button("🚀 Ejecutar Auditoría"):
        try:
            texto_excel = extraer_datos_excel(archivo)
            # Fix 1: "SOLO JSON" para evitar errores de Groq
            extract_prompt = """Extrae SOLO JSON. Si un dato no existe usa null. 
            {"año1": {"ventas":num,"ebitda":num,"activos_corrientes":num,"pasivos_corrientes":num}, 
            "año5": {"ventas":num,"ebitda":num,"activos_totales":num,"pasivos_totales":num,"patrimonio":num,
            "activos_corrientes":num,"pasivos_corrientes":num,"eva":num,"wacc":num,"uodi":num}}"""
            
            res_raw = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user", "content": f"{extract_prompt}\n{texto_excel}"}], response_format={"type":"json_object"})
            d = json.loads(res_raw.choices[0].message.content)
            
            d_a1, d_a5 = d.get('año1', {}), d.get('año5', {})
            m = calcular_metricas_python(d_a1, d_a5)
            status_bal = validar_balance_pro(d_a5)
            
            t1, t2 = st.tabs(["📋 Informe Ejecutivo", "🛡️ Centro de Auditoría"])
            with t1:
                analisis = obtener_analisis_ia(texto_excel, m, client)
                st.markdown(analisis.get('diagnostico'))
                # Feature: Exportar a PDF
                if st.button("📄 Generar Informe PDF"):
                    html = f"<html><body><h1>Informe Finatrix</h1>{analisis.get('diagnostico')}</body></html>"
                    pdf = io.BytesIO()
                    pisa.CreatePDF(io.StringIO(html), dest=pdf)
                    st.download_button("Descargar PDF", pdf.getvalue(), "informe_finatrix.pdf", "application/pdf")
            
            with t2:
                st.metric("Salud Financiera", f"{analisis.get('score', 0)}/100")
                st.write(f"**Validación:** {status_bal}")
                if m['incoherencia']: st.warning("🚨 Alerta: EBITDA > Ventas")
                st.json(m)

            # --- MODO SIMULADOR v6.1 ---
            st.write("---")
            with st.expander("🎮 Simulador de Escenarios y Comparativa"):
                c1, c2, c3 = st.columns(3)
                v_sim = c1.number_input("Ventas Año 5", value=float(d_a5.get('ventas') or 0))
                w_sim = c2.number_input("WACC %", value=float((d_a5.get('wacc') or 0.12)*100)) / 100
                e_sim = c3.number_input("EBITDA Año 5", value=float(d_a5.get('ebitda') or 0))
                
                # Fix 2: Verificación de UODI con is None
                u_base = d_a5.get('uodi')
                u_sim = u_base if u_base is not None else e_sim * 0.7
                
                # Fix 3: Botón deshabilitado si no hay activos para EVA
                if st.button("📊 Recalcular y Guardar", disabled=d_a5.get('activos_totales') is None):
                    eva_sim = u_sim - ((d_a5.get('activos_totales') or 0) * w_sim)
                    if 'escenarios' not in st.session_state: st.session_state.escenarios = []
                    st.session_state.escenarios.append({"Ventas": v_sim, "WACC": f"{w_sim:.1%}", "EVA": round(eva_sim, 2)})
                    st.success("Escenario guardado.")
                
                if 'escenarios' in st.session_state and st.session_state.escenarios:
                    st.write("### Comparativa de Escenarios")
                    st.table(pd.DataFrame(st.session_state.escenarios))

        except Exception as e: st.error(f"Falla crítica: {e}")
