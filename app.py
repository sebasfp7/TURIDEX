import streamlit as st
import pandas as pd
from groq import Groq
import json
import plotly.graph_objects as go

# ==================== CONFIGURACIÓN Y ESTILO ====================
st.set_page_config(page_title="Finatrix Elite Auditor v4.7", layout="wide")

# ==================== NÚCLEO DE CÁLCULO SEGURO ====================
def safe_div(n, d):
    if n is None or d is None or d == 0:
        return None
    return n / d

def calcular_cagr(v_ini, v_fin, periodos=4):
    if v_ini is None or v_fin is None or v_ini <= 0:
        return None
    if v_fin <= 0: return -1.0  
    return (v_fin / v_ini) ** (1 / periodos) - 1

# ==================== FUNCIÓN DE TRAZABILIDAD (EL PORQUÉ) ====================
def generar_memoria_calculo(d1, d5):
    memoria = []
    
    # Crecimiento
    v1, v5 = d1.get('ventas', 0), d5.get('ventas', 0)
    cagr = calcular_cagr(v1, v5)
    txt_cagr = f"{cagr:.2%}" if cagr is not None else "N/A"
    memoria.append(f"📌 **Crecimiento (CAGR):** Basado en Ventas Año 1 (${v1:,.0f}) y Año 5 (${v5:,.0f}). Resultado: {txt_cagr}")

    # Margen EBITDA
    eb5 = d5.get('ebitda', 0)
    m_ebitda = safe_div(eb5, v5)
    txt_margen = f"{m_ebitda:.2%}" if m_ebitda is not None else "N/A"
    memoria.append(f"📌 **Margen EBITDA:** EBITDA (${eb5:,.0f}) / Ventas (${v5:,.0f}). Resultado: {txt_margen}")

    # Punto de Equilibrio
    pe = d5.get('punto_equilibrio_año5', 0)
    cobertura = safe_div(v5, pe)
    txt_cobertura = f"{cobertura:.2f}x" if cobertura is not None else "N/A"
    memoria.append(f"📌 **Cobertura PE:** Ventas (${v5:,.0f}) / Punto Equilibrio (${pe:,.0f}). Cobertura: {txt_cobertura}")

    # EVA
    eva = d5.get('eva', 0)
    memoria.append(f"📌 **EVA:** Valor extraído de la hoja WACC-EVA. Resultado: ${eva:,.0f}")
    
    return memoria

# ==================== MOTOR DE INSIGHTS (v4.2 ORIGINAL) ====================
def generar_analisis_consultoria(d_a1, d_a5):
    criticos, importantes, info = [], [], []
    cagr = calcular_cagr(d_a1.get('ventas'), d_a5.get('ventas'))
    m_ebitda = safe_div(d_a5.get('ebitda'), d_a5.get('ventas'))
    
    if cagr is not None and cagr > 0.20:
        if m_ebitda is not None and m_ebitda < 0.10:
            criticos.append("🔥 Crecimiento Peligroso: Ventas suben >20% pero el margen es bajo. Riesgo de insolvencia.")
        else:
            importantes.append("🚀 Crecimiento Sostenible: Expansión fuerte con márgenes saludables.")
    
    pe_ratio = safe_div(d_a5.get('ventas'), d_a5.get('punto_equilibrio_año5'))
    if pe_ratio is not None and pe_ratio < 1.1:
        criticos.append("⚠️ Riesgo Operativo: Ventas muy cerca del Punto de Equilibrio.")

    if d_a5.get('eva') is not None and d_a5['eva'] < 0:
        criticos.append("❌ Destrucción de Valor: El EVA es negativo.")

    return criticos, importantes, info

# ==================== EXTRACCIÓN Y UI ====================
def extraer_datos_excel(archivo):
    xls = pd.ExcelFile(archivo)
    texto = ""
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet).fillna('').head(40)
        texto += f"\n### HOJA: {sheet} ###\n{df.to_markdown(index=False)}\n"
    return texto[:26000]

st.sidebar.header("⚙️ Finatrix Elite v4.7")
api_key = st.sidebar.text_input("Groq API Key", type="password")
archivo = st.sidebar.file_uploader("Subir Plantilla", type=["xlsx"])

if archivo and api_key:
    client = Groq(api_key=api_key)
    if st.button("🚀 Ejecutar Auditoría"):
        try:
            texto_excel = extraer_datos_excel(archivo)
            prompt = f"""
            Eres un Socio de Consultoría. Extrae Año 1 y Año 5. 
            Devuelve SOLO JSON:
            {{
              "año1": {{"ventas": num, "ebitda": num}},
              "año5": {{"ventas": num, "ebitda": num, "punto_equilibrio_año5": num, "eva": num}}
            }}
            DATOS: {texto_excel}
            """
            chat = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            datos = json.loads(chat.choices[0].message.content)
            d1, d5 = datos['año1'], datos['año5']

            # --- RENDERIZADO DE RESULTADOS ---
            t1, t2 = st.tabs(["💡 Informe", "🔍 El Porqué (Cálculos)"])
            
            with t1:
                crit, imp, inf = generar_analisis_consultoria(d1, d5)
                for c in crit: st.error(c)
                for i in imp: st.warning(i)
                for f in inf: st.info(f)
                
                fig = go.Figure()
                fig.add_trace(go.Bar(name='Ventas', x=['A1', 'A5'], y=[d1.get('ventas'), d5.get('ventas')]))
                fig.add_trace(go.Bar(name='EBITDA', x=['A1', 'A5'], y=[d1.get('ebitda'), d5.get('ebitda')]))
                st.plotly_chart(fig, use_container_width=True)

            with t2:
                st.subheader("Memoria de Cálculo de Auditoría")
                for linea in generar_memoria_calculo(d1, d5):
                    st.info(linea)

        except Exception as e:
            st.error(f"Error técnico: {e}")
