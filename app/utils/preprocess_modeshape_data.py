'''Preprocessing functions for mode shape data handling in digital twinning.'''
import sys
import os
parent_dir = os.path.abspath("../../libraries/surrogate_modelling_organized")
sys.path.insert(0, parent_dir)

import pyuff
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from uncertain_variables.variable_set import VariableSet
from uncertain_variables.variable import Variable
from uncertain_variables.distributions import UniformDistribution
import seaborn as sns
import re

def compute_dot_products(input_eigenvectors : np.ndarray, reference_eigenvectors: np.ndarray) -> np.ndarray:
    '''
    Calculates dot products between eigenvectors and reference eigenvectors.
    
    Parameters
    ----------
    input_eigenvectors : ndarray of shape (n_samples, n_nodes)
        Array of eigenvectors.
        
    reference_eigenvectors : ndarray of shape (n_clusters, n_nodes)
        Array of reference_eigenvectors.
        
    Returns
    -------
    dot_product : ndarray of shape (n_samples, 1, n_clusters)
        Matrix of dot products between input eigenvectors and typical eigenvectors.
    '''
    
    num_of_samples = input_eigenvectors.shape[0]
    num_of_modes = input_eigenvectors.shape[1]
    num_of_components = input_eigenvectors.shape[2]
    input_eigenvectors_reshaped = input_eigenvectors.reshape(-1, num_of_components)
    dot_products = np.dot(input_eigenvectors_reshaped, reference_eigenvectors.T)
    dot_products = dot_products.reshape(num_of_samples, num_of_modes, -1)
    return dot_products

def flip_eigenvectors(input_eigenvectors: np.ndarray, reference_eigenvectors: np.ndarray | None = None) -> np.ndarray:
    '''
    Flips eigenvectors by clusters to the direction of the typical eigenvectors.
    
    Parameters
    ----------
    input_eigenvectors : ndarray of shape (n_samples, n_nodes)
        Array of eigenvectors.
        
    reference_eigenvectors : ndarray of shape (n_clusters, n_nodes), default=None
        Array of reference_eigenvectors.
    
    Returns
    -------
    flipped_eigenvectors : ndarray
        Flipped versions of the input eigenvectors.
    '''
    
    input_eigenvectors = np.expand_dims(input_eigenvectors, axis=1)
    reference_eigenvectors = input_eigenvectors[0].copy() if reference_eigenvectors is None else reference_eigenvectors
    dot_products = compute_dot_products(input_eigenvectors, reference_eigenvectors)
    max_abs_indices = np.argmax(np.abs(dot_products), axis=-1)
    max_abs_signs = np.sign(dot_products[np.arange(dot_products.shape[0])[:, None], np.arange(dot_products.shape[1]), max_abs_indices])
    flipped_eigenvectors = input_eigenvectors*max_abs_signs[:,:,np.newaxis]
    flipped_eigenvectors = flipped_eigenvectors.reshape(flipped_eigenvectors.shape[0], flipped_eigenvectors.shape[2])
    return flipped_eigenvectors

sensor_cols = ['phi_sensor_1_real', 'phi_sensor_1_imag', 'phi_sensor_2_real',
       'phi_sensor_2_imag', 'phi_sensor_3_real', 'phi_sensor_3_imag',
       'phi_sensor_4_real', 'phi_sensor_4_imag', 'phi_sensor_5_real',
       'phi_sensor_5_imag', 'phi_sensor_6_real', 'phi_sensor_6_imag']
modeshape_cols = ['frequency'] + sensor_cols

