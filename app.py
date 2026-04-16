import pandas as pd
import fitz  # PyMuPDF
from docx import Document

# Función para leer el archivo según su tipo
def extraer_contenido(archivo):
    extension = archivo.name.split('.')[-1].lower()
    
    if extension in ['xlsx', 'xls']:
        df = pd.read_excel(archivo)
        return df.to_string() # Convierte el Excel en texto para la IA
        
    elif extension == 'docx':
        doc = Document(archivo)
        return "\n".join([para.text for para in doc.paragraphs])
        
    elif extension == 'pdf':
        doc = fitz.open(stream=archivo.read(), filetype="pdf")
        texto = ""
        for pagina in doc:
            texto += pagina.get_text()
        return texto
    
    else:
        return None # Si es imagen, se lo pasamos a Scout

# --- EN TU APP DE STREAMLIT ---
archivo_subido = st.file_uploader("Sube Balance (Excel, PDF, Word o Imagen)", 
                                  type=["pdf", "xlsx", "docx", "png", "jpg"])

if archivo_subido:
    contenido = extraer_contenido(archivo_subido)
    
    if contenido:
        # SI ES TEXTO/EXCEL: Se lo pasamos directo a Llama-3.3-70b (Ahorras tiempo)
        st.success("Documento leído como texto. Enviando a análisis...")
        prompt_final = f"Analiza estos datos financieros: {contenido}"
    else:
        # SI ES IMAGEN: Usamos Scout (Visión)
        st.warning("Es una imagen. Usando IA de Visión (Scout)...")
        # Aquí va tu código de Scout...
