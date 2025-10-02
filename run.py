#!/usr/bin/env python3
"""
Script para ejecutar la aplicación Portfolio Analyzer
"""

import subprocess
import sys
import os

def install_requirements():
    """Instalar dependencias si es necesario"""
    try:
        import streamlit
        import pandas
        import plotly
        print("✅ Todas las dependencias están instaladas")
    except ImportError:
        print("📦 Instalando dependencias...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def main():
    """Función principal"""
    print("🚀 Iniciando Portfolio Analyzer...")
    
    # Verificar que estamos en el directorio correcto
    if not os.path.exists("app.py"):
        print("❌ Error: No se encontró app.py. Asegúrate de estar en el directorio correcto.")
        return
    
    # Instalar dependencias si es necesario
    install_requirements()
    
    # Ejecutar la aplicación
    print("🌐 Abriendo la aplicación en el navegador...")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", "app.py",
        "--server.port", "8501",
        "--server.address", "localhost"
    ])

if __name__ == "__main__":
    main()
