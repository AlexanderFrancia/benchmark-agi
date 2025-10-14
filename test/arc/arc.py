
import shutil
from pathlib import Path

def copiar_archivos_sin_extension(carpeta_origen, carpeta_destino):
    """
    Copia archivos a una carpeta destino, renombrándolos sin extensión.
    
    Args:
        carpeta_origen: Ruta de la carpeta con los archivos originales
        carpeta_destino: Ruta donde se copiarán los archivos sin extensión
    """
    # Crear carpeta destino si no existe
    Path(carpeta_destino).mkdir(parents=True, exist_ok=True)
    
    # Obtener todos los archivos de la carpeta origen
    carpeta = Path(carpeta_origen)
    archivos_copiados = 0
    
    for archivo in carpeta.iterdir():
        if archivo.is_file():
            # Obtener nombre sin extensión
            nombre_sin_ext = archivo.stem
            
            # Ruta completa del archivo destino (sin extensión)
            archivo_destino = Path(carpeta_destino) / nombre_sin_ext
            
            # Copiar el archivo
            shutil.copy2(archivo, archivo_destino)
            archivos_copiados += 1
            print(f"Copiado: {archivo.name} -> {nombre_sin_ext}")
    
    print(f"\n✓ Total de archivos copiados: {archivos_copiados}")
    return archivos_copiados


def crear_txt_con_nombres(carpeta_origen, carpeta_destino):
    """
    Crea un archivo .txt en la carpeta destino con todos los nombres sin extensión.
    
    Args:
        carpeta_origen: Ruta de la carpeta con los archivos originales
        carpeta_destino: Ruta donde se guardará el archivo de texto
    """
    # Crear carpeta destino si no existe
    Path(carpeta_destino).mkdir(parents=True, exist_ok=True)
    
    # Obtener nombres sin extensión
    carpeta = Path(carpeta_origen)
    nombres_sin_extension = [
        archivo.stem
        for archivo in carpeta.iterdir()
        if archivo.is_file()
    ]
    
    # Guardar en archivo de texto separados por comas
    archivo_salida = Path(carpeta_destino) / "arc2.txt"
    with open(archivo_salida, 'w', encoding='utf-8') as f:
        f.write(', '.join(nombres_sin_extension))
    
    print(f"✓ Archivo creado: {archivo_salida}")
    print(f"✓ Total de nombres guardados: {len(nombres_sin_extension)}")
    return nombres_sin_extension


# Ejemplo de uso
if __name__ == "__main__":
    # Crear archivo de texto con los nombres separados por comas
    crear_txt_con_nombres(
        carpeta_origen="../data/arcagi2/train",
        carpeta_destino="C:/Users/alexa/Documents/Maestria/TESIS/Proyecto/benchmark/test"
    )