def df_from_unv(unv_filename, sensor_cols):
    """
    Reads a UNV file and returns a Pandas DataFrame mapped to custom sensor columns.
    
    Parameters:
    -----------
    unv_filename : str
        Path to the UNV file.
    sensor_cols : list of str
        The specific column names (e.g., ['accel_node_1_real', 'chan_5_imag'])
    """
    # This regex captures: (prefix) (node_number) (real/imag)
    # It looks for digits for the ID and 'real' or 'imag' at the end.
    regex_pattern = r'^(.*?)(\d+)_?(real|imag)$'
    sensor_map = []
    for col in sensor_cols:
        match = re.search(regex_pattern, col, re.IGNORECASE)
        if match:
            sensor_map.append({
                'col_name': col,
                'node_id': int(match.group(2)),
                'part': match.group(3).lower()
            })

    extracted_data = []
    try:
        read_uff = pyuff.UFF(unv_filename)
        all_datasets = read_uff.read_sets()

        for dataset in all_datasets:
            if isinstance(dataset, dict) and dataset.get('type') == 55:
                node_nums = dataset.get('node_nums')
                r1_data = dataset.get('r1')
                node_data_lookup = dict(zip(node_nums, r1_data))

                row_data = {
                    'mode_id': dataset.get('mode_n', 0),
                    'frequency': dataset.get('freq', 0.0),
                    'xi': dataset.get('modal_damp_vis', 0.0),
                }

                for mapping in sensor_map:
                    val = node_data_lookup.get(mapping['node_id'], np.nan)
                    if val is np.nan:
                        row_data[mapping['col_name']] = np.nan
                        continue
                    if mapping['part'] == 'real':
                        row_data[mapping['col_name']] = np.real(val)
                    elif mapping['part'] == 'imag':
                        row_data[mapping['col_name']] = np.imag(val)
                    else:
                        row_data[mapping['col_name']] = np.abs(val)
                extracted_data.append(row_data)
        return pd.DataFrame(extracted_data)
    except Exception as e:
        print(f"An error occurred: {e}")
        return pd.DataFrame()

def preprocess_weather_data(weather_file, time_column='date'):
    '''
    Preprocesses the weather data from a CSV file.

    Parameters:
    -----------
        weather_file: str
            path to the weather CSV file

    Returns:
    --------
        weather_df: pd.DataFrame
            preprocessed weather DataFrame
    '''

    weather_df = pd.read_csv(weather_file, index_col=None)
    if time_column in weather_df.columns:
        weather_df['Datetime'] = pd.to_datetime(weather_df[time_column], utc=True)
        weather_df = weather_df.drop(columns=[time_column])
    weather_df = weather_df.dropna()
    return weather_df

def preprocess_weather_df(df, time_column='date'):
    '''
    Preprocesses the weather data from a DataFrame.

    Parameters:
    -----------
        df: pd.DataFrame
            weather DataFrame

    Returns:
    --------
        weather_df: pd.DataFrame
            preprocessed weather DataFrame
    '''
    weather_df = df.copy()
    if time_column == weather_df.index.name:
        weather_df = weather_df.reset_index()
    if time_column in weather_df.columns:
        weather_df['Datetime'] = pd.to_datetime(weather_df[time_column], utc=True)
        weather_df = weather_df.drop(columns=[time_column])
    weather_df = weather_df.dropna()
    return weather_df

def merge_dataframes(df_modeshapes, df_weather, time_column='Datetime'):
    '''
    Merges mode shape DataFrame with weather DataFrame based on nearest timestamps.

    Parameters:
    -----------
        df_modeshapes: pd.DataFrame 
            Dataframe containing mode shape data
        df_weather: pd.DataFrame 
            Dataframe containing weather data

    Returns:
    --------
        merged_df: pd.DataFrame
            Merged DataFrame
    '''
    if time_column in df_modeshapes.columns and time_column in df_weather.columns:
        df_a = df_modeshapes.sort_values(by=time_column)
        df_b = df_weather.sort_values(by=time_column)
        merged_df = pd.merge_asof(df_a, df_b, on=time_column, direction='nearest') # merge based on the nearest time
    else:
        merged_df = df_modeshapes.join(df_weather, how="inner")
    if 'mode id' in merged_df.columns: # is this still needed?
        merged_df = merged_df.rename(columns={'mode id': 'mode_id'})

    return merged_df

def separate__and_flip_modes(merged_df):
    '''
    Separates the modes from the merged DataFrame and flips the eigenvectors.

    Parameters:
    -----------
        merged_df: pd.DataFrame
            DataFrame containing the merged data

    Returns:
    -----------
        modeshapes_dict: dictionary
            Dictionary with mode ids as keys and DataFrames as values
    '''

    modeshapes_df = merged_df.copy()
    modes = set(modeshapes_df['mode_id'])
    modeshapes_dict = {}
    for mode in modes:
        modeshapes_dict[mode] = modeshapes_df[modeshapes_df['mode_id'] == mode].drop(['mode_id'], axis=1).sort_values(by='Datetime')

        new_df = modeshapes_dict[mode]
        cols = new_df.columns
        df = new_df[sensor_cols].copy()
        new_df1 = pd.DataFrame(flip_eigenvectors(df.values, reference_eigenvectors=None), columns=sensor_cols)
        for col in cols:
            if col not in sensor_cols:
                new_df1[col] = new_df[col].values
        modeshapes_dict[mode] = new_df1.copy()

    return modeshapes_dict

