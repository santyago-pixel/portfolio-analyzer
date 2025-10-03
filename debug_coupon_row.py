#!/usr/bin/env python3
"""
Script para debuggear específicamente la fila del cupón
"""

import pandas as pd
import numpy as np

def debug_coupon_row():
    """Debuggear la fila específica del cupón"""
    
    # Cargar operaciones
    operaciones = pd.read_excel('operaciones.xlsx', sheet_name='Operaciones')
    
    print("=== FILA DEL CUPÓN (fila 5) ===")
    cupon_row = operaciones.iloc[5]  # Fila 5 (índice 5)
    print("Fila completa:")
    print(cupon_row)
    print()
    
    print("=== ANÁLISIS COLUMNA POR COLUMNA ===")
    for col in operaciones.columns:
        value = cupon_row[col]
        print(f"{col}: '{value}' (tipo: {type(value)}, es NaN: {pd.isna(value)})")
    
    print("\n=== MAPEO DE COLUMNAS ===")
    # Mapear como lo hace la app
    fecha = operaciones['Fecha'].iloc[5]
    tipo = operaciones['Operacion'].iloc[5]
    activo = operaciones['Activo'].iloc[5]
    cantidad = operaciones['Nominales'].iloc[5]
    precio = operaciones['Precio'].iloc[5]
    monto = operaciones['Valor'].iloc[5]
    
    print(f"Fecha: '{fecha}' (es NaN: {pd.isna(fecha)})")
    print(f"Tipo: '{tipo}' (es NaN: {pd.isna(tipo)})")
    print(f"Activo: '{activo}' (es NaN: {pd.isna(activo)})")
    print(f"Cantidad: '{cantidad}' (es NaN: {pd.isna(cantidad)})")
    print(f"Precio: '{precio}' (es NaN: {pd.isna(precio)})")
    print(f"Monto: '{monto}' (es NaN: {pd.isna(monto)})")
    
    print("\n=== VERIFICAR QUÉ COLUMNAS TIENEN NOMBRES CORRECTOS ===")
    print("Columnas disponibles:")
    for i, col in enumerate(operaciones.columns):
        print(f"{i}. '{col}'")

if __name__ == "__main__":
    debug_coupon_row()
