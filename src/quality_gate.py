import pandas as pd
import numpy as np

def process_telemetry_data(file_path):
    """
    Day 2: Domain-Aware Quality Gate.
    We FLAG suspicious rows with new boolean columns. We never delete or
    overwrite the original sensor readings.
    """
    print(f"Initiating Quality Gate for: {file_path}\n")

    try:
        df = pd.read_parquet(file_path, engine='pyarrow')
    except Exception as e:
        print(f"[ERROR] Failed to load dataset: {e}")
        return

    # ------------------------------------------------------------------
    # INVESTIGATION: find the real-world boundary of the current sensor's
    # low-end blind spot, instead of guessing a threshold.
    # ------------------------------------------------------------------
    current_blind_spot_rows = df[(df['pvexport_data_current'] == 0) & (df['pvexport_data_power_real'] > 0)]
    current_threshold = current_blind_spot_rows['pvexport_data_power_real'].max()

    print("=== INVESTIGATING CURRENT SENSOR BLIND SPOT ===")
    print(f"Rows where current=0 but power>0: {len(current_blind_spot_rows)}")
    print(f"Highest power_real seen while current still read 0: {current_threshold}\n")

    print("=== QUALITY GATE: FLAGGING (not dropping) ===\n")

    # FLAG 1: Missing sensor pings
    df['flag_missing_reading'] = df.isnull().any(axis=1)

    # FLAG 2: Physically impossible combination.
    impossible_voltage = (df['pvexport_data_voltage'] == 0) & (df['pvexport_data_power_real'] > 0)
    impossible_frequency = (df['pvexport_data_frequency'] == 0) & (df['pvexport_data_power_real'] > 0)

    # KNOWN ISSUE (WIP): current_threshold is the MAX power value seen in the
    # blind-spot group itself, which means "power > current_threshold" can
    # mathematically never be true for rows IN that same group — it's a
    # circular check that guarantees 0 glitches regardless of real data.
    # TODO: replace with a percentile-based threshold (e.g. 95th/99th) so a
    # few genuine high-power glitches can still surface instead of being
    # silently absorbed into "normal blind spot" territory.
    impossible_current = (df['pvexport_data_current'] == 0) & (df['pvexport_data_power_real'] > current_threshold)

    df['flag_sensor_glitch'] = impossible_voltage | impossible_frequency | impossible_current
    
    # FLAG 3: Grid genuinely de-energized — power, voltage, AND frequency
    # all zero together. Rarer and more serious than ordinary night.
    df['flag_grid_deenergized'] = (
        (df['pvexport_data_power_real'] == 0) &
        (df['pvexport_data_voltage'] == 0) &
        (df['pvexport_data_frequency'] == 0)
    )

    # FLAG 4: Genuine offline state — ordinary night-time, grid still fine.
    df['flag_offline_normal'] = (df['pvexport_data_power_real'] == 0) & (~df['flag_grid_deenergized'])

    # FLAG 5: Negative reactive power — informational only, NOT an error
    df['flag_negative_reactive'] = df['pvexport_data_power_reactive'] < 0

    # SUMMARY
    print(f"Missing readings (any column):       {df['flag_missing_reading'].sum()}")
    print(f"Sensor glitches (impossible combo):   {df['flag_sensor_glitch'].sum()}")
    print(f"Grid de-energized (real fault):       {df['flag_grid_deenergized'].sum()}")
    print(f"Genuine offline (night/curtailed):    {df['flag_offline_normal'].sum()}")
    print(f"Negative reactive power (informational): {df['flag_negative_reactive'].sum()}\n")

    if df['flag_sensor_glitch'].sum() > 0:
        print("Sample of flagged sensor glitches:")
        print(df.loc[df['flag_sensor_glitch'], ['pvexport_data_power_real', 'pvexport_data_voltage', 'pvexport_data_frequency', 'pvexport_data_current']].head())

    return df


if __name__ == "__main__":
    RAW_DATA_PATH = r"D:\industrial-telemetry-pipeline\data\raw\solar_scada_raw\MANSLR1.pvexport_data.parquet"
    process_telemetry_data(RAW_DATA_PATH)