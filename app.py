import streamlit as st
from groq import Groq
import PIL.Image
import base64
from gtts import gTTS
import io
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="TURIDEX", layout="wide")

# --- INICIALIZACIÓN DE SESSION STATE ---
if 'historial_ruta' not in st.session_state:
    st.session_state.historial_ruta = []
if 'variante_seleccionada' not in st.session_state:
    st.session_state.variante_seleccionada = None
if 'categoria_actual' not in st.session_state:
    st.session_state.categoria_actual = None

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
    
    /* HEADER PRINCIPAL CON EFECTO GLOW */
    .pokedex-title-box {
        background-color: #000000;
        border: 4px solid #DC0A2D;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        margin-bottom: 15px;
    }
    .pokedex-title { 
        color: #FFDE00 !important; 
        font-family: 'Courier New', monospace; 
        font-size: 3.5em; 
        margin: 0;
        text-shadow: 0 0 10px #FFDE00,
                     0 0 20px #FFDE00,
                     0 0 30px #FF0000,
                     3px 3px 0px #DC0A2D;
        letter-spacing: 5px;
        animation: glow 2s ease-in-out infinite alternate;
    }
    
    @keyframes glow {
        from { text-shadow: 0 0 10px #FFDE00, 0 0 20px #FFDE00, 0 0 30px #FF0000; }
        to { text-shadow: 0 0 20px #FFDE00, 0 0 30px #FFDE00, 0 0 40px #FF0000; }
    }
    
    /* BARRA DE RUTA (BREADCRUMB) */
    .breadcrumb-box {
        background-color: rgba(255, 255, 255, 0.95);
        border: 3px solid #DC0A2D;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 20px;
        text-align: center;
        font-family: 'Courier New', monospace;
        font-size: 1.1em;
        color: #000000;
        font-weight: bold;
    }
    .breadcrumb-arrow {
        color: #DC0A2D;
        margin: 0 8px;
    }
    
    /* ESTADO DEL ESCÁNER */
    .status-indicator {
        background-color: rgba(0, 0, 0, 0.85);
        color: #00FF00;
        padding: 10px 15px;
        border-radius: 5px;
        text-align: center;
        font-family: 'Courier New', monospace;
        font-size: 1em;
        margin-bottom: 15px;
        border: 2px solid #00FF00;
        animation: blink 1.5s ease-in-out infinite;
    }
    
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
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
    
    /* BOTONES DE VARIANTES INTERACTIVOS */
    .stButton > button {
        background-color: #FFCC00 !important;
        color: black !important;
        padding: 12px 20px !important;
        border-radius: 15px !important;
        font-weight: bold !important;
        border: 2px solid #000 !important;
        box-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3) !important;
        width: 100% !important;
        margin: 5px 0 !important;
        transition: all 0.3s ease !important;
        font-size: 1.1em !important;
    }
    
    .stButton > button:hover {
        background-color: #FFD700 !important;
        transform: translateY(-3px) !important;
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.4) !important;
        border: 2px solid #DC0A2D !important;
    }
    
    .stButton > button:active {
        transform: translateY(0px) !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3) !important;
    }
