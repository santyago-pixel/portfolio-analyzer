#!/usr/bin/env python3
"""
Script para probar la carga de Excel directamente
"""

import pandas as pd
import numpy as np
import os

def test_excel_loading():
    """Probar la carga de Excel con el mismo código que la aplicación"""
    
    # Buscar archivos Excel en el directorio
    excel_files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    print(f"Archivos Excel encontrados: {excel_files}")
    
    if not excel_files:
        print("No se encontraron archivos Excel")
        return
    
    excel_file = excel_files[0]
    print(f"Usando archivo: {excel_file}")
    
    try:
        # Cargar operaciones (mismo código que la app)
        operaciones = pd.read_excel(excel_file, sheet_name='Operaciones')
        
        print("\n=== DATOS CRUDOS DEL EXCEL ===")
        print("Primeras 10 filas:")
        print(operaciones.head(10))
        
        print("\n=== TIPOS ÚNICOS EN COLUMNA 'Operacion' ===")
        if 'Operacion' in operaciones.columns:
            tipos_operacion = operaciones['Operacion'].unique()
            for i, tipo in enumerate(tipos_operacion):
                print(f"{i+1}. '{tipo}' (lower: '{str(tipo).lower()}')")
        
        # Mapear columnas (mismo código que la app)
        operaciones_mapped = pd.DataFrame()
        operaciones_mapped['Fecha'] = operaciones['Fecha']
        operaciones_mapped['Tipo'] = operaciones['Operacion']
        operaciones_mapped['Activo'] = operaciones['Activo']
        operaciones_mapped['Cantidad'] = operaciones['Nominales']
        operaciones_mapped['Precio_Concertacion'] = operaciones['Precio']
        operaciones_mapped['Monto'] = operaciones['Valor']
        
        print("\n=== ANTES DEL FILTRADO ===")
        print("Tipos únicos en 'Tipo':")
        tipos_tipo = operaciones_mapped['Tipo'].unique()
        for i, tipo in enumerate(tipos_tipo):
            print(f"{i+1}. '{tipo}' (lower: '{str(tipo).lower()}')")
        
        # Filtrar (mismo código que la app)
        operaciones_mapped['Tipo'] = operaciones_mapped['Tipo'].replace('nan', np.nan)
        operaciones_mapped = operaciones_mapped.dropna()
        
        print("\n=== DESPUÉS DEL FILTRADO ===")
        print("Operaciones filtradas:")
        print(operaciones_mapped)
        
        print("\n=== TIPOS ÚNICOS DESPUÉS DEL FILTRADO ===")
        tipos_finales = operaciones_mapped['Tipo'].unique()
        for i, tipo in enumerate(tipos_finales):
            print(f"{i+1}. '{tipo}' (lower: '{str(tipo).lower()}')")
        
        # Buscar cupones específicamente
        print("\n=== BÚSQUEDA DE CUPONES ===")
        cupones = operaciones_mapped[
            operaciones_mapped['Tipo'].str.strip().str.lower().str.contains('cupon', na=False)
        ]
        print(f"Cupones encontrados: {len(cupones)}")
        if len(cupones) > 0:
            print(cupones)
        else:
            print("No se encontraron cupones")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_excel_loading()
