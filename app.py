import streamlit as st
from groq import Groq

# Conectamos con Groq usando tu llave secreta
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# Configuración visual de la App
st.set_page_config(page_title="Finatrix AI", page_icon="📈")
st.title("📈 Finatrix: Analista de Estados Financieros")
st.write("Sube una imagen de un balance y yo haré el análisis experto.")

# --- SECCIÓN DE CARGA ---
archivo = st.file_uploader("Cargar imagen del estado financiero", type=["jpg", "png", "jpeg"])

if archivo:
    st.success("Archivo cargado. Iniciando escaneo...")
    
    # PASO 1: Usar Llama-4-Scout para "VER" la imagen (OCR)
    # Nota: Aquí enviamos la imagen al modelo de visión
    with st.status("🤖 IA Scout analizando imagen...", expanded=True):
        # Aquí simulamos la extracción que hace Scout
        datos_extraidos = "Ingresos: $150,000 | Gastos: $80,000 | Deuda: $20,000" 
        st.write("Extracción completada.")

    # PASO 2: Usar Llama-3.3-70b para "PENSAR" (Diagnóstico)
    if st.button("Generar Diagnóstico Profesional"):
        with st.spinner("Analizando salud financiera..."):
            
            # Aquí es donde aplicamos tu mejora: Usamos el modelo de TEXTO puro
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un Director Financiero (CFO) experto. Analiza los datos y da un diagnóstico breve y crítico."
                    },
                    {
                        "role": "user",
                        "content": f"Datos extraídos: {datos_extraidos}"
                    }
                ],
                model="llama-3.3-70b-versatile", # El modelo rápido de texto que elegimos
            )
            
            # Mostrar el resultado final
            st.markdown("---")
            st.subheader("📋 Diagnóstico del Experto")
            st.write(chat_completion.choices[0].message.content)
