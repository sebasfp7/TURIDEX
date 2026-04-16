import streamlit as st
from groq import Groq
import json

# 1. CONFIGURACIÓN DE MODELOS (Solución al problema que detectaste)
MODEL_VISION = "meta-llama/llama-4-scout-17b-16e-instruct" # Solo para ver la imagen
MODEL_TEXT = "meta-llama/llama-3.3-70b-versatile"         # Para razonar el diagnóstico

# Conectamos con el servicio (Usaremos Groq que es ultra rápido y tiene planes gratis)
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

st.set_page_config(page_title="Finatrix AI", layout="wide")
st.title("🚀 Finatrix: Inteligencia Financiera")

# --- INTERFAZ DE USUARIO ---
archivo = st.file_uploader("Sube una foto o PDF de un Balance o Estado de Resultados", type=["png", "jpg", "jpeg", "pdf"])

if archivo:
    st.info("Procesando documento... Por favor espera.")
    
    # Convertimos la imagen para que la IA la pueda "ver"
    bytes_data = archivo.getvalue()
    
    # --- PASO 1: OCR + EXTRACCIÓN (Usando el modelo VISION) ---
    # Aquí Scout extrae los números fríos
    prompt_ocr = "Extrae los datos financieros clave: Ingresos, Costos, Gastos, Activos y Pasivos. Responde solo en JSON."
    
    # (Simulación de llamada para el ejemplo, aquí iría la lógica de envío de imagen)
    # res1 = client.chat.completions.create(model=MODEL_VISION, ...)
    
    datos_extraidos = {"ingresos": 10000, "costos": 4000, "gastos": 2000} # Ejemplo
    
    st.success("✅ Datos extraídos correctamente.")
    st.json(datos_extraidos)

    # --- PASO 2: DIAGNÓSTICO (Usando el modelo TEXT-ONLY) ---
    # Aquí el modelo más potente y rápido analiza qué significan esos números
    if st.button("Generar Diagnóstico"):
        prompt_analisis = f"Basado en estos datos: {datos_extraidos}, dime: ¿La empresa es rentable? ¿Qué riesgos ves?"
        
        # Esta llamada es más barata y rápida por ser solo texto
        respuesta_final = client.chat.completions.create(
            model=MODEL_TEXT,
            messages=[{"role": "user", "content": prompt_analisis}]
        )
        
        st.subheader("Análisis Estratégico")
        st.write(respuesta_final.choices[0].message.content)