</style>
""", unsafe_allow_html=True)

# HEADER CON ANIMACIÓN
st.markdown("<div class='pokedex-title-box'><h1 class='pokedex-title'>⚡ TURIDEX ⚡</h1></div>", unsafe_allow_html=True)

# BARRA DE RUTA (BREADCRUMB)
if st.session_state.historial_ruta:
    ruta_texto = " <span class='breadcrumb-arrow'>→</span> ".join(st.session_state.historial_ruta)
    st.markdown(f"<div class='breadcrumb-box'>📍 Ruta: {ruta_texto}</div>", unsafe_allow_html=True)

try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Error: Configura la API KEY.")

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

def sanitizar_texto(texto):
    """Función de limpieza: elimina símbolos, duplicados y formatea"""
    texto = re.sub(r'[*#_\[\]]', '', texto)
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    return texto.strip()

def extraer_dato(tag, texto):
    """Extracción única y limpia de datos - PRIMERA APARICIÓN SOLAMENTE"""
    patron = rf"{tag}:\s*(.*?)(?=\n(?:NOMBRE|CATEGORIA|DESC|HISTORIA|STATS|EVOS):|$)"
    matches = re.findall(patron, texto, re.S | re.I)
    
    if matches:
        contenido = matches[0].strip()
        return sanitizar_texto(contenido)
    return "Dato no disponible"

def consultar_ia(prompt_texto, imagen_b64=None):
    """Función unificada para consultar la IA con o sin imagen"""
    
    if imagen_b64:
        # Consulta con imagen
        messages = [{
            "role": "user", 
            "content": [
                {"type": "text", "text": prompt_texto}, 
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{imagen_b64}"}}
            ]
        }]
    else:
        # Consulta solo texto
        messages = [{"role": "user", "content": prompt_texto}]
    
    chat = client.chat.completions.create(
        messages=messages,
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        temperature=0.05,
        max_tokens=1200
    )
    
    return chat.choices[0].message.content

def obtener_prompt_base(nombre_elemento=None):
    """Genera el prompt base. Si recibe un nombre, lo busca por texto"""
    
    if nombre_elemento:
        # PROMPT PARA BÚSQUEDA POR TEXTO (cuando se pulsa una variante)
        return f"""Eres TURIDEX. El usuario quiere información sobre: {nombre_elemento}

⚠️ IMPORTANTE: Mantén la misma categoría que el elemento anterior.
- Si venías de COMIDA, este también debe ser COMIDA
- Si venías de ANIMAL, este también debe ser ANIMAL
- Si venías de LUGAR, este también debe ser LUGAR

Proporciona la información completa siguiendo EXACTAMENTE este formato:

NOMBRE: {nombre_elemento}
CATEGORIA: [Usa la misma categoría del contexto anterior]
DESC: [Descripción breve en máximo 15 palabras]
HISTORIA: [Dos párrafos: 1) Origen e historia 2) Importancia actual. Total 100-150 palabras]
STATS: [num1, num2, num3, num4]
EVOS: [Variante1, Variante2, Variante3]

REGLAS PARA STATS según categoría:
- COMIDA: Sabor, Picante, Salud, Rareza (comida frita tiene Salud 5-15)
- ANIMAL: Fuerza, Agilidad, Peligro, Rareza
- LUGAR: Historia, Belleza, Cultura, Rareza

REGLAS PARA EVOS:
✅ SOLO sustantivos del mismo tipo
✅ EXACTAMENTE 3 variantes
❌ NO adjetivos ni frases

Responde AHORA:"""
    
    else:
        # PROMPT PARA ANÁLISIS DE IMAGEN (escaneo inicial)
        return """Eres TURIDEX, sistema avanzado de identificación. Sigue estas instrucciones AL PIE DE LA LETRA.

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

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ SI DETECTASTE: COMIDA                  ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ STATS: Sabor, Picante, Salud, Rareza  ┃
┃ (Comida frita/chatarra: Salud 5-15)   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ SI DETECTASTE: ANIMAL                  ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ STATS: Fuerza, Agilidad, Peligro, Rareza ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ SI DETECTASTE: LUGAR                   ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ STATS: Historia, Belleza, Cultura, Rareza ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 FASE 3: VARIANTES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ CORRECTO:
• COMIDA: Salchipapa → Papas fritas, Hot dog, Choripán
• ANIMAL: León → Tigre, Leopardo, Jaguar
• LUGAR: Machu Picchu → Chichén Itzá, Petra, Angkor Wat

