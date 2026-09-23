from os import path
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import os


current_path = os.path.dirname(os.path.abspath(__file__))
# processed_climate_data/ lives under app/, not app/utils/ (this file's own directory)
DATA_DIR = os.path.join(os.path.dirname(current_path), 'processed_climate_data')

def get_windows(lat, lon, scenario, variable, value, models):
    windows = np.zeros((len(models), 12))
    if len(models) == 1:
        dataframe = pd.read_csv(os.path.join(DATA_DIR, scenario, variable, value, '{}.csv'.format(models[0])), sep=';', decimal=',')
        dist = (dataframe.lat - lat)**2 + (dataframe.lon - lon)**2
        idx = dist.argmin()
        windows = dataframe.values[idx, -12:].reshape(1, -1)
        index = models
    else:
        for i in range(len(models)):
            dataframe = pd.read_csv(os.path.join(DATA_DIR, scenario, variable, value, '{}.csv'.format(models[i])), sep=';', decimal=',')
            dist = (dataframe.lat - lat)**2 + (dataframe.lon - lon)**2
            idx = dist.argmin()
            windows[i, :] = dataframe.values[idx, -12:]
        
        mean = np.mean(windows, axis = 0).reshape(1, -1)
        windows = np.concatenate((windows, mean), axis = 0)
        index = models + ['Mean']

    columns = ['1951-1990', '1961-2000', '1971-2010', '1981-2020', '1991-2030', '2001-2040', '2011-2050', '2021-2060', '2031-2070', '2041-2080', '2051-2090', '2061-2100']
    df_windows = pd.DataFrame(windows, columns=columns, index=index)
    return df_windows


def get_figure(windows, value, variable, scenario):
    font = "Arial"
    TITLE_MAP = {
        "mean": "Mean value of",
        "cov": "Coefficient of variation of",
        "charactLSM": "Characteristic Value of",
        "fcLSM": "Factor of Change of"
    }

    Y_LABEL_MAP = {
        "mean": variable,
        "cov": f"COV ({variable})",
        "charactLSM": f"Characteristic {variable}",
        "fcLSM": f"FC ({variable})"
    }

    title_label = TITLE_MAP.get(value, value)

    UNITS_MAP = {
        "tasmax": "°C",
        "tasmin": "°C",
        "pr": "mm",
        "sfcwind": "m/s"
    }

    unit = UNITS_MAP.get(variable.lower(), "")
    y_label = f"[{unit}]" if unit else Y_LABEL_MAP.get(value, variable)

    VALUE_FMT = {
        "mean": "{:.2f}",      # 2 decimals
        "cov": "{:.2f}",
        "charactLSM": "{:.2f}",
        "fcLSM": "{:+.2f}"
    }

    fmt = VALUE_FMT.get(value, "{:.2f}")

    # ============================================================
    # 8. CREATION OF INTERACTIVE GRAPHS
    # ============================================================
    fig = go.Figure()
    
    x_values = windows.columns.tolist()

    if windows.values.shape[0] == 1:
        y_values = windows.values[0].tolist()
        fig.add_trace(go.Scatter(
            x=x_values,
            y=y_values,
            mode='lines+markers',  
            name=windows.index[0],
            line=dict(width=3),
            marker=dict(size=10),
            hovertemplate='%{y:.2f} ' + unit + '<extra></extra>'  # arrotonda a 2 decimali
    ))
    else:
        for i in range(windows.values.shape[0]-1):
            y_values = windows.values[i, :].tolist()
            fig.add_trace(go.Scatter(
                x=x_values,
                y=y_values,
                mode='lines+markers',  
                name=windows.index[i],
                line=dict(width=3),
                marker=dict(size=10),
                hovertemplate='%{y:.2f} ' + unit + '<extra></extra>'  # arrotonda a 2 decimali
            ))
        mean_y = windows.values[-1, :].tolist()
        fig.add_trace(go.Scatter(
                x=x_values,
                y=mean_y,
                mode='lines+markers',  
                name=windows.index[-1],
                line=dict(color='black', width=5),
                marker=dict(size=10),
                hovertemplate='%{y:.2f} ' + unit + '<extra></extra>'  # arrotonda a 2 decimali
            ))
    
    VARIABLE_TITLE_MAP = {
        "tasmax": "maximum temperature",
        "tasmin": "minimum temperature",
        "sfcwind": "wind speed",
        "pr": "precipitation"
    }
    variable_title = VARIABLE_TITLE_MAP.get(variable.lower(), variable)

    SCENARIO_MAP = {
        "4.5": "RCP4.5",
        "8.5": "RCP8.5"
    }

    scenario_label = SCENARIO_MAP.get(scenario.lower(), scenario.upper())

    fig.update_layout(
        title=dict(
            text=f"{title_label} {variable_title}<br>{scenario_label}",
            x=0.5,
            xanchor='center',
            font=dict(size=28, family=font)
        ),
        xaxis=dict(
            title=dict(
                text="Time-windows",
                font=dict(size=24, family=font)
            ),
            tickangle=25,
            tickfont=dict(size=20, family=font),
            showgrid=True,
            gridcolor="lightgrey",
            gridwidth=1,
            zeroline=False
        ),
        yaxis=dict(
            title=dict(
                text=y_label,
                font=dict(size=24, family=font)
            ),
            tickfont=dict(size=20, family=font),
            showgrid=True,
            gridcolor="lightgrey",
            gridwidth=1,
            zeroline=False
        ),
        template="simple_white",
        autosize=True,
    )
    return fig


def get_figure_and_table(lat, lon, scenario, variable, value, models):
    try:
        windows = get_windows(lat, lon, scenario, variable, value, models)
        figure = get_figure(windows, value, variable, scenario)
        return figure, windows
    except Exception as e:
        print(f"Error in get_figure_and_table: {e}")
        return None, None


