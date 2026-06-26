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
    current_threshold = current_blind_spot_rows['pvexport_data_power_real'].quantile(0.95)

    print("=== INVESTIGATING CURRENT SENSOR BLIND SPOT ===")
    print(f"Rows where current=0 but power>0: {len(current_blind_spot_rows)}")
    print(f"95th percentile power_real while current still read 0: {current_threshold}\n")

    print("=== QUALITY GATE: FLAGGING (not dropping) ===\n")

    # FLAG 1: Missing sensor pings
    df['flag_missing_reading'] = df.isnull().any(axis=1)

    # ------------------------------------------------------------------
    # NEW: look at neighboring minutes using .shift(), so we can tell apart
    # a smooth sunrise/sunset blind-spot ramp from a genuine one-minute glitch
    # ------------------------------------------------------------------
    df['current_prev_minute'] = df['pvexport_data_current'].shift(1)
    df['current_next_minute'] = df['pvexport_data_current'].shift(-1)

    # FLAG 2: Physically impossible combination (voltage/frequency checks stay strict)
    impossible_voltage = (df['pvexport_data_voltage'] == 0) & (df['pvexport_data_power_real'] > 0)
    impossible_frequency = (df['pvexport_data_frequency'] == 0) & (df['pvexport_data_power_real'] > 0)

    # Current check: power high enough (above 95th percentile of the blind-spot
    # group) that current=0 no longer makes sense at all, regardless of timing.
    impossible_current = (df['pvexport_data_current'] == 0) & (df['pvexport_data_power_real'] > current_threshold)

    # NEW: isolated single-minute current DROPOUT during daytime — current=0
    # for exactly one minute, with non-zero readings right before and after,
    # while power is actively flowing. Different from the blind spot: this can
    # happen at ANY power level, not just near the sunrise/sunset threshold.
    isolated_current_dropout = (
        (df['pvexport_data_current'] == 0) &
        (df['current_prev_minute'] != 0) &
        (df['current_next_minute'] != 0) &
        (df['pvexport_data_power_real'] > 0)
    )

    # NEW: isolated single-minute current SPIKE during a moment with no real
    # or reactive power at all — current has no electrical reason to exist.
    # Small tolerance (+-1) used instead of an exact 0, since reactive power
    # readings are rarely exactly zero even when negligible.
    isolated_current_spike = (
        (df['pvexport_data_power_real'] == 0) &
        (df['pvexport_data_power_reactive'].between(-1, 1)) &
        (df['current_prev_minute'] == 0) &
        (df['pvexport_data_current'] != 0) &
        (df['current_next_minute'] == 0)
    )

    df['flag_sensor_glitch'] = (
        impossible_voltage | impossible_frequency | impossible_current
        | isolated_current_dropout | isolated_current_spike
    )

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