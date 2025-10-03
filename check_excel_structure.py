#!/usr/bin/env python3

import pandas as pd

# Verificar estructura del Excel
try:
    # Cargar operaciones
    operaciones = pd.read_excel('operaciones.xlsx', sheet_name='Operaciones')
    print("=== OPERACIONES ===")
    print(f"Columnas: {list(operaciones.columns)}")
    print(f"Primeras 5 filas:")
    print(operaciones.head())
    
    # Cargar precios
    precios = pd.read_excel('operaciones.xlsx', sheet_name='Precios')
    print("\n=== PRECIOS ===")
    print(f"Columnas: {list(precios.columns)}")
    print(f"Primeras 5 filas:")
    print(precios.head())
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