def merge_modes(modeshapes_dict):
    '''
    Merges the modes from the modeshapes dictionary back into a single DataFrame.

    Parameters
    -----------
        modeshapes_dict: dictionary
            Dictionary with mode ids as keys and DataFrames as values

    Returns
    -------
        modeshapes_df: pd.DataFrame
            mMrged DataFrame containing all modes
    '''

    for i in modeshapes_dict.keys():
        df = modeshapes_dict[i]
        df['mode_id'] = pd.Series([i] * df.shape[0])
        modeshapes_dict[i] = df

    modeshapes_df = pd.concat([modeshapes_dict[i] for i in modeshapes_dict.keys()])

    return modeshapes_df

def select_modes(df, modes, X_cols):
    '''
    Selects specified modes from the DataFrame and pivots the data so that each mode's data is in separate columns.

    Parameters
    -----------
        df: pd.DataFrame
            DataFrame containing the merged data
        modes: list
            List of mode ids to select
        X_cols: list
            List of weather columns to be used

    Returns:
    -----------
        final_df: pd.DataFrame
            Dataframe with selected modes and pivoted structure
    '''
    df = df.copy()
    df['Datetime'] = pd.to_datetime(df['Datetime'])
    df['Datetime_grouped'] = df['Datetime'].dt.floor('h')
    
    pivoted = df[df['mode_id'].isin(modes)].pivot_table(
        index='Datetime_grouped', 
        columns='mode_id',
        values=[col for col in modeshape_cols if col in df.columns],
        aggfunc='mean'
    )
    
    pivoted.columns = [f'{col[0]}_mode_{col[1]}' for col in pivoted.columns]
    pivoted = pivoted.sort_index().ffill().bfill()
    
    weather_data = df[['Datetime_grouped'] + X_cols].groupby('Datetime_grouped').mean()
    
    final_df = weather_data.join(pivoted, how='inner').reset_index()
    final_df = final_df.rename(columns={'Datetime_grouped': 'Datetime'})
    
    return final_df

def select_cols(data, X_cols, y_cols, modes=None):
    '''
    Selects input features and output targets from the DataFrame based on specified modes and columns.

    Parameters:
    -----------
        data: pd.DataFrame
            Dataframe containing the merged data
        X_cols: list
            List of weather columns to be used
        y_cols
            Can be 'frequency', 'modeshapes', 'frequency+modeshapes', or a list of column names
        modes: list, optional
            List of mode ids to select. If None, all modes will be selected.

    Returns:
    --------
        X: pd.DataFrame
            DataFrame of input features
        y: pd.DataFrame
            DataFrame of output targets
        Q: VariableSet
            VariableSet of input variables
        y_names: list
            List of output target names
    '''
    if modes is None:
        if 'mode_id' in data.columns:
            modes = sorted(data['mode_id'].unique())
        else:
            found_modes = set(re.findall(r'mode_(\d+)', ' '.join(data.columns)))
            modes = sorted([int(m) for m in found_modes])

    df = select_modes(data, modes, X_cols)
    
    if df.empty:
        raise ValueError("The aligned DataFrame is empty. Check your data timestamps.")

    potential_targets = [col for col in df.columns if col not in X_cols]
    selected_y_names = []
    
    if y_cols == 'frequency':
        selected_y_names = [col for col in potential_targets if 'frequency' in col]
    elif y_cols == 'modeshapes':
        for mode in modes:
            selected_y_names.extend([f"{p}_mode_{mode}" for p in sensor_cols if f"{p}_mode_{mode}" in potential_targets])
    elif y_cols == 'frequency+modeshapes':
        for mode in modes:
            selected_y_names.extend([f"{p}_mode_{mode}" for p in modeshape_cols if f"{p}_mode_{mode}" in potential_targets])
    elif isinstance(y_cols, list):
        selected_y_names = [c for c in y_cols if c in df.columns]

    X = df[X_cols]
    y = df[selected_y_names]

    variance_mask = (y.max() - y.min() != 0)
    constant_cols = y.columns[~variance_mask].tolist()
    
    if constant_cols:
        print(f"WARNING: Removing constant columns {constant_cols} to prevent ZeroDivisionError in evaluation.")
        y = y.loc[:, variance_mask]
        selected_y_names = y.columns.tolist()

    if y.empty:
        raise ValueError("No targets with variance found. All mode data is constant!")

    Q = VariableSet()
    for col in X_cols:
        Q.add(Variable(col, UniformDistribution(df[col].min(), df[col].max())))
    
    return X, y, Q, selected_y_names

