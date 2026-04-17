import streamlit as st
import pandas as pd
from groq import Groq
import google.generativeai as genai
import requests
import json
import pdfplumber
import re

# ==================== 1. MOTOR DE LIMPIEZA (EVITA EL FALLO TOTAL) ====================
def limpiar_json(texto):
    """Extrae el contenido JSON de una respuesta de texto para evitar errores de formato."""
    try:
        match = re.search(r'\{.*\}', texto, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return json.loads(texto)
    except:
        return None

# ==================== 2. LLAMADAS A LOS MOTORES ====================
def motor_groq(key, prompt):
    client = Groq(api_key=key)
    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role":"user", "content":prompt}],
        response_format={"type":"json_object"}
    )
    return json.loads(res.choices[0].message.content)

def motor_gemini(key, prompt):
    genai.configure(api_key=key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    res = model.generate_content(prompt)
    return limpiar_json(res.text)

def motor_openrouter(key, prompt):
    res = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        data=json.dumps({
            "model": "deepseek/deepseek-chat",
            "messages": [{"role": "user", "content": prompt}]
        })
    )
    return limpiar_json(res.json()['choices'][0]['message']['content'])

# ==================== 3. INTERFAZ Y RECOLECCIÓN DE DATOS ====================
st.set_page_config(page_title="Finatrix Fortress Final", layout="wide")
st.title("🛡️ Finatrix Elite | CFO Virtual")

archivo = st.file_uploader("Subir Estados Financieros", type=["pdf"])

if archivo and st.button("🚀 Iniciar Gran Auditoría"):
    with st.spinner("Ejecutando motores de respaldo..."):
        with pdfplumber.open(archivo) as pdf:
            raw_text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])[:12000]

        prompt_maestro = f"""Actúa como CFO Senior. Analiza estos datos: {raw_text}
        DEBES RESPONDER ÚNICAMENTE EN FORMATO JSON:
        {{
          "m": {{ "score": 85, "eva": 1000, "wacc": 0.12 }},
          "resumen_ejecutivo": "...",
          "diagnostico_pilares": {{ "rentabilidad": "...", "liquidez": "...", "solvencia": "...", "creacion_valor": "..." }},
          "semaforo": {{ "verde": [], "amarillo": [], "rojo": [] }},
          "plan_90_dias": {{ "t30": "...", "t60": "...", "t90": "..." }}
        }}"""

        data = None
        # Lista de motores configurados en Secrets
        motores = [
            ("Groq", st.secrets.get("GROQ_KEY"), motor_groq),
            ("Gemini", st.secrets.get("GEMINI_KEY"), motor_gemini),
            ("OpenRouter", st.secrets.get("OPENROUTER_KEY"), motor_openrouter)
        ]

        for nombre, key, funcion in motores:
            if key and not data:
                try:
                    data = funcion(key, prompt_maestro)
                    if data:
                        st.success(f"✅ Informe generado con {nombre}")
                        break
                except Exception as e:
                    st.warning(f"⚠️ {nombre} no disponible.")

        if data:
            # --- DISEÑO DE INFORME COMPLETO ---
            m = data.get('m', {})
            c1, c2, c3 = st.columns(3)
            c1.metric("Salud Estratégica", f"{m.get('score', 0)}/100")
            c2.metric("EVA (Creación de Valor)", f"${m.get('eva', 0):,.0f}")
            c3.metric("WACC (Costo Capital)", f"{m.get('wacc', 0):.2%}")

            st.write("---")
            st.subheader("📋 Resumen Ejecutivo")
            st.info(data.get('resumen_ejecutivo', ''))

            st.write("---")
            st.subheader("🔬 Diagnóstico por Pilares")
            diag = data.get('diagnostico_pilares', {})
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**📈 Rentabilidad:**\n{diag.get('rentabilidad')}")
                st.markdown(f"**💧 Liquidez:**\n{diag.get('liquidez')}")
            with col_b:
                st.markdown(f"**🏗️ Solvencia:**\n{diag.get('solvencia')}")
                st.markdown(f"**💎 Creación de Valor:**\n{diag.get('creacion_valor')}")

            st.write("---")
            st.subheader("🚦 Semáforo Directivo")
            sem = data.get('semaforo', {})
            cs1, cs2, cs3 = st.columns(3)
            cs1.success("**VERDE**\n\n" + "\n".join([f"• {x}" for x in sem.get('verde', [])]))
            cs2.warning("**AMARILLO**\n\n" + "\n".join([f"• {x}" for x in sem.get('amarillo', [])]))
            cs3.error("**ROJO**\n\n" + "\n".join([f"• {x}" for x in sem.get('rojo', [])]))

            st.write("---")
            st.subheader("🎯 Plan de Acción 90 Días")
            plan = data.get('plan_90_dias', {})
            t1, t2, t3 = st.tabs(["30 Días", "60 Días", "90 Días"])
            t1.markdown(plan.get('t30'))
            t2.markdown(plan.get('t60'))
            t3.markdown(plan.get('t90'))
        else:
            st.error("No se pudo obtener el análisis. Revisa que las Keys en Secrets sean correctas.")
