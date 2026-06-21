import pandas as pd

def profile_telemetry_data(file_path):
    """
    Reads raw SCADA Parquet telemetry and profiles it for engineering quality checks.
    """
    print(f"Initiating Idempotent Ingestion for: {file_path}\n")
    df = pd.read_parquet(file_path, engine='pyarrow')

    print(df.index)
    print(df.head())
    
    try:
        # Load the dataset using the Parquet engine
        df = pd.read_parquet(file_path, engine='pyarrow')
    except Exception as e:
        print(f"[ERROR] Failed to load dataset: {e}")
        return

    # 1. Pipeline Dimensions
    print("=== 1. TELEMETRY DIMENSIONS ===")
    print(f"Total Sensor Pings (Rows): {df.shape[0]}")
    print(f"Telemetry Channels (Columns): {df.shape[1]}\n")
    print(df.head())

    # 2. Schema Validation
    print("=== 2. SCHEMA & DATA TYPES ===")
    print(df.dtypes)
    print("\n")

    # 3. Missing Data (Comms Dropouts)
    print("=== 3. SENSOR DROPOUTS (Missing Values) ===")
    print(df.isnull().sum())
    print("\n")

    # 4. Physical Plausibility Bounds
    numeric_df = df.select_dtypes(include=['float64', 'int64', 'float32', 'int32'])
    print("=== 4. PHYSICAL BOUNDS (Min/Max Summary) ===")
    if not numeric_df.empty:
        print(numeric_df.describe().T[['min', 'mean', 'max']])
    else:
        print("No numeric columns found to summarize.")

if __name__ == "__main__":
    # Pointing to the MANSLR1 PV Export Parquet file
    RAW_DATA_PATH = r"D:\industrial-telemetry-pipeline\data\raw\solar_scada_raw\MANSLR1.pvexport_data.parquet" 

    profile_telemetry_data(RAW_DATA_PATH)
