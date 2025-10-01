import streamlit as st
import pandas as pd
import os
import shutil
from pathlib import Path
import zipfile
import io # Para trabajar con datos en memoria (esencial en la nube)

# --- CONFIGURACIÓN ---
COLUMNA_CURP = 'CURP'
TEMP_DIR = Path("temp_processing") # Directorio temporal para la nube

def extraer_zip(archivo_comprimido, ruta_destino):
    """Extrae archivos de un ZIP cargado por el usuario a una carpeta temporal."""
    try:
        with zipfile.ZipFile(archivo_comprimido, 'r') as zf:
            # Crea la carpeta de destino si no existe
            ruta_destino.mkdir(parents=True, exist_ok=True)
            # Extrae todos los contenidos
            zf.extractall(ruta_destino)
        return True
    except Exception as e:
        st.error(f"❌ Error al extraer el archivo comprimido: {e}")
        return False

def crear_zip_para_descarga(archivos_movidos: list, carpeta_destino: Path):
    """Crea un archivo ZIP en memoria con los archivos encontrados para que el usuario lo descargue."""
    # Usamos io.BytesIO para crear el archivo ZIP en memoria
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for archivo_nombre in archivos_movidos:
            archivo_path = carpeta_destino / archivo_nombre
            if archivo_path.is_file():
                # Escribir el archivo en el ZIP, usando solo el nombre del archivo (no la ruta completa)
                zf.write(archivo_path, arcname=archivo_nombre)
    
    # Restablece el puntero al inicio del buffer
    buffer.seek(0)
    return buffer

def buscar_y_mover_archivos(df_curps: pd.DataFrame, ruta_origen: Path, ruta_destino: Path):
    """
    Busca archivos en la ruta de origen cuyos nombres contengan una CURP de la lista
    y los 'mueve' (simula el movimiento, usando copia para asegurar) a la carpeta de destino.
    """
    curps_encontradas = 0
    archivos_movidos = []
    
    # Asegurar que la carpeta de destino existe
    ruta_destino.mkdir(parents=True, exist_ok=True)
    
    st.info(f"Buscando en {ruta_origen}...")
    
    # Obtener lista de CURP de forma limpia
    lista_curps = df_curps[COLUMNA_CURP].astype(str).str.upper().str.strip().tolist()
    
    # 3. Iterar sobre todos los archivos en la carpeta de origen
    for archivo_nombre in os.listdir(ruta_origen):
        
        archivo_path = ruta_origen / archivo_nombre
        if archivo_path.is_file():
            nombre_archivo_upper = archivo_nombre.upper()
            
            for curp in lista_curps:
                if curp in nombre_archivo_upper:
                    
                    destino_completo = ruta_destino / archivo_nombre
                    
                    try:
                        # En la nube, es mejor COPIAR a la carpeta de destino
                        # y luego eliminar la original si fuera necesario.
                        shutil.copy(archivo_path, destino_completo) 
                        curps_encontradas += 1
                        archivos_movidos.append(archivo_nombre)
                        st.success(f"✅ Encontrado y Preparado: **{archivo_nombre}** (CURP: {curp})")
                        break # Pasa al siguiente archivo
                    except Exception as e:
                        st.error(f"❌ Error al procesar {archivo_nombre}: {e}")
    
    return curps_encontradas, archivos_movidos


# --- INTERFAZ DE STREAMLIT ---

st.title("☁️ Organizador de Documentos por CURP (Cloud) By Emiliado D")
st.markdown("Sube tu lista de **CURP (XLS/XLSX)** y un **ZIP** o **RAR** con los documentos de tus alumnos.")

# --- ENTRADAS DEL USUARIO ---

# 1. Carga del archivo Excel
archivo_excel = st.file_uploader("1. Sube el Archivo Excel con las CURP", type=['xls', 'xlsx'])

# 2. Carga del archivo comprimido
archivo_zip = st.file_uploader("2. Sube el Archivo ZIP/RAR con los Documentos", type=['zip', 'rar'])

if archivo_excel and archivo_zip:
    
    if st.button("🚀 Iniciar Búsqueda, Organización y Descarga"):
        
        # 0. Preparar y limpiar el entorno temporal
        if TEMP_DIR.exists():
            shutil.rmtree(TEMP_DIR)
        TEMP_DIR.mkdir()

        # Definir subcarpetas dentro del directorio temporal
        CARPETA_ORINGEN_ARCHIVOS = TEMP_DIR / "archivos_descomprimidos"
        CARPETA_DESTINO_ENCONTRADOS = TEMP_DIR / "archivos_encontrados"
        
        st.subheader("Paso 1: Extrayendo Archivos...")
        
        # 1. Descomprimir el archivo cargado
        if extraer_zip(archivo_zip, CARPETA_ORINGEN_ARCHIVOS):
            st.success("Archivos extraídos correctamente.")
            
            try:
                # 2. Leer el archivo Excel
                df_curps = pd.read_excel(archivo_excel)
                
                if COLUMNA_CURP not in df_curps.columns:
                    st.error(f"❌ Error: La columna esperada '{COLUMNA_CURP}' no se encontró en el Excel.")
                else:
                    st.subheader("Paso 2: Buscando y Organizando Archivos...")
                    
                    # 3. Ejecutar la función principal de búsqueda
                    conteo, archivos_encontrados = buscar_y_mover_archivos(
                        df_curps, 
                        CARPETA_ORINGEN_ARCHIVOS, 
                        CARPETA_DESTINO_ENCONTRADOS
                    )
                    
                    if conteo > 0:
                        st.subheader("Paso 3: Generando Archivo de Descarga...")
                        
                        # 4. Comprimir los archivos encontrados para descarga
                        zip_buffer = crear_zip_para_descarga(archivos_encontrados, CARPETA_DESTINO_ENCONTRADOS)
                        
                        st.balloons()
                        st.success(f"🎉 Proceso Terminado. Se encontraron y prepararon {conteo} archivos.")
                        st.dataframe(pd.DataFrame({"Archivos Encontrados": archivos_encontrados}))
                        
                        # 5. Botón de descarga
                        st.download_button(
                            label="⬇️ Descargar Archivos Encontrados (ZIP)",
                            data=zip_buffer,
                            file_name="documentos_filtrados_curp.zip",
                            mime="application/zip"
                        )
                        
                    else:
                        st.warning("No se encontró ningún archivo con las CURP especificadas en el ZIP.")

            except Exception as e:
                st.error(f"Ocurrió un error en el procesamiento: {e}")
        
        # Opcional: Limpieza final del directorio temporal
        if TEMP_DIR.exists():
            shutil.rmtree(TEMP_DIR)