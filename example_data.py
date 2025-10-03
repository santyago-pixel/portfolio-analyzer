"""
Generador de datos de ejemplo para testing
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def generate_sample_data(start_date: str = "2024-01-01", end_date: str = "2024-12-31"):
    """Generar datos de ejemplo para testing"""
    
    # Configurar semilla para reproducibilidad
    np.random.seed(42)
    random.seed(42)
    
    # Fechas
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    date_range = pd.date_range(start, end, freq='D')
    
    # Activos de ejemplo
    assets = {
        'BONO_GD30': {'tipo': 'Bono', 'precio_inicial': 95.0, 'volatilidad': 0.02},
        'BONO_AL30': {'tipo': 'Bono', 'precio_inicial': 92.0, 'volatilidad': 0.025},
        'ACCION_YPF': {'tipo': 'Accion', 'precio_inicial': 8500.0, 'volatilidad': 0.03},
        'ACCION_GGAL': {'tipo': 'Accion', 'precio_inicial': 1200.0, 'volatilidad': 0.035},
        'ACCION_MIRG': {'tipo': 'Accion', 'precio_inicial': 450.0, 'volatilidad': 0.04}
    }
    
    # Generar precios diarios
    precios_data = []
    for asset, info in assets.items():
        precio_actual = info['precio_inicial']
        volatilidad = info['volatilidad']
        
        for fecha in date_range:
            # Generar retorno diario
            if info['tipo'] == 'Bono':
                # Bonos con menor volatilidad
                retorno = np.random.normal(0.0002, volatilidad)
            else:
                # Acciones con mayor volatilidad
                retorno = np.random.normal(0.0005, volatilidad)
            
            precio_actual *= (1 + retorno)
            
            precios_data.append({
                'Fecha': fecha,
                'Activo': asset,
                'Precio': round(precio_actual, 2)
            })
    
    precios_df = pd.DataFrame(precios_data)
    
    # Generar operaciones
    operaciones_data = []
    
    # Operaciones iniciales de compra
    for asset in assets.keys():
        operaciones_data.append({
            'Fecha': start,
            'Tipo': 'Compra',
            'Activo': asset,
            'Cantidad': random.randint(50, 200),
            'Precio': assets[asset]['precio_inicial'],
            'Monto': 0  # Se calculará
        })
    
    # Generar operaciones aleatorias durante el año
    for _ in range(20):
        fecha = random.choice(date_range[30:])  # Después del primer mes
        asset = random.choice(list(assets.keys()))
        tipo = random.choice(['Compra', 'Venta', 'Cupón', 'Dividendo'])
        
        if tipo in ['Compra', 'Venta']:
            cantidad = random.randint(10, 100)
            precio = precios_df[
                (precios_df['Activo'] == asset) & 
                (precios_df['Fecha'] == fecha)
            ]['Precio'].iloc[0]
            monto = cantidad * precio
        else:
            cantidad = 0
            precio = 0
            monto = random.randint(100, 1000)
        
        operaciones_data.append({
            'Fecha': fecha,
            'Tipo': tipo,
            'Activo': asset,
            'Cantidad': cantidad,
            'Precio': precio,
            'Monto': monto
        })
    
    # Calcular montos para operaciones de compra/venta
    for op in operaciones_data:
        if op['Tipo'] in ['Compra', 'Venta'] and op['Monto'] == 0:
            op['Monto'] = op['Cantidad'] * op['Precio']
    
    operaciones_df = pd.DataFrame(operaciones_data)
    
    # Ordenar por fecha
    operaciones_df = operaciones_df.sort_values('Fecha')
    
    return operaciones_df, precios_df

def save_sample_data(filename: str = "sample_portfolio.xlsx"):
    """Guardar datos de ejemplo en un archivo Excel"""
    operaciones, precios = generate_sample_data()
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        operaciones.to_excel(writer, sheet_name='Operaciones', index=False)
        precios.to_excel(writer, sheet_name='Precios', index=False)
    
    print(f"Datos de ejemplo guardados en {filename}")
    return operaciones, precios

if __name__ == "__main__":
    # Generar y guardar datos de ejemplo
    operaciones, precios = save_sample_data()
    
    print("Operaciones generadas:")
    print(operaciones.head())
    print("\nPrecios generados:")
    print(precios.head())
