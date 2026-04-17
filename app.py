import streamlit as st
import pandas as pd
from groq import Groq
import json
import plotly.graph_objects as go

# ==================== CONFIGURACIÓN Y ESTILO ====================
st.set_page_config(page_title="Finatrix Elite Auditor v4.7", layout="wide")

# ==================== NÚCLEO DE CÁLCULO CON EXPLICACIÓN ====================
def safe_div(n, d):
    if n is None or d is None or d == 0:
        return None
    return n / d

# Nueva función para rastrear el origen de la lógica
def generar_memoria_calculo(d1, d5):
    memoria = []
    
    # Explicación de Ventas y Crecimiento
    v1, v5 = d1.get('ventas', 0), d5.get('ventas', 0)
    cagr = (((v5/v1)**(1/4))-1) if v1 > 0 else 0
    memoria.append(f"📌 **Crecimiento (CAGR):** Calculado usando Ventas Año 1 (${v1:,.0f}) y Año 5 (${v5:,.0f}). Fórmula: ((V5/V1)^(1/4))-1 = {cagr:.2%}")

    # Explicación de EBITDA
    eb5 = d5.get('ebitda', 0)
    m_ebitda = safe_div(eb5, v5)
    memoria.append(f"📌 **Margen EBITDA:** Se tomó el EBITDA (${eb5:,.0f}) sobre las Ventas (${v5:,.0f}). Resultado: {m_ebitda:.2% if m_ebitda else 'N/A'}")

    # Explicación de Punto de Equilibrio
    pe = d5.get('punto_equilibrio_año5', 0)
    cobertura = safe_div(v5, pe)
    memoria.append(f"📌 **Punto de Equilibrio:** Ventas (${v5:,.0f}) / Pto. Equilibrio (${pe:,.0f}). La empresa vende {cobertura:.2f}x veces lo mínimo necesario.")

    # Explicación de EVA
    eva = d5.get('eva', 0)
    memoria.append(f"📌 **EVA (Valor Económico):** Dato extraído directamente de la hoja 'WACC-EVA'. Valor: ${eva:,.0f}")
    
    return memoria

# ==================== MOTOR DE INSIGHTS (v4.2 ORIGINAL) ====================
def generar_analisis_consultoria(d_a1, d_a5):
    criticos, importantes, info = [], [], []
    cagr = (((d_a5.get('ventas',0)/d_a1.get('ventas',1))**(1/4))-1)
    m_ebitda = safe_div(d_a5.get('ebitda'), d_a5.get('ventas'))
    
    if cagr > 0.20:
        if m_ebitda is not None and m_ebitda < 0.10:
            criticos.append("🔥 Crecimiento Peligroso: Ventas suben rápido pero el margen es bajo. Riesgo de insolvencia.")
        else:
            importantes.append("🚀 Crecimiento Sostenible: Expansión fuerte con márgenes saludables.")
    
    gao = d_a5.get('gao')
    pe_ratio = safe_div(d_a5.get('ventas'), d_a5.get('punto_equilibrio_año5'))
    
    if gao is not None and gao > 4 and pe_ratio is not None and pe_ratio < 1.2:
        criticos.append("⚠️ Vulnerabilidad Extrema: Alto GAO y ventas cerca del Punto de Equilibrio.")

    eva = d_a5.get('eva')
    if eva is not None:
        if eva < 0: criticos.append("❌ Destrucción de Valor: El EVA es negativo.")
        else: info.append("🟢 Generación de Valor detectada.")

    return criticos, importantes, info

# ==================== EXTRACCIÓN (v4.2 ORIGINAL) ====================
def extraer_datos_excel(archivo):
    xls = pd.ExcelFile(archivo)
    texto_contexto = ""
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet).fillna('').head(40)
        texto_contexto += f"\n### HOJA: {sheet} ###\n{df.to_markdown(index=False)}\n"
    return texto_contexto[:26000]

# ==================== UI STREAMLIT ====================
st.sidebar.header("⚙️ Configuración")
api_key = st.sidebar.text_input("Groq API Key", type="password")
archivo = st.sidebar.file_uploader("Subir Plantilla", type=["xlsx"])

if archivo and api_key:
    client = Groq(api_key=api_key)
    if st.button("🚀 Ejecutar Auditoría"):
        with st.spinner("Analizando..."):
            texto_excel = extraer_datos_excel(archivo)
            prompt = f"""
            Eres un Socio de Consultoría. Extrae Año 1 y Año 5. 
            Devuelve SOLO JSON puro:
            {{
              "año1": {{"ventas": num, "ebitda": num}},
              "año5": {{"ventas": num, "ebitda": num, "punto_equilibrio_año5": num, "eva": num, "gao": num}}
            }}
            DATOS: {texto_excel}
            """
            try:
                chat = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                datos = json.loads(chat.choices[0].message.content)
                d1, d5 = datos['año1'], datos['año5']

                # --- DISEÑO DE RESPUESTA EN TABS ---
                st.subheader("📊 Resultados de la Auditoría")
                t_diag, t_mem = st.tabs(["💡 Diagnóstico Estratégico", "🔍 Memoria de Cálculo (El Porqué)"])
                
                with t_diag:
                    crit, imp, inf = generar_analisis_consultoria(d1, d5)
                    for c in crit: st.error(c)
                    for i in imp: st.warning(i)
                    for f in inf: st.info(f)
                    
                    # Gráfico original
                    fig = go.Figure()
                    fig.add_trace(go.Bar(name='Ventas', x=['A1', 'A5'], y=[d1.get('ventas'), d5.get('ventas')]))
                    fig.add_trace(go.Bar(name='EBITDA', x=['A1', 'A5'], y=[d1.get('ebitda'), d5.get('ebitda')]))
                    st.plotly_chart(fig, use_container_width=True)

                with t_mem:
                    st.write("### Trazabilidad de los Números")
                    memoria = generar_memoria_calculo(d1, d5)
                    for linea in memoria:
                        st.write(linea)
                    st.success("Nota: Los datos fueron extraídos mediante procesamiento de lenguaje natural de las hojas correspondientes.")

            except Exception as e:
                st.error(f"Error: {e}")
else:
    st.info("Configura los accesos para comenzar.")
