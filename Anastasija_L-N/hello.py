import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# Load data
df = pd.read_csv("output/SensorReading.csv")
df["RecordedAt"] = pd.to_datetime(df["RecordedAt"])
df = df.sort_values("RecordedAt")

# Select one sensor
sensor_id = df["SensorID"].iloc[0]
df = df[df["SensorID"] == sensor_id]

# Convert time to numeric
df["TimeNumeric"] = df["RecordedAt"].astype("int64") // 10**9

# Sample for speed (important with 78k rows)
df_sample = df.sample(min(8000, len(df)), random_state=42)

fig = plt.figure(figsize=(10,7))
ax = fig.add_subplot(111, projection='3d')

sc = ax.scatter(
    df_sample["TimeNumeric"],
    df_sample["Temperature"],
    df_sample["TDS"],
    c=df_sample["TDS"],
    s=8
)

ax.set_xlabel("Time")
ax.set_ylabel("Temperature")
ax.set_zlabel("TDS")
plt.title(f"3D Scatter - Sensor {sensor_id}")

plt.colorbar(sc)
plt.show()