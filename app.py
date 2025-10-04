import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
import os
import io
from io import BytesIO
warnings.filterwarnings('ignore')

# Importar módulos personalizados
from portfolio_calculator import PortfolioCalculator
from example_data import generate_sample_data

# Configuración de la página
st.set_page_config(
    page_title="Portfolio Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .main > div {
        padding-top: 1rem;
    }
    .metric-card {
        background: #708090;
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        margin: 0.5rem 0;
        text-align: center;
        color: white;
    }
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
        color: white;
        text-align: center;
    }
    .positive {
        color: #00C851;
    }
    .negative {
        color: #ff4444;
    }
    .neutral {
        color: #ffbb33;
    }
</style>
""", unsafe_allow_html=True)

def load_data(uploaded_file=None):
    """Cargar datos de operaciones y precios"""
    # Si no se proporciona un archivo, intentar cargar automáticamente el archivo operaciones.xlsx
    if uploaded_file is None:
        default_file = "operaciones.xlsx"
        if os.path.exists(default_file):
            uploaded_file = default_file
        else:
            # Buscar archivo Excel automáticamente
            excel_files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
            if excel_files:
                # Si hay archivos Excel en el directorio, usar el primero
                excel_file = excel_files[0]
                uploaded_file = open(excel_file, 'rb')
    
    if uploaded_file is not None:
        try:
            # Cargar operaciones (estructura: Fecha, Operacion, Tipo de activo, Activo, Nominales, Precio, Valor)
            operaciones = pd.read_excel(uploaded_file, sheet_name='Operaciones')
            
            
            # Mapear columnas a formato esperado
            operaciones_mapped = pd.DataFrame()
            operaciones_mapped['Fecha'] = operaciones['Fecha']
            operaciones_mapped['Tipo'] = operaciones['Operacion']  # Compra/Venta/Cupón/Dividendo/Flujo
            operaciones_mapped['Activo'] = operaciones['Activo']
            operaciones_mapped['Cantidad'] = operaciones['Nominales']
            operaciones_mapped['Precio_Concertacion'] = operaciones['Precio']  # Precio de la transacción
            operaciones_mapped['Monto'] = operaciones['Valor']
            
            # Filtrar filas válidas (eliminar NaN pero mantener cupones que pueden tener NaN en cantidad/precio)
            # Primero convertir 'nan' strings a NaN reales
            operaciones_mapped['Tipo'] = operaciones_mapped['Tipo'].replace('nan', np.nan)
            
            # Para cupones y amortizaciones, llenar NaN en cantidad y precio con 0
            cupon_mask = operaciones_mapped['Tipo'].str.strip().str.lower().str.contains('cupon', na=False)
            amortization_mask = operaciones_mapped['Tipo'].str.strip().str.lower().str.contains('amortizacion', na=False)
            
            # Combinar máscaras para cupones y amortizaciones
            special_ops_mask = cupon_mask | amortization_mask
            
            operaciones_mapped.loc[special_ops_mask, 'Cantidad'] = operaciones_mapped.loc[special_ops_mask, 'Cantidad'].fillna(0)
            operaciones_mapped.loc[special_ops_mask, 'Precio_Concertacion'] = operaciones_mapped.loc[special_ops_mask, 'Precio_Concertacion'].fillna(0)
            
            # Ahora eliminar filas con NaN en columnas críticas
            operaciones_mapped = operaciones_mapped.dropna(subset=['Fecha', 'Tipo', 'Activo', 'Monto'])
            
            
            # Cargar precios (estructura: fechas en columna A, activos en fila 1)
            precios = pd.read_excel(uploaded_file, sheet_name='Precios')
            
            # La primera columna debe ser las fechas
            fecha_col = precios.columns[0]
            precios = precios.rename(columns={fecha_col: 'Fecha'})
            
            # Convertir a formato largo (melt)
            precios_long = precios.melt(
                id_vars=['Fecha'], 
                var_name='Activo', 
                value_name='Precio'
            )
            precios_long = precios_long.dropna()  # Eliminar filas con NaN
            
            st.session_state.use_sample_data = False
            return operaciones_mapped, precios_long
            
        except Exception as e:
            st.error(f"Error al cargar el archivo: {str(e)}")
            st.error("Verifica que el archivo tenga la estructura correcta:")
            st.error("- Hoja 'Operaciones': Fecha, Operacion, Tipo de activo, Activo, Nominales, Precio, Valor")
            st.error("- Hoja 'Precios': Fechas en columna A, activos en fila 1")
            return None, None
    
    # Usar datos de ejemplo si está habilitado
    if st.session_state.get('use_sample_data', False):
        from example_data import generate_sample_data_with_your_structure
        operaciones, precios = generate_sample_data_with_your_structure()
        return operaciones, precios
    
    return None, None


def create_portfolio_composition(calculator: PortfolioCalculator):
    """Crear sección de composición de la cartera"""
    if calculator.portfolio_data is None:
        calculator.portfolio_data = calculator.calculate_portfolio_value()
    
    # Obtener activos únicos y filtrar NaN
    assets = calculator.operaciones['Activo'].unique()
    assets = [asset for asset in assets if pd.notna(asset)]  # Filtrar NaN
    
    composition_data = []
    
    for asset in assets:
        # Obtener operaciones del activo
        asset_ops = calculator.operaciones[calculator.operaciones['Activo'] == asset]
        
        
        # Calcular posición actual y precio promedio ponderado
        total_invested = 0
        total_quantity = 0
        weighted_price_sum = 0  # Para calcular precio promedio ponderado
        
        for idx, op in asset_ops.iterrows():
            # Limpiar espacios en blanco del tipo de operación
            tipo_limpio = str(op['Tipo']).strip()
            
            if tipo_limpio == 'Compra':
                total_invested += op['Monto']
                total_quantity += op['Cantidad']
                # Acumular para precio promedio ponderado
                weighted_price_sum += op['Cantidad'] * op['Precio_Concertacion']
            elif tipo_limpio == 'Venta':
                # Para ventas, reducimos cantidad pero mantenemos el precio promedio
                total_quantity -= op['Cantidad']
                # No afectamos weighted_price_sum para mantener precio promedio de compras
        
        # Mostrar todos los activos que han tenido operaciones
        if total_invested != 0 or total_quantity != 0:  # Mostrar si hay inversión o cantidad
            # Calcular precio promedio ponderado
            if total_quantity > 0:
                avg_price = weighted_price_sum / total_quantity
            else:
                avg_price = 0
            
            # Obtener precio actual
            asset_prices = calculator.precios[calculator.precios['Activo'] == asset]
            if not asset_prices.empty and len(asset_prices) > 0:
                current_price = asset_prices['Precio'].iloc[-1]
                current_value = total_quantity * current_price
                
                # Calcular peso en la cartera
                portfolio_value = calculator.portfolio_data['Valor_Cartera'].iloc[-1] if not calculator.portfolio_data.empty and len(calculator.portfolio_data) > 0 else 1
                weight = current_value / portfolio_value if portfolio_value > 0 else 0
                
                # Calcular ganancia/pérdida
                gain_loss = current_value - total_invested
                gain_loss_pct = gain_loss / total_invested if total_invested > 0 else 0
                
                composition_data.append({
                    'Activo': asset,
                    'Cantidad': f"{total_quantity:,.0f}",
                    'Precio_Promedio': f"${avg_price:,.2f}" if avg_price > 0 else "N/A",
                    'Precio_Actual': f"${current_price:,.2f}",
                    'Valor_Actual': f"${current_value:,.2f}",
                    'Inversion_Total': f"${total_invested:,.2f}",
                    'Ganancia_Perdida': f"${gain_loss:,.2f}",
                    'Ganancia_Perdida_%': f"{gain_loss_pct:.2%}",
                    'Peso_Cartera': f"{weight:.2%}"
                })
            else:
                # Si no hay datos de precios, mostrar solo la información básica
                composition_data.append({
                    'Activo': asset,
                    'Cantidad': f"{total_quantity:,.0f}",
                    'Precio_Promedio': f"${avg_price:,.2f}" if avg_price > 0 else "N/A",
                    'Precio_Actual': "N/A",
                    'Valor_Actual': f"${0:,.2f}",
                    'Inversion_Total': f"${total_invested:,.2f}",
                    'Ganancia_Perdida': f"${-total_invested:,.2f}",
                    'Ganancia_Perdida_%': "-100.00%",
                    'Peso_Cartera': "0.00%"
                })
    
    if composition_data:
        composition_df = pd.DataFrame(composition_data)
        
        st.header("Composición de la Cartera")
        
        # Mostrar resumen
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_assets = len(composition_df)
            st.metric("Total de Activos", total_assets)
        
        with col2:
            total_invested = sum([float(x.replace('$', '').replace(',', '')) for x in composition_df['Inversion_Total']])
            st.metric("Inversión Total", f"${total_invested:,.2f}")
        
        with col3:
            total_current = sum([float(x.replace('$', '').replace(',', '')) for x in composition_df['Valor_Actual']])
            st.metric("Valor Actual", f"${total_current:,.2f}")
        
        # Tabla detallada
        st.dataframe(
            composition_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Activo": st.column_config.TextColumn("Activo", width="medium"),
                "Cantidad": st.column_config.TextColumn("Cantidad", width="small"),
                "Precio_Promedio": st.column_config.TextColumn("Precio Promedio", width="medium"),
                "Precio_Actual": st.column_config.TextColumn("Precio Actual", width="medium"),
                "Valor_Actual": st.column_config.TextColumn("Valor Actual", width="medium"),
                "Inversion_Total": st.column_config.TextColumn("Inversión Total", width="medium"),
                "Ganancia_Perdida": st.column_config.TextColumn("Ganancia/Pérdida", width="medium"),
                "Ganancia_Perdida_%": st.column_config.TextColumn("Ganancia/Pérdida %", width="medium"),
                "Peso_Cartera": st.column_config.TextColumn("Peso en Cartera", width="medium")
            }
        )
        
        return composition_df
    
    return pd.DataFrame()

def create_performance_chart(returns_df):
    """Crear gráfico de performance"""
    if returns_df is None:
        return None
    
    # Calcular retornos acumulados
    returns_df['Cumulative_Return'] = (1 + returns_df['Rendimiento_Diario']).cumprod()
    
    fig = go.Figure()
    
    # Línea de rendimiento acumulado
    fig.add_trace(go.Scatter(
        x=returns_df['Fecha'],
        y=returns_df['Cumulative_Return'],
        mode='lines',
        name='Rendimiento Acumulado',
        line=dict(color='#667eea', width=2)
    ))
    
    # Línea de referencia (100%)
    fig.add_hline(y=1, line_dash="dash", line_color="gray", 
                  annotation_text="Punto de partida")
    
    fig.update_layout(
        title="Performance de la Cartera",
        xaxis_title="Fecha",
        yaxis_title="Valor Acumulado",
        hovermode='x unified',
        template="plotly_white"
    )
    
    return fig

def create_returns_distribution(returns_df):
    """Crear gráfico de distribución de rendimientos"""
    if returns_df is None:
        return None
    
    fig = px.histogram(
        returns_df, 
        x='Rendimiento_Diario',
        nbins=50,
        title="Distribución de Rendimientos Diarios",
        labels={'Rendimiento_Diario': 'Rendimiento Diario', 'count': 'Frecuencia'}
    )
    
    fig.update_layout(template="plotly_white")
    
    return fig

def main():
    st.markdown("---")
    
    # Cargar datos primero (usando archivo por defecto para el sidebar)
    operaciones, precios = load_data()
    
    # Validar que los datos se cargaron correctamente
    if operaciones is None or precios is None:
        st.error("Error al cargar los datos. Verifica que el archivo Excel tenga las hojas 'Operaciones' y 'Precios'.")
        return
    
    # Sidebar con configuración
    with st.sidebar:
        st.header("Configuración")
        
        # Período de análisis
        st.subheader("Período de Análisis")
        
        # Calcular fechas mínimas y máximas disponibles
        min_date = None
        max_date = None
        if operaciones is not None and precios is not None:
            # Usar copias para no modificar los datos originales
            ops_copy = operaciones.copy()
            precios_copy = precios.copy()
            ops_copy['Fecha'] = pd.to_datetime(ops_copy['Fecha'])
            precios_copy['Fecha'] = pd.to_datetime(precios_copy['Fecha'])
            
            # Fecha mínima: primera fecha de operaciones
            min_date = ops_copy['Fecha'].min().date()
            
            # Fecha máxima: última fecha de precios
            max_date = precios_copy['Fecha'].max().date()
        
        # Usar fechas disponibles o valores por defecto
        default_start = min_date if min_date else datetime.now() - timedelta(days=365)
        default_end = max_date if max_date else datetime.now()
        
        start_date = st.date_input(
            "Fecha de Inicio", 
            value=default_start,
            min_value=min_date,
            max_value=max_date
        )
        end_date = st.date_input(
            "Fecha de Fin", 
            value=default_end,
            min_value=min_date,
            max_value=max_date
        )
        
        # Carga de archivos
        st.subheader("Carga de Datos")
        uploaded_file = st.file_uploader(
            "Cargar archivo Excel",
            type=['xlsx', 'xls'],
            help="El archivo debe contener dos hojas: 'Operaciones' y 'Precios'",
            key="excel_uploader"
        )
        
        # Mostrar qué archivo se está usando
        if uploaded_file is not None:
            st.success(f"📁 Archivo cargado: {uploaded_file.name}")
        else:
            st.info("📁 Usando archivo por defecto: operaciones.xlsx")
        
    # Recargar datos si se subió un archivo nuevo
    if uploaded_file is not None:
        operaciones, precios = load_data(uploaded_file)
    
    
    if operaciones is not None and precios is not None:
        # Convertir fechas a datetime si no lo están
        operaciones['Fecha'] = pd.to_datetime(operaciones['Fecha'])
        precios['Fecha'] = pd.to_datetime(precios['Fecha'])
        
        # Filtrar datos por período seleccionado
        operaciones_filtered = operaciones[
            (operaciones['Fecha'] >= pd.to_datetime(start_date)) & 
            (operaciones['Fecha'] <= pd.to_datetime(end_date))
        ]
        
        precios_filtered = precios[
            (precios['Fecha'] >= pd.to_datetime(start_date)) & 
            (precios['Fecha'] <= pd.to_datetime(end_date))
        ]
        
        # Crear calculador de cartera con TODOS los datos para calcular posiciones iniciales correctamente
        # pero usar datos filtrados para el análisis del período
        calculator_full = PortfolioCalculator(operaciones, precios, pd.to_datetime(start_date))
        
        # Verificar si hay activos en cartera a la fecha de inicio
        initial_positions = calculator_full._get_initial_positions(pd.to_datetime(start_date))
        has_assets_in_portfolio = any(pos['cantidad'] > 0 for pos in initial_positions.values())
        
        # Si no hay activos en cartera al inicio del período, mostrar mensaje
        if not has_assets_in_portfolio:
            st.warning(f"No hay activos en cartera al inicio del período seleccionado: {start_date.strftime('%Y-%m-%d')}")
            return
        
        # Crear calculador con datos completos para calcular métricas de rendimiento
        # pero usar start_date y end_date para limitar el análisis al período seleccionado
        calculator = PortfolioCalculator(operaciones, precios, pd.to_datetime(start_date), pd.to_datetime(end_date))
        
        # Calcular rendimientos diarios
        returns_df = calculator.calculate_daily_returns()
        
        if returns_df is not None:
            # Calcular métricas
            metrics = calculator.calculate_metrics(0.05)  # Tasa libre de riesgo fija del 5%
            
            if metrics is not None:
                # Mostrar métricas principales
                st.header("Rendimiento de la Cartera")
                
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    # Valor de la cartera (última fecha de la tabla detalle de rendimientos)
                    portfolio_value = returns_df['Valor_Cartera'].iloc[-1] if not returns_df.empty else 0
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">Valor de la Cartera</div>
                        <div class="metric-value">
                            ${portfolio_value:,.0f}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    # Calcular rendimiento total usando la misma fórmula que la última sección
                    if 'Rendimiento_Diario' in returns_df.columns:
                        cumulative_return = (1 + returns_df['Rendimiento_Diario']).prod() - 1
                    else:
                        cumulative_return = metrics['total_return'] # Fallback if no daily returns
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">Rendimiento Total</div>
                        <div class="metric-value">
                            {cumulative_return:.2%}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    # Calcular amortizaciones del período usando datos ya filtrados
                    amortizaciones = 0
                    if 'Amortizaciones_Diarias' in returns_df.columns:
                        # Usar datos ya filtrados por el período (misma lógica que Rendimiento Total)
                        amortizaciones = returns_df['Amortizaciones_Diarias'].sum()
                    elif operaciones is not None:
                        # Fallback: filtrar operaciones por período seleccionado
                        ops_periodo = operaciones[
                            (operaciones['Fecha'] >= pd.to_datetime(start_date)) & 
                            (operaciones['Fecha'] <= pd.to_datetime(end_date))
                        ]
                        # Filtrar operaciones de amortizaciones
                        amortizacion_mask = ops_periodo['Tipo'].str.strip().str.lower().str.contains('amortización|amortizacion|amortization', na=False)
                        amortizaciones = ops_periodo[amortizacion_mask]['Monto'].sum()
                    
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">Amortizaciones</div>
                        <div class="metric-value">
                            ${amortizaciones:,.0f}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">Volatilidad</div>
                        <div class="metric-value">
                            {metrics['volatility']:.2%}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col5:
                    # Calcular cupones y dividendos del período usando datos ya filtrados
                    cupones_dividendos = 0
                    if 'Cupones_Diarios' in returns_df.columns:
                        # Usar datos ya filtrados por el período (misma lógica que Rendimiento Total)
                        cupones_dividendos = returns_df['Cupones_Diarios'].sum()
                    elif operaciones is not None:
                        # Fallback: filtrar operaciones por período seleccionado
                        ops_periodo = operaciones[
                            (operaciones['Fecha'] >= pd.to_datetime(start_date)) & 
                            (operaciones['Fecha'] <= pd.to_datetime(end_date))
                        ]
                        # Filtrar operaciones de cupones y dividendos
                        cupon_dividendo_mask = ops_periodo['Tipo'].str.strip().str.lower().str.contains('cupon|dividendo|coupon|dividend', na=False)
                        cupones_dividendos = ops_periodo[cupon_dividendo_mask]['Monto'].sum()
                    
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">Cupones y Dividendos</div>
                        <div class="metric-value">
                            ${cupones_dividendos:,.0f}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Tabla de activos del período
                st.subheader("Activos del Período")
                
                # Crear tabla con activos que tuvieron nominales positivos durante el período
                assets_table_data = []
                
                # Obtener todos los activos únicos del período
                period_operations = operaciones[
                    (operaciones['Fecha'] >= pd.to_datetime(start_date)) & 
                    (operaciones['Fecha'] <= pd.to_datetime(end_date))
                ]
                
                # Obtener activos que tuvieron operaciones en el período
                period_assets = period_operations['Activo'].unique()
                period_assets = [asset for asset in period_assets if pd.notna(asset)]
                
                for asset in period_assets:
                    # Calcular nominales al final del período
                    final_nominals = 0
                    
                    # Obtener todas las operaciones del activo hasta el final del período
                    asset_ops = operaciones[operaciones['Activo'] == asset]
                    asset_ops_until_end = asset_ops[asset_ops['Fecha'] <= pd.to_datetime(end_date)]
                    
                    for _, op in asset_ops_until_end.iterrows():
                        if str(op['Tipo']).strip() == 'Compra':
                            final_nominals += op['Cantidad']
                        elif str(op['Tipo']).strip() == 'Venta':
                            final_nominals -= op['Cantidad']
                    
                    # Solo incluir activos con nominales positivos al final del período
                    if final_nominals > 0:
                        # Obtener precio actual del activo
                        asset_prices = precios[
                            (precios['Activo'] == asset) & 
                            (precios['Fecha'] <= pd.to_datetime(end_date))
                        ]
                        current_price = asset_prices.iloc[-1]['Precio'] if not asset_prices.empty else 0
                        
                        # Calcular monto invertido (compras - ventas) en el período
                        period_asset_ops = period_operations[period_operations['Activo'] == asset]
                        purchases = period_asset_ops[period_asset_ops['Tipo'].str.strip() == 'Compra']['Monto'].sum()
                        sales = period_asset_ops[period_asset_ops['Tipo'].str.strip() == 'Venta']['Monto'].sum()
                        invested_amount = purchases - sales
                        
                        assets_table_data.append({
                            'Activo': asset,
                            'Nominales': final_nominals,
                            'Precio': current_price,
                            'Monto': final_nominals * current_price,
                            'Invertido': invested_amount,
                            'Dividendos Cupones Amortizaciones': '',  # Dejar en blanco por ahora
                            'Ganancia Neta': '',  # Dejar en blanco por ahora
                            '%': ''  # Dejar en blanco por ahora
                        })
                
                # Crear DataFrame y mostrar tabla
                if assets_table_data:
                    assets_df = pd.DataFrame(assets_table_data)
                    
                    # Formatear la tabla para mejor visualización
                    display_assets_df = assets_df.copy()
                    display_assets_df['Precio'] = display_assets_df['Precio'].apply(lambda x: f"${x:,.2f}")
                    display_assets_df['Monto'] = display_assets_df['Monto'].apply(lambda x: f"${x:,.0f}")
                    display_assets_df['Invertido'] = display_assets_df['Invertido'].apply(lambda x: f"${x:,.0f}")
                    
                    st.dataframe(display_assets_df, use_container_width=True)
                else:
                    st.info("No hay activos con nominales positivos al final del período seleccionado.")
            
            # Gráfico de evolución del valor de la cartera con rendimiento acumulado
            fig_cumulative = go.Figure()
            
            # Agregar serie de valor de cartera (eje izquierdo)
            fig_cumulative.add_trace(go.Scatter(
                x=returns_df['Fecha'],
                y=returns_df['Valor_Cartera'],
                mode='lines',
                name='Evolución del Capital Invertido',
                line=dict(color='#1f77b4', width=2),
                yaxis='y'
            ))
            
            # Calcular rendimiento acumulado si no existe
            if 'Rendimiento_Acumulado' not in returns_df.columns and 'Rendimiento_Diario' in returns_df.columns:
                returns_df['Rendimiento_Acumulado'] = (1 + returns_df['Rendimiento_Diario']).cumprod() - 1
            
            # Agregar serie de rendimiento acumulado (eje derecho)
            if 'Rendimiento_Acumulado' in returns_df.columns:
                fig_cumulative.add_trace(go.Scatter(
                    x=returns_df['Fecha'],
                    y=returns_df['Rendimiento_Acumulado'] * 100,  # Convertir a porcentaje
                    mode='lines',
                    name='Rendimiento Acumulado (%)',
                    line=dict(color='#00BFFF', width=2),  # Celeste continua
                    yaxis='y2'
                ))
            
            # Configurar layout con dos ejes Y
            fig_cumulative.update_layout(
                title="Evolución del Valor de la Cartera y Rendimiento Acumulado",
                template="plotly_white",
                xaxis=dict(title="Fecha"),
                yaxis=dict(
                    title="Valor de la Cartera ($)",
                    side="left",
                    showgrid=True
                ),
                yaxis2=dict(
                    title="Rendimiento Acumulado (%)",
                    side="right",
                    overlaying="y",
                    showgrid=False,
                    tickformat='.1f'
                ),
                legend=dict(
                    x=0.02,
                    y=0.98,
                    bgcolor="rgba(255,255,255,0.8)"
                )
            )
            
            st.plotly_chart(fig_cumulative, use_container_width=True)
            
            
            # Calcular análisis de atribución
            attribution = calculator.calculate_attribution_analysis()
            
            if not attribution.empty:
                # Gráfico de contribución por activo
                fig_attribution = px.bar(
                    attribution, 
                    x='Activo', 
                    y='Contribucion',
                    title="Contribución al Rendimiento por Activo"
                )
                fig_attribution.update_layout(template="plotly_white")
                st.plotly_chart(fig_attribution, use_container_width=True)
                
                # Tabla de atribución (oculta visualmente pero mantiene datos)
                # st.subheader("Contribución por Activo")
                
                # Formatear columnas
                attribution_display = attribution.copy()
                
                # Formatear porcentajes
                percentage_cols = ['Peso', 'Retorno_vs_Costo', 'Retorno_Total', 'Contribucion']
                for col in percentage_cols:
                    if col in attribution_display.columns:
                        attribution_display[col] = attribution_display[col].apply(lambda x: f"{x:.2%}")
                
                # Formatear precios
                price_cols = ['Valor_Actual', 'Precio_Promedio', 'Precio_Actual', 'Ganancias_Realizadas', 'Ingresos_Cupones_Dividendos', 'Amortizaciones', 'Ganancias_No_Realizadas', 'Inversion_Total']
                for col in price_cols:
                    if col in attribution_display.columns:
                        attribution_display[col] = attribution_display[col].apply(lambda x: f"${x:,.2f}")
                
                # Formatear cantidad
                if 'Cantidad' in attribution_display.columns:
                    attribution_display['Cantidad'] = attribution_display['Cantidad'].apply(lambda x: f"{x:,.0f}")
                
                # st.dataframe(attribution_display, use_container_width=True)
            
            
            # Estadísticas resumidas por activo (usando análisis de atribución corregido)
            asset_stats = calculator.calculate_attribution_analysis()
            if not asset_stats.empty:
                st.subheader("Estadísticas por Activo")
                
                # Formatear las columnas para mejor visualización
                asset_stats_display = asset_stats.copy()
                percentage_cols = ['Retorno_Total', 'Retorno_vs_Costo', 'Contribucion']
                
                for col in percentage_cols:
                    if col in asset_stats_display.columns:
                        asset_stats_display[col] = asset_stats_display[col].apply(lambda x: f"{x:.2%}")
                
                # Formatear precios
                    price_cols = ['Precio_Promedio', 'Precio_Actual', 'Valor_Actual', 'Ganancias_Realizadas', 'Ingresos_Cupones_Dividendos', 'Ganancias_No_Realizadas', 'Inversion_Total']
                for col in price_cols:
                    if col in asset_stats_display.columns:
                        asset_stats_display[col] = asset_stats_display[col].apply(lambda x: f"${x:,.2f}")
                
                # Formatear peso
                if 'Peso' in asset_stats_display.columns:
                    asset_stats_display['Peso'] = asset_stats_display['Peso'].apply(lambda x: f"{x:.1%}")
                
                # Formatear cantidad
                if 'Cantidad' in asset_stats_display.columns:
                    asset_stats_display['Cantidad'] = asset_stats_display['Cantidad'].apply(lambda x: f"{x:,.0f}")
                
                st.dataframe(asset_stats_display, use_container_width=True)
                
                # Gráfico de rendimientos por activo
                col1, col2 = st.columns(2)
                
                with col1:
                    fig_returns = px.bar(
                        asset_stats,
                        x='Activo',
                        y='Retorno_Total',
                        title="Rendimiento Total por Activo",
                        color='Retorno_Total',
                        color_continuous_scale=['#708090', '#87CEEB', '#B0C4DE', '#E0E0E0']
                    )
                    fig_returns.update_layout(yaxis_tickformat='.1%')
                    st.plotly_chart(fig_returns, use_container_width=True)
                
                with col2:
                    fig_contribution = px.bar(
                        asset_stats,
                        x='Activo',
                        y='Contribucion',
                        title="Contribución al Portfolio por Activo",
                        color='Contribucion',
                        color_continuous_scale=['#708090', '#87CEEB', '#B0C4DE', '#E0E0E0']
                    )
                    fig_contribution.update_layout(yaxis_tickformat='.1%')
                    st.plotly_chart(fig_contribution, use_container_width=True)
            
            # Performance histórica individual
            individual_performance = calculator.calculate_asset_cumulative_returns()
            if not individual_performance.empty:
                # Filtrar por fechas seleccionadas en el sidebar
                individual_performance['Fecha'] = pd.to_datetime(individual_performance['Fecha'])
                individual_performance_filtered = individual_performance[
                    (individual_performance['Fecha'] >= pd.to_datetime(start_date)) & 
                    (individual_performance['Fecha'] <= pd.to_datetime(end_date))
                ]
                
                if not individual_performance_filtered.empty:
                    st.subheader("Evolución de Rendimientos Acumulados")
                    
                    fig_individual = px.line(
                        individual_performance_filtered,
                        x='Fecha',
                        y='Rendimiento_Acumulado',
                        color='Activo',
                        title="Rendimiento Acumulado por Activo (Sin Flujos de Cash)",
                        labels={'Rendimiento_Acumulado': 'Rendimiento Acumulado'}
                    )
                fig_individual.update_layout(yaxis_tickformat='.1%')
                st.plotly_chart(fig_individual, use_container_width=True)
            
            # Comparación de precios (usar función original que incluye precios)
            individual_prices = calculator.calculate_individual_asset_performance()
            if not individual_prices.empty:
                # Filtrar por fechas seleccionadas en el sidebar
                individual_prices['Fecha'] = pd.to_datetime(individual_prices['Fecha'])
                individual_prices_filtered = individual_prices[
                    (individual_prices['Fecha'] >= pd.to_datetime(start_date)) & 
                    (individual_prices['Fecha'] <= pd.to_datetime(end_date))
                ]
                
                if not individual_prices_filtered.empty:
                    st.subheader("Evolución de Precios")
                    fig_prices = px.line(
                        individual_prices_filtered,
                        x='Fecha',
                        y='Precio',
                        color='Activo',
                        title="Evolución de Precios por Activo",
                        labels={'Precio': 'Precio'}
                    )
                st.plotly_chart(fig_prices, use_container_width=True)
            
            
            # Tabla de datos
            st.header("Datos de Rendimientos")
            
            if returns_df is not None and not returns_df.empty:
                # Formatear la tabla para mejor visualización
                display_df = returns_df.copy()
                
                # Calcular rendimiento acumulado
                if 'Rendimiento_Diario' in display_df.columns:
                    display_df['Rendimiento_Acumulado'] = (1 + display_df['Rendimiento_Diario']).cumprod() - 1
                
                # Agregar columnas de cupones, amortizaciones y dividendos por día
                # Inicializar con ceros
                display_df['Cupones_Diarios'] = 0.0
                display_df['Amortizaciones_Diarias'] = 0.0
                display_df['Dividendos_Diarios'] = 0.0
                
                # Calcular cupones, amortizaciones y dividendos por día
                if operaciones_filtered is not None:
                    for idx, row in display_df.iterrows():
                        fecha = pd.to_datetime(row['Fecha'])
                        
                        # Filtrar operaciones del día
                        ops_dia = operaciones_filtered[pd.to_datetime(operaciones_filtered['Fecha']).dt.date == fecha.date()]
                        
                        # Cupones
                        cupones_mask = ops_dia['Tipo'].str.strip().str.lower().str.contains('cupon|coupon', na=False)
                        display_df.loc[idx, 'Cupones_Diarios'] = ops_dia[cupones_mask]['Monto'].sum()
                        
                        # Amortizaciones
                        amort_mask = ops_dia['Tipo'].str.strip().str.lower().str.contains('amortizacion|amortization', na=False)
                        display_df.loc[idx, 'Amortizaciones_Diarias'] = ops_dia[amort_mask]['Monto'].sum()
                        
                        # Dividendos
                        div_mask = ops_dia['Tipo'].str.strip().str.lower().str.contains('dividendo|dividend', na=False)
                        display_df.loc[idx, 'Dividendos_Diarios'] = ops_dia[div_mask]['Monto'].sum()
                
                # Reordenar columnas: mantener todas las columnas originales y agregar las nuevas
                column_order = ['Fecha', 'Rendimiento_Diario', 'Rendimiento_Acumulado', 'Valor_Cartera', 'Daily_Cash_Flow', 
                               'Value_Without_Cash_Flow', 'Valor_Inicial',
                               'Cupones_Diarios', 'Amortizaciones_Diarias', 'Dividendos_Diarios']
                
                # Solo incluir columnas que existen
                available_columns = [col for col in column_order if col in display_df.columns]
                display_df = display_df[available_columns]
                
                # Formatear fechas
                if 'Fecha' in display_df.columns:
                    display_df['Fecha'] = pd.to_datetime(display_df['Fecha']).dt.strftime('%Y-%m-%d')
                
                # Formatear porcentajes
                percentage_cols = ['Rendimiento_Diario', 'Rendimiento_Acumulado']
                for col in percentage_cols:
                    if col in display_df.columns:
                        display_df[col] = display_df[col].apply(lambda x: f"{x:.2%}")
                
                # Formatear valores monetarios
                money_cols = ['Valor_Cartera', 'Daily_Cash_Flow', 'Value_Without_Cash_Flow', 'Valor_Inicial', 
                             'Cupones_Diarios', 'Amortizaciones_Diarias', 'Dividendos_Diarios']
                for col in money_cols:
                    if col in display_df.columns:
                        display_df[col] = display_df[col].apply(lambda x: f"${x:,.2f}")
                
                st.dataframe(display_df, use_container_width=True)
                
                # Botón de descarga en Excel
                # Crear archivo Excel en memoria
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    # Preparar datos para Excel (incluir rendimiento acumulado y nuevas columnas)
                    excel_df = returns_df.copy()
                    if 'Rendimiento_Diario' in excel_df.columns:
                        excel_df['Rendimiento_Acumulado'] = (1 + excel_df['Rendimiento_Diario']).cumprod() - 1
                    
                    # Agregar columnas de cupones, amortizaciones y dividendos por día
                    excel_df['Cupones_Diarios'] = 0.0
                    excel_df['Amortizaciones_Diarias'] = 0.0
                    excel_df['Dividendos_Diarios'] = 0.0
                    
                    # Calcular cupones, amortizaciones y dividendos por día
                    if operaciones_filtered is not None:
                        for idx, row in excel_df.iterrows():
                            fecha = pd.to_datetime(row['Fecha'])
                            
                            # Filtrar operaciones del día
                            ops_dia = operaciones_filtered[pd.to_datetime(operaciones_filtered['Fecha']).dt.date == fecha.date()]
                            
                            # Cupones
                            cupones_mask = ops_dia['Tipo'].str.strip().str.lower().str.contains('cupon|coupon', na=False)
                            excel_df.loc[idx, 'Cupones_Diarios'] = ops_dia[cupones_mask]['Monto'].sum()
                            
                            # Amortizaciones
                            amort_mask = ops_dia['Tipo'].str.strip().str.lower().str.contains('amortizacion|amortization', na=False)
                            excel_df.loc[idx, 'Amortizaciones_Diarias'] = ops_dia[amort_mask]['Monto'].sum()
                            
                            # Dividendos
                            div_mask = ops_dia['Tipo'].str.strip().str.lower().str.contains('dividendo|dividend', na=False)
                            excel_df.loc[idx, 'Dividendos_Diarios'] = ops_dia[div_mask]['Monto'].sum()
                    
                    # Reordenar columnas para Excel
                    column_order = ['Fecha', 'Rendimiento_Diario', 'Rendimiento_Acumulado', 'Valor_Cartera', 'Daily_Cash_Flow', 
                                   'Value_Without_Cash_Flow', 'Valor_Inicial',
                                   'Cupones_Diarios', 'Amortizaciones_Diarias', 'Dividendos_Diarios']
                    available_columns = [col for col in column_order if col in excel_df.columns]
                    excel_df = excel_df[available_columns]
                    
                    # Hoja con datos de rendimientos (sin formatear para mantener valores numéricos)
                    excel_df.to_excel(writer, sheet_name='Datos_Rendimientos', index=False)
                    
                    # Hoja con estadísticas resumidas
                    stats_data = {
                        'Métrica': ['Rendimiento Promedio Diario', 'Volatilidad Diaria', 'Rendimiento Total'],
                        'Valor': [
                            f"{returns_df['Rendimiento_Diario'].mean():.2%}" if 'Rendimiento_Diario' in returns_df.columns else "N/A",
                            f"{returns_df['Rendimiento_Diario'].std():.2%}" if 'Rendimiento_Diario' in returns_df.columns else "N/A",
                            f"{(1 + returns_df['Rendimiento_Diario']).prod() - 1:.2%}" if 'Rendimiento_Diario' in returns_df.columns else "N/A"
                        ]
                    }
                    stats_df = pd.DataFrame(stats_data)
                    stats_df.to_excel(writer, sheet_name='Estadisticas', index=False)
                
                output.seek(0)
                
                # Descargar archivo directamente
                st.download_button(
                    label="📥 Descargar Datos de Rendimientos (Excel)",
                    data=output.getvalue(),
                    file_name=f"datos_rendimientos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_excel_file"
                )
            else:
                st.warning("No hay datos de rendimientos disponibles.")
    
    else:
        # Mostrar información de ejemplo
        st.info("""
        ## Formato Esperado del Excel
        
        Tu archivo Excel debe contener dos hojas:
        
        ### Hoja "Operaciones"
        - **Fecha**: Fecha de la operación
        - **Tipo**: Compra, Venta, Cupón, Dividendo, Flujo
        - **Activo**: Nombre del activo
        - **Cantidad**: Cantidad de activos
        - **Precio**: Precio por unidad
        - **Monto**: Monto total de la operación
        
        ### Hoja "Precios"
        - **Fecha**: Fecha del precio
        - **Activo**: Nombre del activo
        - **Precio**: Precio de cierre
        """)
        
        # Mostrar ejemplo de datos
        st.subheader("Ejemplo de Datos")
        
        # Ejemplo de operaciones
        st.write("**Operaciones de Ejemplo:**")
        ejemplo_operaciones = pd.DataFrame({
            'Fecha': ['2024-01-01', '2024-01-15', '2024-02-01'],
            'Tipo': ['Compra', 'Cupón', 'Venta'],
            'Activo': ['BONO_GD30', 'BONO_GD30', 'BONO_GD30'],
            'Cantidad': [100, 0, 50],
            'Precio': [95.50, 0, 96.20],
            'Monto': [9550, 250, 4810]
        })
        st.dataframe(ejemplo_operaciones)
        
        # Ejemplo de precios
        st.write("**Precios de Ejemplo:**")
        ejemplo_precios = pd.DataFrame({
            'Fecha': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'Activo': ['BONO_GD30', 'BONO_GD30', 'BONO_GD30'],
            'Precio': [95.50, 95.80, 96.10]
        })
        st.dataframe(ejemplo_precios)

if __name__ == "__main__":
    main()
