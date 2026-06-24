import pandas as pd
import numpy as np

def process_telemetry_data(file_path):
    """
    Day 2: Domain-Aware Quality Gate.
    We FLAG suspicious rows with new boolean columns. We never delete or
    overwrite the original sensor readings. Imputation (filling NaNs) is
    Day 3's job, not today's — you need to know WHERE the bad data is
    before you decide HOW to fix it.
    """
    print(f"Initiating Quality Gate for: {file_path}\n")

    try:
        df = pd.read_parquet(file_path, engine='pyarrow')
    except Exception as e:
        print(f"[ERROR] Failed to load dataset: {e}")
        return

    print("=== QUALITY GATE: FLAGGING (not dropping) ===\n")

    # FLAG 1: Missing sensor pings (the 8,721 NaN rows we found in Day 1)
    df['flag_missing_reading'] = df.isnull().any(axis=1)

    # FLAG 2: Physically impossible combination (the real "glitch" case)
    # A grid-tied inverter cannot generate real power while voltage reads 0.
    impossible_voltage = (df['pvexport_data_voltage'] == 0) & (df['pvexport_data_power_real'] > 0)
    impossible_frequency = (df['pvexport_data_frequency'] == 0) & (df['pvexport_data_power_real'] > 0)
    df['flag_sensor_glitch'] = impossible_voltage | impossible_frequency

    # FLAG 3: Genuine offline state (NOT an error — informational)
    # Night-time / curtailment: power_real == 0 AND voltage is also low.
    df['flag_offline_normal'] = (df['pvexport_data_power_real'] == 0)


    # FLAG 4: Negative reactive power — informational only, NOT an error
    df['flag_negative_reactive'] = df['pvexport_data_power_reactive'] < 0

    # SUMMARY: counts per flag
    print(f"Missing readings (any column):     {df['flag_missing_reading'].sum()}")
    print(f"Sensor glitches (impossible combo): {df['flag_sensor_glitch'].sum()}")
    print(f"Genuine offline (night/curtailed):  {df['flag_offline_normal'].sum()}")
    print(f"Negative reactive power (informational): {df['flag_negative_reactive'].sum()}\n")

    # Sanity check: look at a few glitch rows to confirm the logic makes sense
    if df['flag_sensor_glitch'].sum() > 0:
        print("Sample of flagged sensor glitches:")
        print(df.loc[df['flag_sensor_glitch'], ['pvexport_data_power_real', 'pvexport_data_voltage', 'pvexport_data_frequency']].head())

    return df


if __name__ == "__main__":
    RAW_DATA_PATH = r"D:\industrial-telemetry-pipeline\data\raw\solar_scada_raw\MANSLR1.pvexport_data.parquet"
    process_telemetry_data(RAW_DATA_PATH)
    #