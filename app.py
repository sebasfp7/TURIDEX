import streamlit as st
from groq import Groq
import PIL.Image
import base64
from gtts import gTTS
import io
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="TURIDEX", layout="wide")

st.markdown("""
<style>
    .stApp {
        background-image: url('https://vignette.wikia.nocookie.net/es.pokemon/images/c/c1/Mapa_de_Kanto_GSC.png/revision/latest?cb=20191215132219');
        background-size: cover; background-position: center; background-attachment: fixed;
    }
    .pokedex-frame {
        background-color: rgba(255, 255, 255, 0.95);
        border: 4px solid #DC0A2D;
        border-radius: 20px;
        padding: 25px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
    }
    
    /* HEADER UNIFICADO - SOLO CUADRO NEGRO CON TÍTULO */
    .pokedex-title-box {
        background-color: #000000;
        border: 4px solid #DC0A2D;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        margin-bottom: 20px;
    }
    .pokedex-title { 
        color: #FFDE00 !important; 
        font-family: 'Courier New', monospace; 
        font-size: 3.5em; 
        margin: 0;
        text-shadow: 3px 3px 0px #DC0A2D, 
                     -1px -1px 0px #DC0A2D,  
                     1px -1px 0px #DC0A2D,
                     -1px 1px 0px #DC0A2D,
                     1px 1px 0px #DC0A2D;
        letter-spacing: 5px;
    }
    
    /* INDICADOR DE ESTADO */
    .status-indicator {
        background-color: rgba(0, 0, 0, 0.8);
        color: #00FF00;
        padding: 8px 15px;
        border-radius: 5px;
        text-align: center;
        font-family: 'Courier New', monospace;
        font-size: 0.9em;
        margin-top: 10px;
        border: 2px solid #00FF00;
    }
    
    /* TEXTO CON MÁXIMA LEGIBILIDAD */
    .black-text, p, h1, h2, h3, span, label, div { 
        color: #000000 !important; 
        font-weight: 600;
        text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8),
                     -1px -1px 2px rgba(255, 255, 255, 0.8);
    }
    
    .data-card {
        background-color: rgba(255, 255, 255, 0.92);
        border-left: 5px solid #DC0A2D;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
        box-shadow: 2px 2px 8px rgba(0, 0, 0, 0.3);
    }
    
    .historia-box {
        background-color: rgba(255, 255, 255, 0.92);
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
        box-shadow: 2px 2px 8px rgba(0, 0, 0, 0.3);
    }
    
    .evo-tag {
        background-color: #FFCC00;
        color: black !important;
        padding: 8px 16px;
        border-radius: 15px;
        font-weight: bold;
        display: inline-block;
        margin: 5px;
        border: 2px solid #000;
        box-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# HEADER ÚNICO CON TÍTULO
st.markdown("<div class='pokedex-title-box'><h1 class='pokedex-title'>⚡ TURIDEX ⚡</h1></div>", unsafe_allow_html=True)

try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Error: Configura la API KEY.")

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

def sanitizar_texto(texto):
    """Función de limpieza: elimina símbolos, duplicados y formatea"""
    # Elimina símbolos especiales
    texto = re.sub(r'[*#_\[\]]', '', texto)
    # Elimina saltos de línea múltiples
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    return texto.strip()

def extraer_dato(tag, texto):
    """Extracción única y limpia de datos - PRIMERA APARICIÓN SOLAMENTE"""
    patron = rf"{tag}:\s*(.*?)(?=\n(?:NOMBRE|CATEGORIA|DESC|HISTORIA|STATS|EVOS):|$)"
    matches = re.findall(patron, texto, re.S | re.I)
    
    if matches:
        # TOMA SOLO LA PRIMERA APARICIÓN
        contenido = matches[0].strip()
        return sanitizar_texto(contenido)
    return "Dato no disponible"

with st.container():
    st.markdown("<div class='pokedex-frame'>", unsafe_allow_html=True)
    
    # Indicador de estado
    estado_placeholder = st.empty()
    estado_placeholder.markdown("<div class='status-indicator'>⏳ Esperando objetivo...</div>", unsafe_allow_html=True)
    
    col_img, col_info = st.columns([1, 2])
    
    with col_img:
        archivo = st.file_uploader("", type=["jpg", "png", "jpeg"])
        if archivo:
            st.image(PIL.Image.open(archivo), use_container_width=True)
            analizar = st.button("🔍 ESCANEAR OBJETIVO")

    if archivo and analizar:
        estado_placeholder.markdown("<div class='status-indicator'>🔄 Analizando datos...</div>", unsafe_allow_html=True)
        
        with st.spinner("Procesando..."):
            try:
                img_b64 = encode_image(archivo)
                
                # ========================================
                # 🎯 PROMPT DEFINITIVO V2.0
                # ========================================
                prompt = """Eres TURIDEX, sistema avanzado de identificación. Sigue estas instrucciones AL PIE DE LA LETRA.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 FASE 1: IDENTIFICACIÓN PRECISA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Observa la imagen y clasifica en UNA de estas categorías:

🍕 COMIDA: Cualquier alimento, bebida o plato culinario
   Ejemplos: Pizza, Salchipapa, Ceviche, Sushi, Café
   Indicadores: Platos, ingredientes visibles, comida preparada

🦁 ANIMAL: Cualquier ser vivo del reino animal
   Ejemplos: León, Perro, Águila, Delfín, Mariposa
   Indicadores: Ojos, pelaje/plumas/escamas, movimiento

🏛️ LUGAR: Monumentos, ciudades, paisajes, edificios
   Ejemplos: Machu Picchu, Torre Eiffel, Gran Cañón
   Indicadores: Arquitectura, geografía, construcciones

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 FASE 2: ASIGNACIÓN DE ESTADÍSTICAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IMPORTANTE: Los STATS cambian según la categoría detectada.

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ SI DETECTASTE: COMIDA                  ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ STATS (valores 0-100):                 ┃
┃ • Sabor: Qué tan delicioso es         ┃
┃ • Picante: Nivel de ají/chile         ┃
┃ • Salud: Valor nutricional            ┃
┃   (Comida frita/chatarra = 5-15)      ┃
┃ • Rareza: Dificultad para encontrar   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ SI DETECTASTE: ANIMAL                  ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ STATS (valores 0-100):                 ┃
┃ • Fuerza: Poder físico                ┃
┃ • Agilidad: Velocidad y reflejos      ┃
┃ • Peligro: Amenaza para humanos       ┃
┃ • Rareza: Estado de conservación      ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ SI DETECTASTE: LUGAR                   ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ STATS (valores 0-100):                 ┃
┃ • Historia: Antigüedad e importancia  ┃
┃ • Belleza: Atractivo visual           ┃
┃ • Cultura: Relevancia cultural        ┃
┃ • Rareza: Exclusividad/acceso         ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 FASE 3: VARIANTES (EVOLUCIONES)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ REGLA CRÍTICA: Las variantes DEBEN ser SUSTANTIVOS del mismo tipo.

✅ CORRECTO:
• COMIDA: Salchipapa → Papas fritas, Hot dog, Choripán
• ANIMAL: León → Tigre, Leopardo, Jaguar
• LUGAR: Machu Picchu → Chichén Itzá, Petra, Angkor Wat

❌ INCORRECTO:
• NO uses adjetivos: "Fuerte", "Delicioso", "Antiguo"
• NO mezcles categorías: Pizza → Perro, Torre Eiffel
• NO uses frases: "Muy sabroso", "El más grande"

Proporciona EXACTAMENTE 3 variantes como sustantivos simples.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 FORMATO DE RESPUESTA (COPIA EXACTO)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NOMBRE: [Nombre del elemento]
CATEGORIA: [Escribe solo: COMIDA, ANIMAL o LUGAR]
DESC: [Una frase de máximo 15 palabras]
HISTORIA: [Escribe 2 párrafos. Párrafo 1: Origen e historia. Párrafo 2: Importancia actual. Total: 100-150 palabras]
STATS: [num1, num2, num3, num4]
EVOS: [Sustantivo1, Sustantivo2, Sustantivo3]

⚠️ PROHIBIDO:
• Usar asteriscos *, hashtags #, corchetes []
• Repetir secciones
• Incluir explicaciones adicionales
• Usar adjetivos en EVOS

Analiza la imagen AHORA:"""

                # ========================================
                # Llamada a la IA con configuración óptima
                # ========================================
                chat = client.chat.completions.create(
                    messages=[{
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": prompt}, 
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                        ]
                    }],
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                    temperature=0.05,
                    max_tokens=1200
                )
                
                respuesta_cruda = chat.choices[0].message.content

                # ========================================
                # EXTRACCIÓN SANITIZADA (UNA SOLA VEZ)
                # ========================================
                nombre = extraer_dato("NOMBRE", respuesta_cruda)
                categoria = extraer_dato("CATEGORIA", respuesta_cruda).upper()
                descripcion = extraer_dato("DESC", respuesta_cruda)
                historia = extraer_dato("HISTORIA", respuesta_cruda)
                stats_raw = extraer_dato("STATS", respuesta_cruda)
                evos_raw = extraer_dato("EVOS", respuesta_cruda)
                
                # Procesar números de stats
                numeros = [int(n) for n in re.findall(r'\d+', stats_raw)][:4]
                while len(numeros) < 4: 
                    numeros.append(0)
                numeros = [min(100, max(0, n)) for n in numeros]

                # ========================================
                # INTERRUPTOR DE ETIQUETAS (LABEL SWITCHER)
                # ========================================
                if "ANIMAL" in categoria:
                    etiquetas = ["🐾 Fuerza", "⚡ Agilidad", "⚠️ Peligro", "💎 Rareza"]
                elif "LUGAR" in categoria:
                    etiquetas = ["🏛️ Historia", "📸 Belleza", "🌍 Cultura", "💎 Rareza"]
                else:  # COMIDA por defecto
                    categoria = "COMIDA"  # Forzar categoría si no está clara
                    etiquetas = ["😋 Sabor", "🌶️ Picante", "🥗 Salud", "💎 Rareza"]

                # ========================================
                # RENDERIZADO ÚNICO (SIN DUPLICADOS)
                # ========================================
                with col_info:
                    # Título
                    st.markdown(f"## 📋 {nombre}")
                    
                    # Categoría y descripción
                    st.markdown(f"<div class='data-card'><p><b>CATEGORÍA:</b> {categoria}</p><p>{descripcion}</p></div>", unsafe_allow_html=True)
                    
                    # Historia con fondo
                    st.markdown("### 📖 Historia")
                    st.markdown(f"<div class='historia-box'><p>{historia}</p></div>", unsafe_allow_html=True)
                    
                    # Stats con etiquetas correctas
                    st.markdown("### 📊 Puntos Base")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"<p>{etiquetas[0]}: {numeros[0]}%</p>", unsafe_allow_html=True)
                        st.progress(numeros[0]/100)
                        st.markdown(f"<p>{etiquetas[1]}: {numeros[1]}%</p>", unsafe_allow_html=True)
                        st.progress(numeros[1]/100)
                    with c2:
                        st.markdown(f"<p>{etiquetas[2]}: {numeros[2]}%</p>", unsafe_allow_html=True)
                        st.progress(numeros[2]/100)
                        st.markdown(f"<p>{etiquetas[3]}: {numeros[3]}%</p>", unsafe_allow_html=True)
                        st.progress(numeros[3]/100)

                    # Variantes filtradas (solo sustantivos)
                    st.markdown("### 🔄 Variantes Registradas")
                    variantes = [v.strip() for v in evos_raw.split(",") if v.strip() and len(v.strip()) > 2]
                    for var in variantes[:3]:
                        st.markdown(f"<span class='evo-tag'>{var}</span>", unsafe_allow_html=True)

                # Audio
                texto_audio = f"{nombre}. {descripcion}. {historia[:180]}"
                texto_audio = sanitizar_texto(texto_audio)
                tts = gTTS(text=texto_audio, lang='es')
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                st.audio(fp)
                
                # Actualizar estado a completado
                estado_placeholder.markdown("<div class='status-indicator'>✅ Escaneo completado</div>", unsafe_allow_html=True)

            except Exception as e:
                estado_placeholder.markdown("<div class='status-indicator'>❌ Error en escaneo</div>", unsafe_allow_html=True)
                st.error(f"⚠️ Error: {str(e)}")
                
    st.markdown("</div>", unsafe_allow_html=True)
