"""
Módulo para cálculos avanzados de cartera de inversión
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

class PortfolioCalculator:
    """Calculadora avanzada de métricas de cartera"""
    
    def __init__(self, operaciones: pd.DataFrame, precios: pd.DataFrame, start_date: pd.Timestamp = None):
        self.operaciones = operaciones.copy()
        self.precios = precios.copy()
        self.start_date = start_date
        self.portfolio_data = None
        self.daily_returns = None
        self.metrics = None
        
        # Procesar datos
        self._process_data()
    
    def _process_data(self):
        """Procesar y limpiar los datos de entrada"""
        # Debug removido para limpiar la salida
        
        # Convertir fechas
        self.operaciones['Fecha'] = pd.to_datetime(self.operaciones['Fecha'])
        
        # Limpiar espacios en blanco de las columnas de texto
        if 'Tipo' in self.operaciones.columns:
            self.operaciones['Tipo'] = self.operaciones['Tipo'].str.strip()
        if 'Activo' in self.operaciones.columns:
            self.operaciones['Activo'] = self.operaciones['Activo'].str.strip()
        
        # Normalizar nombres de columnas de operaciones
        if 'Operacion' in self.operaciones.columns and 'Tipo' not in self.operaciones.columns:
            self.operaciones['Tipo'] = self.operaciones['Operacion']
        if 'Nominales' in self.operaciones.columns and 'Cantidad' not in self.operaciones.columns:
            self.operaciones['Cantidad'] = self.operaciones['Nominales']
        if 'Valor' in self.operaciones.columns and 'Monto' not in self.operaciones.columns:
            self.operaciones['Monto'] = self.operaciones['Valor']
        
        # Mapear precio de concertación si existe
        if 'Precio_Concertacion' in self.operaciones.columns:
            # Ya está mapeado correctamente
            pass
        elif 'Precio' in self.operaciones.columns:
            self.operaciones['Precio_Concertacion'] = self.operaciones['Precio']
        
        # Procesar precios (estructura: fechas en columna A, activos en fila 1)
        if 'Activo' in self.precios.columns and 'Precio' in self.precios.columns:
            # Formato largo: Fecha, Activo, Precio
            self.precios['Fecha'] = pd.to_datetime(self.precios['Fecha'])
            self.precios = self.precios.sort_values('Fecha')
        else:
            # Formato ancho: fechas en columna A, activos en fila 1
            # Asegurar que la primera columna sea 'Fecha'
            if self.precios.columns[0] != 'Fecha':
                fecha_col = self.precios.columns[0]  # Primera columna (fechas)
                self.precios = self.precios.rename(columns={fecha_col: 'Fecha'})
            
            self.precios['Fecha'] = pd.to_datetime(self.precios['Fecha'])
            
            # Convertir a formato largo (melt)
            self.precios = self.precios.melt(
                id_vars=['Fecha'], 
                var_name='Activo', 
                value_name='Precio'
            )
            self.precios = self.precios.dropna()  # Eliminar filas con NaN
            self.precios = self.precios.sort_values('Fecha')
        
        # Ordenar operaciones por fecha
        self.operaciones = self.operaciones.sort_values('Fecha')
        
        # Crear índice de fechas únicas
        min_date = self.precios['Fecha'].min()
        max_date = self.precios['Fecha'].max()
        
        # Si se especifica una fecha de inicio, usarla como mínimo
        if self.start_date is not None:
            min_date = max(min_date, self.start_date)
            # Asegurar que siempre haya al menos la fecha de inicio
            if min_date > max_date:
                max_date = min_date
        
        self.date_range = pd.date_range(
            start=min_date,
            end=max_date,
            freq='D'
        )
    
    def _get_initial_positions(self, start_date: pd.Timestamp) -> dict:
        """Obtener las posiciones iniciales a una fecha específica"""
        # Obtener todas las operaciones hasta la fecha de inicio
        ops_until_start = self.operaciones[self.operaciones['Fecha'] < start_date]
        
        positions = {}
        for _, op in ops_until_start.iterrows():
            asset = op['Activo']
            tipo = str(op['Tipo']).strip()
            cantidad = op['Cantidad']
            precio = op['Precio_Concertacion']
            
            if asset not in positions:
                positions[asset] = {'cantidad': 0, 'precio_promedio': 0}
            
            if tipo == 'Compra':
                old_qty = positions[asset]['cantidad']
                old_avg = positions[asset]['precio_promedio']
                
                new_qty = old_qty + cantidad
                if new_qty > 0:
                    new_avg = (old_qty * old_avg + cantidad * precio) / new_qty
                else:
                    new_avg = precio
                
                positions[asset]['cantidad'] = new_qty
                positions[asset]['precio_promedio'] = new_avg
                
            elif tipo == 'Venta':
                positions[asset]['cantidad'] -= cantidad
        
        return positions

    def calculate_portfolio_value(self) -> pd.DataFrame:
        """Calcular el valor de la cartera por día"""
        portfolio_values = []
        
        # Obtener posiciones iniciales si hay fecha de inicio
        initial_positions = {}
        if self.start_date is not None:
            initial_positions = self._get_initial_positions(self.start_date)
        
        for date in self.date_range:
            # Obtener operaciones hasta esta fecha
            if self.start_date is not None:
                # Si hay fecha de inicio, solo considerar operaciones desde esa fecha
                ops_until_date = self.operaciones[
                    (self.operaciones['Fecha'] <= date) & 
                    (self.operaciones['Fecha'] >= self.start_date)
                ]
            else:
                ops_until_date = self.operaciones[self.operaciones['Fecha'] <= date]
            
            # Calcular posición actual de cada activo
            # Empezar con las posiciones iniciales si existen
            positions = {}
            for asset, pos in initial_positions.items():
                positions[asset] = {
                    'cantidad': pos['cantidad'],
                    'precio_promedio': pos['precio_promedio']
                }
            
            cash_flow = 0
            
            # Procesar operaciones solo si existen
            if not ops_until_date.empty:
                for _, op in ops_until_date.iterrows():
                    asset = op['Activo']
                    tipo = str(op['Tipo']).strip()  # Limpiar espacios en blanco
                    cantidad = op['Cantidad']
                    precio = op['Precio_Concertacion']
                    monto = op['Monto']
                    
                    if asset not in positions:
                        positions[asset] = {'cantidad': 0, 'precio_promedio': 0}
                    
                    if tipo == 'Compra':
                        # Compra: ingresa monto a la cartera + se compra el activo
                        # Actualizar posición del activo
                        old_qty = positions[asset]['cantidad']
                        old_avg = positions[asset]['precio_promedio']
                        
                        new_qty = old_qty + cantidad
                        if new_qty > 0:
                            new_avg = (old_qty * old_avg + cantidad * precio) / new_qty
                        else:
                            new_avg = precio
                        
                        positions[asset]['cantidad'] = new_qty
                        positions[asset]['precio_promedio'] = new_avg
                        
                        # No afecta cash_flow neto (ingresa monto, sale monto por compra)
                        
                    elif tipo == 'Venta':
                        # Venta: sale monto de la cartera + se vende el activo
                        # Reducir posición
                        positions[asset]['cantidad'] -= cantidad
                        # No afecta cash_flow neto (ingresa monto por venta, sale monto de cartera)
                    
                    elif any(keyword in tipo.strip().lower() for keyword in ['cupón', 'cupon', 'dividendo', 'coupon', 'dividend', 'interes', 'interest']):
                        # Cupón/Dividendo: ingresa por cobro, luego sale de la cartera
                        # No afecta cash_flow neto, pero es ganancia realizada
                        # El monto se suma al rendimiento del activo y de la cartera
                        # Se considera outflow (salida de efectivo de la cartera)
                        pass
                    
                    elif any(keyword in tipo.strip().lower() for keyword in ['amortización', 'amortizacion', 'amortization']):
                        # Amortización: no modifica el nominal, se suma como ganancia realizada
                        # Es un outflow para la cartera (salida de dinero)
                        # No afecta la cantidad de títulos, solo el flujo de efectivo
                        pass
                    
                    elif tipo == 'Flujo':
                        # Flujo de caja directo (aportes/retiros netos)
                        cash_flow += monto
            
            # Calcular valor de la cartera (solo valor de mercado de activos)
            portfolio_value = 0  # Empezar en 0, no incluir cash
            
            for asset, pos in positions.items():
                if pos['cantidad'] > 0:
                    # Obtener precio actual del activo
                    asset_prices = self.precios[
                        (self.precios['Activo'] == asset) & 
                        (self.precios['Fecha'] <= date)
                    ]
                    
                    if not asset_prices.empty:
                        current_price = asset_prices.iloc[-1]['Precio']
                        asset_value = pos['cantidad'] * current_price
                        portfolio_value += asset_value
            
            
            portfolio_values.append({
                'Fecha': date,
                'Valor_Cartera': portfolio_value,
                'Flujo_Cash': cash_flow
            })
        
        return pd.DataFrame(portfolio_values)
    
    def calculate_daily_returns(self) -> pd.DataFrame:
        """Calcular rendimientos diarios de la cartera excluyendo flujos de cash"""
        if self.portfolio_data is None:
            self.portfolio_data = self.calculate_portfolio_value()
        
        # Obtener valores de la cartera
        portfolio_data = self.portfolio_data.copy()
        
        # Calcular rendimientos excluyendo flujos de cash
        returns = []
        cash_flows = []
        values_without_cash_flow = []
        initial_value = None
        previous_value = None
        
        for i, row in portfolio_data.iterrows():
            current_value = row['Valor_Cartera']
            current_date = row['Fecha']
            
            # Calcular flujos de cash del día
            daily_operations = self.operaciones[self.operaciones['Fecha'] == current_date]
            daily_purchases = daily_operations[daily_operations['Tipo'].str.strip() == 'Compra']['Monto'].sum()
            daily_sales = daily_operations[daily_operations['Tipo'].str.strip() == 'Venta']['Monto'].sum()
            daily_coupons = daily_operations[daily_operations['Tipo'].str.strip().isin(['Cupón', 'Cupon', 'Dividendo'])]['Monto'].sum()
            daily_amortizations = daily_operations[daily_operations['Tipo'].str.strip().str.lower().str.contains('|'.join(['amortización', 'amortizacion', 'amortization']), na=False)]['Monto'].sum()
            daily_cash_flow = daily_purchases - daily_sales - daily_coupons - daily_amortizations
            
            # El primer día con valor > 0 es nuestro valor inicial
            if initial_value is None and current_value > 0:
                initial_value = current_value
                daily_return = 0.0  # Primer día = 0% rendimiento
                previous_value = current_value
            elif previous_value is None or previous_value == 0:
                # Días sin activos en cartera
                daily_return = 0.0
                if current_value > 0:
                    previous_value = current_value
            else:
                # Calcular rendimiento excluyendo flujos de cash
                # El rendimiento es solo por movimientos de precios de activos existentes
                value_without_cash_flow = current_value - daily_cash_flow
                daily_return = (value_without_cash_flow - previous_value) / previous_value
                previous_value = current_value
            
            returns.append(daily_return)
            cash_flows.append(daily_cash_flow)
            values_without_cash_flow.append(current_value - daily_cash_flow)
        
        # Crear DataFrame
        returns_df = pd.DataFrame({
            'Fecha': portfolio_data['Fecha'],
            'Rendimiento_Diario': returns,
            'Valor_Cartera': portfolio_data['Valor_Cartera'],
            'Daily_Cash_Flow': cash_flows,
            'Value_Without_Cash_Flow': values_without_cash_flow
        })
        
        # Filtrar valores válidos (donde hay activos en cartera)
        returns_df = returns_df[returns_df['Valor_Cartera'] > 0].copy()
        
        # Agregar valor inicial para referencia (usar el primer valor válido si initial_value es None)
        if initial_value is None and not returns_df.empty:
            initial_value = returns_df['Valor_Cartera'].iloc[0]
        
        returns_df['Valor_Inicial'] = initial_value if initial_value is not None else 0
        
        self.daily_returns = returns_df
        return returns_df
    
    def calculate_metrics(self, risk_free_rate: float = 0.05) -> Dict:
        """Calcular métricas de performance"""
        if self.daily_returns is None:
            self.calculate_daily_returns()
        
        returns = self.daily_returns['Rendimiento_Diario']
        
        # Calcular rendimiento total usando el producto acumulado de rendimientos diarios
        # Esta es la fórmula correcta que incluye automáticamente cupones y dividendos
        total_return = (1 + returns).prod() - 1
        
        days = len(returns)
        annualized_return = (1 + total_return) ** (252 / days) - 1 if days > 0 else 0
        
        # Volatilidad
        volatility = returns.std() * np.sqrt(252)
        
        # Sharpe ratio
        excess_return = annualized_return - risk_free_rate
        sharpe_ratio = excess_return / volatility if volatility > 0 else 0
        
        # Drawdown
        cumulative_returns = (1 + returns).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Métricas adicionales
        positive_days = (returns > 0).sum()
        win_rate = positive_days / days
        
        # Calmar ratio
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # Sortino ratio (solo desviación negativa)
        negative_returns = returns[returns < 0]
        downside_volatility = negative_returns.std() * np.sqrt(252) if len(negative_returns) > 0 else 0
        sortino_ratio = excess_return / downside_volatility if downside_volatility > 0 else 0
        
        # VaR (Value at Risk) 95%
        var_95 = np.percentile(returns, 5)
        
        # CVaR (Conditional Value at Risk) 95%
        cvar_95 = returns[returns <= var_95].mean()
        
        self.metrics = {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'var_95': var_95,
            'cvar_95': cvar_95,
            'total_days': days,
            'positive_days': positive_days
        }
        
        return self.metrics
    
    def calculate_benchmark_comparison(self, benchmark_returns: pd.Series) -> Dict:
        """Comparar con un benchmark"""
        if self.daily_returns is None:
            self.calculate_daily_returns()
        
        portfolio_returns = self.daily_returns['Rendimiento_Diario']
        
        # Alinear fechas
        common_dates = portfolio_returns.index.intersection(benchmark_returns.index)
        portfolio_aligned = portfolio_returns.loc[common_dates]
        benchmark_aligned = benchmark_returns.loc[common_dates]
        
        # Calcular métricas de comparación
        excess_returns = portfolio_aligned - benchmark_aligned
        
        # Alpha (intercepto de la regresión)
        beta = np.cov(portfolio_aligned, benchmark_aligned)[0, 1] / np.var(benchmark_aligned)
        alpha = portfolio_aligned.mean() - beta * benchmark_aligned.mean()
        
        # Tracking error
        tracking_error = excess_returns.std() * np.sqrt(252)
        
        # Information ratio
        information_ratio = excess_returns.mean() / excess_returns.std() if excess_returns.std() > 0 else 0
        
        return {
            'alpha': alpha,
            'beta': beta,
            'tracking_error': tracking_error,
            'information_ratio': information_ratio,
            'excess_return': excess_returns.mean()
        }
    
    def calculate_attribution_analysis(self) -> pd.DataFrame:
        """Análisis de atribución por activo"""
        if self.portfolio_data is None:
            self.portfolio_data = self.calculate_portfolio_value()

        # Obtener activos únicos que estuvieron en cartera durante el período de análisis
        if self.start_date is not None:
            # Si hay fecha de inicio, considerar:
            # 1. Activos con operaciones desde esa fecha
            # 2. Activos que estaban en cartera antes de esa fecha (posiciones iniciales)
            period_operations = self.operaciones[self.operaciones['Fecha'] >= self.start_date]
            period_assets = set(period_operations['Activo'].unique())
            
            # Agregar activos que estaban en cartera antes de la fecha de inicio
            initial_positions = self._get_initial_positions(self.start_date)
            initial_assets = set(initial_positions.keys())
            
            # Combinar ambos conjuntos
            assets = list(period_assets.union(initial_assets))
        else:
            # Si no hay fecha de inicio, considerar todos los activos
            assets = self.operaciones['Activo'].unique()
        
        attribution_data = []
        
        for asset in assets:
            # Obtener operaciones del activo
            asset_ops = self.operaciones[self.operaciones['Activo'] == asset]
            
            # Usar la misma lógica que calculate_positions_summary para consistencia
            total_invested = 0  # Inversión total original (solo compras)
            current_quantity = 0  # Cantidad actual en cartera
            weighted_price_sum = 0  # Suma ponderada para precio promedio
            realized_gains = 0  # Ganancias realizadas acumuladas
            coupon_dividend_income = 0  # Ingresos por cupones y dividendos
            amortizations = 0  # Amortizaciones (salida de capital, no ganancia realizada)
            
            # Procesar operaciones históricamente
            for _, op in asset_ops.iterrows():
                tipo = str(op['Tipo']).strip()
                cantidad = op['Cantidad']
                precio_op = op['Precio_Concertacion']
                monto = op['Monto']
                
                # Debug removido para limpiar la salida
                
                if tipo == 'Compra':
                    total_invested += monto
                    current_quantity += cantidad
                    weighted_price_sum += cantidad * precio_op
                elif tipo == 'Venta':
                    if current_quantity > 0:
                        # Calcular precio promedio al momento de la venta
                        avg_price_at_sale = weighted_price_sum / current_quantity
                        # Calcular ganancia/pérdida de la venta
                        sale_gain = (precio_op - avg_price_at_sale) * cantidad
                        realized_gains += sale_gain
                    
                    current_quantity -= cantidad
                    if current_quantity <= 0:
                        current_quantity = 0
                        weighted_price_sum = 0
                    else:
                        # Ajustar suma ponderada proporcionalmente
                        weighted_price_sum = (weighted_price_sum / (current_quantity + cantidad)) * current_quantity
                
                elif any(keyword in tipo.strip().lower() for keyword in ['cupón', 'cupon', 'dividendo', 'coupon', 'dividend', 'interes', 'interest']):
                    # Cupón/Dividendo: se suma al rendimiento del activo
                    # No afecta la cantidad ni el precio promedio
                    coupon_dividend_income += monto
                
                elif any(keyword in tipo.strip().lower() for keyword in ['amortización', 'amortizacion', 'amortization']):
                    # Amortización: no modifica el nominal, es una salida de capital
                    # NO es una ganancia realizada, se contabiliza por separado
                    # Es un outflow para la cartera (salida de dinero)
                    amortizations += monto
            
            # Incluir todos los activos que tuvieron operaciones, incluso si ya fueron vendidos completamente
            if total_invested > 0:  # Solo incluir si hubo inversión en el activo
                # Calcular precio promedio de compra (solo para activos que aún tienen cantidad)
                avg_purchase_price = weighted_price_sum / current_quantity if current_quantity > 0 else 0
                
                # Obtener precio actual (verificar que existan datos)
                asset_prices = self.precios[self.precios['Activo'] == asset]
                current_price = 0
                if not asset_prices.empty and len(asset_prices) > 0:
                    current_price = asset_prices['Precio'].iloc[-1]
                
                # Calcular valor actual de la posición
                current_value = current_quantity * current_price
                
                # Calcular ganancia/pérdida no realizada (solo si hay cantidad actual)
                unrealized_gain = current_value - (current_quantity * avg_purchase_price) if current_quantity > 0 else 0
                
                # Calcular ganancia total (realizada + no realizada + cupones/dividendos + amortizaciones)
                total_gain = realized_gains + unrealized_gain + coupon_dividend_income + amortizations
                
                # Calcular retorno total
                total_return = total_gain / total_invested if total_invested > 0 else 0
                
                # Calcular contribución al portfolio
                portfolio_value = self.portfolio_data['Valor_Cartera'].iloc[-1] if not self.portfolio_data.empty and len(self.portfolio_data) > 0 else 1
                weight = current_value / portfolio_value if portfolio_value > 0 else 0
                
                # Incluir cupones/dividendos en las ganancias realizadas para mostrar el impacto total
                total_realized_gains = realized_gains + coupon_dividend_income
                
                attribution_data.append({
                    'Activo': asset,
                    'Peso': weight,
                    'Retorno_vs_Costo': total_return,
                    'Retorno_Total': total_return,
                    'Contribucion': weight * total_return,
                    'Valor_Actual': current_value,
                    'Precio_Promedio': avg_purchase_price,
                    'Precio_Actual': current_price,
                    'Cantidad': current_quantity,
                    'Ganancias_Realizadas': total_realized_gains,
                    'Ganancias_No_Realizadas': unrealized_gain,
                    'Ingresos_Cupones_Dividendos': coupon_dividend_income,
                    'Amortizaciones': amortizations,
                    'Inversion_Total': total_invested
                })
        
        return pd.DataFrame(attribution_data)
    
    def calculate_asset_cumulative_returns(self) -> pd.DataFrame:
        """Calcular rendimientos acumulados por activo excluyendo flujos de cash"""
        if self.portfolio_data is None:
            self.portfolio_data = self.calculate_portfolio_value()
        
        # Obtener activos únicos
        assets = self.operaciones['Activo'].unique()
        assets = [asset for asset in assets if pd.notna(asset)]
        
        asset_returns_data = []
        
        for asset in assets:
            # Obtener operaciones del activo
            asset_ops = self.operaciones[self.operaciones['Activo'] == asset].sort_values('Fecha')
            
            # Obtener precios del activo
            asset_prices = self.precios[self.precios['Activo'] == asset].sort_values('Fecha')
            
            if asset_prices.empty:
                continue
            
            # Calcular rendimientos diarios del activo excluyendo flujos de cash
            returns = []
            dates = []
            previous_value = None
            initial_value = None
            
            for _, row in asset_prices.iterrows():
                current_date = row['Fecha']
                current_price = row['Precio']
                
                # Calcular cantidad actual del activo en esta fecha
                current_quantity = 0
                for _, op in asset_ops.iterrows():
                    if op['Fecha'] <= current_date:
                        if str(op['Tipo']).strip() == 'Compra':
                            current_quantity += op['Cantidad']
                        elif str(op['Tipo']).strip() == 'Venta':
                            current_quantity -= op['Cantidad']
                
                current_quantity = max(0, current_quantity)  # No puede ser negativo
                current_value = current_quantity * current_price
                
                # Calcular flujos de cash del día para este activo
                daily_ops = asset_ops[asset_ops['Fecha'] == current_date]
                daily_purchases = daily_ops[daily_ops['Tipo'].str.strip() == 'Compra']['Monto'].sum()
                daily_sales = daily_ops[daily_ops['Tipo'].str.strip() == 'Venta']['Monto'].sum()
                daily_coupons = daily_ops[daily_ops['Tipo'].str.strip().str.lower().str.contains('|'.join(['cupón', 'cupon', 'dividendo', 'coupon', 'dividend', 'interes', 'interest']), na=False)]['Monto'].sum()
                daily_amortizations = daily_ops[daily_ops['Tipo'].str.strip().str.lower().str.contains('|'.join(['amortización', 'amortizacion', 'amortization']), na=False)]['Monto'].sum()
                daily_cash_flow = daily_purchases - daily_sales - daily_coupons - daily_amortizations
                
                if previous_value is None and current_value > 0:
                    initial_value = current_value
                    daily_return = 0.0
                    previous_value = current_value
                elif previous_value is None or previous_value == 0:
                    daily_return = 0.0
                    if current_value > 0:
                        previous_value = current_value
                else:
                    # Calcular rendimiento excluyendo flujos de cash
                    value_without_cash_flow = current_value - daily_cash_flow
                    daily_return = (value_without_cash_flow - previous_value) / previous_value
                    previous_value = current_value
                
                returns.append(daily_return)
                dates.append(current_date)
            
            # Calcular rendimiento acumulado
            if returns:
                cumulative_returns = [(1 + r) for r in returns]
                cumulative_return = 1.0
                for i, cr in enumerate(cumulative_returns):
                    cumulative_return *= cr
                    asset_returns_data.append({
                        'Fecha': dates[i],
                        'Activo': asset,
                        'Rendimiento_Diario': returns[i],
                        'Rendimiento_Acumulado': cumulative_return - 1
                    })
        
        return pd.DataFrame(asset_returns_data)
    
    def calculate_individual_asset_performance(self) -> pd.DataFrame:
        """Calcular rendimiento individual de cada activo a lo largo del tiempo"""
        # Obtener activos únicos
        assets = self.operaciones['Activo'].unique()
        
        # Crear DataFrame con fechas únicas
        dates = self.precios['Fecha'].unique()
        dates = sorted(dates)
        
        performance_data = []
        
        for asset in assets:
            # Obtener precios del activo
            asset_prices = self.precios[self.precios['Activo'] == asset].copy()
            asset_prices = asset_prices.sort_values('Fecha')
            
            if not asset_prices.empty:
                # Calcular precio promedio de compra y rendimiento real del activo
                asset_ops = self.operaciones[self.operaciones['Activo'] == asset].sort_values('Fecha')
                
                # Variables para tracking de posición
                total_invested = 0
                total_quantity = 0
                weighted_price_sum = 0
                realized_gains = 0  # Ganancias realizadas por ventas
                coupon_dividend_income = 0  # Ingresos por cupones y dividendos
                amortizations = 0  # Amortizaciones (salida de capital, no ganancia realizada)
                
                # Procesar operaciones históricamente
                for _, op in asset_ops.iterrows():
                    tipo_limpio = str(op['Tipo']).strip()
                    if tipo_limpio == 'Compra':
                        total_invested += op['Monto']
                        total_quantity += op['Cantidad']
                        weighted_price_sum += op['Cantidad'] * op['Precio_Concertacion']
                    elif tipo_limpio == 'Venta':
                        # Calcular ganancia/pérdida de la venta
                        if total_quantity > 0:
                            avg_purchase_price = weighted_price_sum / total_quantity
                            sale_gain = (op['Precio_Concertacion'] - avg_purchase_price) * op['Cantidad']
                            realized_gains += sale_gain
                        
                        # Reducir posición
                        total_quantity -= op['Cantidad']
                        if total_quantity <= 0:
                            # Si se vendió todo, reiniciar
                            total_invested = 0
                            weighted_price_sum = 0
                    
                    elif any(keyword in tipo_limpio.lower() for keyword in ['cupón', 'cupon', 'dividendo', 'coupon', 'dividend', 'interes', 'interest']):
                        # Cupón/Dividendo: se suma al rendimiento del activo
                        # No afecta la cantidad ni el precio promedio
                        coupon_dividend_income += op['Monto']
                    
                    elif any(keyword in tipo_limpio.lower() for keyword in ['amortización', 'amortizacion', 'amortization']):
                        # Amortización: no modifica el nominal, es una salida de capital
                        # NO es una ganancia realizada, se contabiliza por separado
                        # Es un outflow para la cartera (salida de dinero)
                        amortizations += op['Monto']
                
                # Calcular precio promedio actual (solo para cantidad restante)
                if total_quantity > 0:
                    avg_purchase_price = weighted_price_sum / total_quantity
                else:
                    avg_purchase_price = 0
                
                # Calcular rendimientos considerando ganancias realizadas
                for _, row in asset_prices.iterrows():
                    # Calcular rendimiento total del activo (incluyendo ventas realizadas)
                    total_invested_original = 0
                    total_quantity_original = 0
                    
                    # Recalcular inversión total original (solo compras)
                    for _, op in asset_ops.iterrows():
                        tipo_limpio = str(op['Tipo']).strip()
                        if tipo_limpio == 'Compra':
                            total_invested_original += op['Monto']
                            total_quantity_original += op['Cantidad']
                    
                    if total_invested_original > 0:
                        # Rendimiento total = (Valor actual + Ganancias realizadas + Cupones/Dividendos + Amortizaciones - Inversión original) / Inversión original
                        current_value = total_quantity * row['Precio'] if total_quantity > 0 else 0
                        total_return = (current_value + realized_gains + coupon_dividend_income + amortizations - total_invested_original) / total_invested_original
                    else:
                        total_return = 0
                    
                    # Incluir cupones/dividendos en las ganancias realizadas para mostrar el impacto total
                    total_realized_gains = realized_gains + coupon_dividend_income
                    
                    # Calcular rendimiento diario real (cambio de precio del activo)
                    if len(performance_data) > 0:
                        # Obtener precio anterior
                        previous_price = performance_data[-1]['Precio']
                        daily_return = (row['Precio'] - previous_price) / previous_price if previous_price > 0 else 0
                    else:
                        daily_return = 0  # Primer día
                    
                    performance_data.append({
                        'Fecha': row['Fecha'],
                        'Activo': asset,
                        'Precio': row['Precio'],
                        'Precio_Promedio_Compra': avg_purchase_price if avg_purchase_price > 0 else 0,
                        'Rendimiento_Diario': daily_return,
                        'Rendimiento_Acumulado': total_return,
                        'Ganancias_Realizadas': total_realized_gains,
                        'Ingresos_Cupones_Dividendos': coupon_dividend_income,
                        'Amortizaciones': amortizations,
                        'Cantidad_Actual': total_quantity,
                        'Valor_Actual': total_quantity * row['Precio'] if total_quantity > 0 else 0,
                        'Inversion_Original': total_invested_original
                    })
        
        return pd.DataFrame(performance_data)
    
    def get_asset_summary_stats(self) -> pd.DataFrame:
        """Obtener estadísticas resumidas de cada activo"""
        individual_performance = self.calculate_individual_asset_performance()
        
        if individual_performance.empty:
            return pd.DataFrame()
        
        summary_stats = []
        
        for asset in individual_performance['Activo'].unique():
            asset_data = individual_performance[individual_performance['Activo'] == asset]
            
            if not asset_data.empty:
                returns = asset_data['Rendimiento_Diario'].dropna()
                
                if len(returns) > 0:
                    summary_stats.append({
                        'Activo': asset,
                        'Rendimiento_Total': asset_data['Rendimiento_Acumulado'].iloc[-1],
                        'Rendimiento_Anualizado': (1 + asset_data['Rendimiento_Acumulado'].iloc[-1]) ** (252 / len(asset_data)) - 1,
                        'Volatilidad_Anualizada': returns.std() * np.sqrt(252),
                        'Sharpe_Ratio': (returns.mean() * 252) / (returns.std() * np.sqrt(252)) if returns.std() > 0 else 0,
                        'Rendimiento_Maximo': returns.max(),
                        'Rendimiento_Minimo': returns.min(),
                        'Dias_Positivos': (returns > 0).sum(),
                        'Dias_Negativos': (returns < 0).sum(),
                        'Precio_Inicial': asset_data['Precio'].iloc[0],
                        'Precio_Final': asset_data['Precio'].iloc[-1],
                        'Precio_Maximo': asset_data['Precio'].max(),
                        'Precio_Minimo': asset_data['Precio'].min()
                    })
        
        return pd.DataFrame(summary_stats)
    
    def get_performance_summary(self) -> pd.DataFrame:
        """Resumen de performance por período"""
        if self.daily_returns is None:
            self.calculate_daily_returns()
        
        # Crear columna de año-mes como string para evitar problemas con Period
        self.daily_returns['Año_Mes'] = self.daily_returns['Fecha'].dt.strftime('%Y-%m')
        
        # Agrupar por mes
        monthly_returns = self.daily_returns.groupby('Año_Mes')['Rendimiento_Diario'].apply(
            lambda x: (1 + x).prod() - 1
        )
        
        # Calcular métricas mensuales
        monthly_volatility = self.daily_returns.groupby('Año_Mes')['Rendimiento_Diario'].std() * np.sqrt(252)
        
        monthly_metrics = pd.DataFrame({
            'Retorno_Mensual': monthly_returns,
            'Volatilidad_Mensual': monthly_volatility,
            'Sharpe_Mensual': monthly_returns / monthly_volatility
        })
        
        # Convertir el índice a datetime para mejor visualización
        monthly_metrics.index = pd.to_datetime(monthly_metrics.index + '-01')
        monthly_metrics.index.name = 'Fecha'
        
        return monthly_metrics