def plot_correlation(input_df: pd.DataFrame,
                     output_df: pd.DataFrame,
                     input_features: list = None,
                     output_features: list = None,
                     annot: bool = True,
                     mode: str = 'input-output') -> plt.Figure:
    '''
    Plots a correlation heatmap between input and output features.

    Parameters:
    -----------
        input_df: pd.DataFrame
            Input features DataFrame
        output_df: pd.DataFrame
            Output targets DataFrame
        input_features: list, optional
            List of input feature names to include
        output_features: list, optional
            List of output feature names to include
        annot: bool
            Whether to annotate the heatmap with correlation values
        mode: str
            'input-output', 'input-input', or 'output-output'

    Returns:
    -------
        matplotlib Figure
    '''

    base_cell_size = 0.8
    max_figsize = (20, 15)

    # Keep only numeric columns
    input_df = input_df.select_dtypes(include='number')
    output_df = output_df.select_dtypes(include='number')

    # Filter selected features
    if input_features:
        input_df = input_df[input_features]
    if output_features:
        output_df = output_df[output_features]

    # Determine correlation matrix based on mode
    if mode == 'input-output':
        correlations = pd.DataFrame(index=input_df.columns, columns=output_df.columns)
        for input_col in input_df.columns:
            for output_col in output_df.columns:
                correlations.loc[input_col, output_col] = input_df[input_col].corr(output_df[output_col])
    elif mode == 'input-input':
        correlations = input_df.corr()
    elif mode == 'output-output':
        correlations = output_df.corr()
    else:
        raise ValueError("Invalid mode. Choose from 'input-output', 'input-input', or 'output-output'.")

    correlations = correlations.astype(float)

    # Determine dynamic figure size
    height = min(max_figsize[1], max(4, base_cell_size * correlations.shape[0]))
    width = min(max_figsize[0], max(4, base_cell_size * correlations.shape[1]))
    fig, ax = plt.subplots(figsize=(width, height))

    # Plot heatmap
    sns.heatmap(correlations, cmap='coolwarm', annot=annot, fmt=".2f",
                cbar=True, ax=ax, vmin=-1, vmax=1)

    # Set axis labels
    if mode == 'input-output':
        ax.set_xlabel('Output Features')
        ax.set_ylabel('Input Features')
        ax.set_title('Correlation Between Input and Output Features')
    elif mode == 'input-input':
        ax.set_title('Correlation Between Input Features')
    elif mode == 'output-output':
        ax.set_title('Correlation Between Output Features')

    plt.tight_layout()
    return fig

def scatter_plot(input_df: pd.DataFrame,
                 output_df: pd.DataFrame,
                 x_col: str,
                 y_col: str,
                 hue_col: str = None,
                 title: str = None) -> plt.Figure:
    '''
    Creates a scatter plot using two features from input or output dataframes.

    Parameters:
    -----------
        input_df : pd.DataFrame
            DataFrame containing input features
        output_df: pd.DataFrame
            DataFrame containing output features
        x_col: str
            Name of feature to use for x-axis
        y_col: str
            Name of feature to use for y-axis
        hue_col: str, optional
            Name of feature to color by
        title : str, optional
            Title for the plot

    Returns:
    -------
        matplotlib Figure
    '''

    # Merge input and output DataFrames for flexibility
    if 'Datetime' in input_df.columns and 'Datetime' in output_df.columns:
        df = merge_dataframes(input_df, output_df)
        df = separate__and_flip_modes(df)
        df = merge_modes(df)
        df = df.sort_values(by='Datetime')

    else:
        df = pd.concat([input_df, output_df], axis=1)

    # Check if requested columns exist
    for col in [x_col, y_col, hue_col]:
        if col and col not in df.columns:
            raise ValueError(f"Column '{col}' not found in input or output DataFrames.")

    # Create plot
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.scatterplot(data=df, x=x_col, y=y_col, hue=hue_col, ax=ax)

    if not title:
        title = f'Scatter Plot of {x_col} vs {y_col}'

    ax.set_title(title)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.grid(True)

    return fig

def remove_constant_columns(df: pd.DataFrame) -> (pd.DataFrame):
    '''
    Removes columns with constant values from the DataFrame.

    Parameters
    ----------
        df: pd.DataFrame
            Input DataFrame

    Returns
    -----------
        df: pd.DataFrame
            DataFrame with constant columns removed
    '''

    constant_cols = [col for col in df.columns if df[col].dropna().nunique() == 1]
    if constant_cols:
        print(f"Constant columns {constant_cols} were found and excluded.")
        df = df.drop(columns=constant_cols)
    return df