❌ INCORRECTO:
• Adjetivos: "Fuerte", "Delicioso"
• Mezclar categorías
• Frases largas

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 FORMATO DE RESPUESTA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NOMBRE: [Nombre]
CATEGORIA: [COMIDA/ANIMAL/LUGAR]
DESC: [Máximo 15 palabras]
HISTORIA: [2 párrafos, 100-150 palabras total]
STATS: [num1, num2, num3, num4]
EVOS: [Variante1, Variante2, Variante3]

⚠️ PROHIBIDO: *, #, [], repeticiones

Analiza AHORA:"""

def procesar_respuesta(respuesta_ia):
    """Procesa la respuesta de la IA y devuelve datos estructurados"""
    
    nombre = extraer_dato("NOMBRE", respuesta_ia)
    categoria = extraer_dato("CATEGORIA", respuesta_ia).upper()
    descripcion = extraer_dato("DESC", respuesta_ia)
    historia = extraer_dato("HISTORIA", respuesta_ia)
    stats_raw = extraer_dato("STATS", respuesta_ia)
    evos_raw = extraer_dato("EVOS", respuesta_ia)
    
    # Procesar números
    numeros = [int(n) for n in re.findall(r'\d+', stats_raw)][:4]
    while len(numeros) < 4: 
        numeros.append(0)
    numeros = [min(100, max(0, n)) for n in numeros]
    
    # Procesar variantes
    variantes = [v.strip() for v in evos_raw.split(",") if v.strip() and len(v.strip()) > 2][:3]
    
    return {
        'nombre': nombre,
        'categoria': categoria,
        'descripcion': descripcion,
        'historia': historia,
        'numeros': numeros,
        'variantes': variantes
    }

def obtener_etiquetas(categoria):
    """Devuelve las etiquetas correctas según la categoría"""
    if "ANIMAL" in categoria:
        return ["🐾 Fuerza", "⚡ Agilidad", "⚠️ Peligro", "💎 Rareza"]
    elif "LUGAR" in categoria:
        return ["🏛️ Historia", "📸 Belleza", "🌍 Cultura", "💎 Rareza"]
    else:
        return ["😋 Sabor", "🌶️ Picante", "🥗 Salud", "💎 Rareza"]

def renderizar_ficha(datos, etiquetas):
    """Renderiza la ficha técnica del elemento"""
    
    st.markdown(f"## 📋 {datos['nombre']}")
    st.markdown(f"<div class='data-card'><p><b>CATEGORÍA:</b> {datos['categoria']}</p><p>{datos['descripcion']}</p></div>", unsafe_allow_html=True)
    
    st.markdown("### 📖 Historia")
    st.markdown(f"<div class='historia-box'><p>{datos['historia']}</p></div>", unsafe_allow_html=True)
    
    st.markdown("### 📊 Puntos Base")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"<p>{etiquetas[0]}: {datos['numeros'][0]}%</p>", unsafe_allow_html=True)
        st.progress(datos['numeros'][0]/100)
        st.markdown(f"<p>{etiquetas[1]}: {datos['numeros'][1]}%</p>", unsafe_allow_html=True)
        st.progress(datos['numeros'][1]/100)
    with c2:
        st.markdown(f"<p>{etiquetas[2]}: {datos['numeros'][2]}%</p>", unsafe_allow_html=True)
        st.progress(datos['numeros'][2]/100)
        st.markdown(f"<p>{etiquetas[3]}: {datos['numeros'][3]}%</p>", unsafe_allow_html=True)
        st.progress(datos['numeros'][3]/100)
    
    st.markdown("### 🔄 Variantes Registradas")
    st.markdown("*Haz clic en cualquier variante para explorarla*")
    
    return datos['variantes']

# ========================================
# INTERFAZ PRINCIPAL
# ========================================

with st.container():
    st.markdown("<div class='pokedex-frame'>", unsafe_allow_html=True)
    
    estado_placeholder = st.empty()
    
    # PRIORIDAD 1: Verificar si se pulsó una variante
    if st.session_state.variante_seleccionada:
        estado_placeholder.markdown(f"<div class='status-indicator'>🔄 Accediendo a datos de {st.session_state.variante_seleccionada}...</div>", unsafe_allow_html=True)
        
        try:
            prompt = obtener_prompt_base(st.session_state.variante_seleccionada)
            respuesta = consultar_ia(prompt)
            datos = procesar_respuesta(respuesta)
            
            # Heredar categoría si existe
            if st.session_state.categoria_actual:
                datos['categoria'] = st.session_state.categoria_actual
            
            etiquetas = obtener_etiquetas(datos['categoria'])
            
            # Actualizar ruta
            st.session_state.historial_ruta.append(datos['nombre'])
            st.session_state.categoria_actual = datos['categoria']
            
            col_img, col_info = st.columns([1, 2])
            
            with col_img:
                st.info(f"ℹ️ Consultando base de datos para:\n\n**{datos['nombre']}**")
            
            with col_info:
                variantes = renderizar_ficha(datos, etiquetas)
                
                # Botones de variantes
                for var in variantes:
                    if st.button(f"🔍 {var}", key=f"var_{var}"):
                        st.session_state.variante_seleccionada = var
                        st.rerun()
            
            # Audio
            texto_audio = f"{datos['nombre']}. {datos['descripcion']}. {datos['historia'][:180]}"
            texto_audio = sanitizar_texto(texto_audio)
            tts = gTTS(text=texto_audio, lang='es')
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            st.audio(fp)
            
            estado_placeholder.markdown("<div class='status-indicator'>✅ Datos cargados</div>", unsafe_allow_html=True)
            
            # Resetear selección
            st.session_state.variante_seleccionada = None
            
        except Exception as e:
            estado_placeholder.markdown("<div class='status-indicator'>❌ Error al cargar variante</div>", unsafe_allow_html=True)
            st.error(f"Error: {e}")
    
    # PRIORIDAD 2: Escaneo de imagen
    else:
        estado_placeholder.markdown("<div class='status-indicator'>⏳ Esperando objetivo...</div>", unsafe_allow_html=True)
        
        col_img, col_info = st.columns([1, 2])
        
        with col_img:
            archivo = st.file_uploader("", type=["jpg", "png", "jpeg"])
            if archivo:
                st.image(PIL.Image.open(archivo), use_container_width=True)
                analizar = st.button("🔍 ESCANEAR OBJETIVO")
        
        if archivo and analizar:
            estado_placeholder.markdown("<div class='status-indicator'>🔄 Analizando imagen...</div>", unsafe_allow_html=True)
            
            try:
                img_b64 = encode_image(archivo)
                prompt = obtener_prompt_base()
                respuesta = consultar_ia(prompt, img_b64)
                datos = procesar_respuesta(respuesta)
                etiquetas = obtener_etiquetas(datos['categoria'])
                
                # Resetear e iniciar ruta
                st.session_state.historial_ruta = [datos['nombre']]
                st.session_state.categoria_actual = datos['categoria']
                
                with col_info:
                    variantes = renderizar_ficha(datos, etiquetas)
                    
                    # Botones de variantes
                    for var in variantes:
                        if st.button(f"🔍 {var}", key=f"var_{var}"):
                            st.session_state.variante_seleccionada = var
                            st.rerun()
                
                # Audio
                texto_audio = f"{datos['nombre']}. {datos['descripcion']}. {datos['historia'][:180]}"
                texto_audio = sanitizar_texto(texto_audio)
                tts = gTTS(text=texto_audio, lang='es')
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                st.audio(fp)
                
                estado_placeholder.markdown("<div class='status-indicator'>✅ Escaneo completado</div>", unsafe_allow_html=True)
                
            except Exception as e:
                estado_placeholder.markdown("<div class='status-indicator'>❌ Error en escaneo</div>", unsafe_allow_html=True)
                st.error(f"Error: {e}")
    
    st.markdown("</div>", unsafe_allow_html=True)
