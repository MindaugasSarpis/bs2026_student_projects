# ---------------------------------------------------------
# IMPORT LIBRARIES
# ---------------------------------------------------------

# pandas = data analysis
import pandas as pd

# matplotlib = plotting graphs
import matplotlib.pyplot as plt

# glob = automatically find all CSV files in a folder
import glob


# ---------------------------------------------------------
# 1. LOAD ALL CSV FILES
# ---------------------------------------------------------

# Find all CSV files in the current folder
files = glob.glob("*.csv")

# Create an empty list to store dataframes
df_list = []

# Loop through each CSV file
for file in files:

    # Read the CSV file
    # low_memory=False prevents mixed datatype warnings
    df = pd.read_csv(file, low_memory=False)

    # Add dataframe to list
    df_list.append(df)

# Combine all files into one dataframe
df = pd.concat(df_list, ignore_index=True)


# ---------------------------------------------------------
# 2. FIX COLUMN NAMES
# ---------------------------------------------------------

# Rename the time column so the rest of the code is simpler
df = df.rename(columns={"Time and Date": "time"})


# ---------------------------------------------------------
# 3. CONVERT TIME COLUMN TO DATETIME
# ---------------------------------------------------------

# Convert text date to proper datetime format
# dayfirst=True because your data is DD/MM/YYYY
df["time"] = pd.to_datetime(df["time"], dayfirst=True, errors="coerce")

# Remove rows where time could not be parsed
df = df.dropna(subset=["time"])

# ---------------------------------------------------------
# REMOVE DUPLICATE TIMESTAMPS
# ---------------------------------------------------------

df = df.sort_values("time")

df = df.drop_duplicates(subset="time")

print("Rows after removing duplicates:", len(df))

# ---------------------------------------------------------
# RESAMPLE DATA TO 10-MINUTE INTERVALS
# ---------------------------------------------------------

# Set time as index
df = df.set_index("time")

# Resample to 10-minute averages
df = df.resample("10T").mean()

# Restore time as a column
df = df.reset_index()

# ---------------------------------------------------------
# 4. SELECT HEIGHT FOR WIND ANALYSIS
# ---------------------------------------------------------

# Choose the measurement height (you can change this)
height = 248

# Create the wind column name dynamically
wind_column = f"Horizontal Wind Speed (m/s) at {height}m"

# Convert wind speed column to numeric values
df["wind"] = pd.to_numeric(df[wind_column], errors="coerce")

#----------------------------------------------------------
# Wind direction column based on selected height
direction_column = f"Wind Direction (deg) at {height}m"

df["direction"] = pd.to_numeric(df[direction_column], errors="coerce")

# Remove invalid direction values
df = df.dropna(subset=["direction"])

# ---------------------------------------------------------
# 5. REMOVE INVALID SENSOR VALUES
# ---------------------------------------------------------

# In this dataset missing data is coded as 9999 or 9998
# Wind speeds above 100 m/s are impossible, so we remove them

df.loc[df["wind"] > 100, "wind"] = None

# Remove rows with missing wind values
df = df.dropna(subset=["wind"])


# ---------------------------------------------------------
# 6. BASIC DATA INFORMATION
# ---------------------------------------------------------

print("Selected height:", height, "m")
print("Total rows:", len(df))

print("Data from:", df["time"].min())
print("Data until:", df["time"].max())

# Calculate average wind speed
avg_wind = df["wind"].mean()

# Calculate maximum wind speed
max_wind = df["wind"].max()

print("Average wind speed:", round(avg_wind, 2), "m/s")
print("Maximum wind speed:", round(max_wind, 2), "m/s")


# ---------------------------------------------------------
# 7. WIND SPEED TIME SERIES PLOT
# ---------------------------------------------------------

plt.figure(figsize=(12,6))

# Plot wind speed vs time
plt.plot(df["time"], df["wind"])

# Axis labels
plt.xlabel("Time")
plt.ylabel("Wind Speed (m/s)")

# Plot title
plt.title(f"Wind Speed at {height} m")

plt.tight_layout()

plt.show()


# ---------------------------------------------------------
# 8. MONTHLY WIND SPEED ANALYSIS
# ---------------------------------------------------------

# Create a year-month column (keeps correct order)
df["year_month"] = df["time"].dt.to_period("M")

# Calculate average wind speed for each month
monthly_avg = df.groupby("year_month")["wind"].mean()

# Print monthly averages
print("\nMonthly Average Wind Speeds:")
print(monthly_avg)


# ---------------------------------------------------------
# 9. MONTHLY AVERAGE WIND SPEED PLOT
# ---------------------------------------------------------

plt.figure(figsize=(10,5))

monthly_avg.plot(kind="bar")

plt.xlabel("Month")
plt.ylabel("Average Wind Speed (m/s)")

plt.title(f"Monthly Average Wind Speed at {height} m")

plt.xticks(rotation=45)

plt.tight_layout()

plt.show()

# ---------------------------------------------------------
# 10. WIND SPEED DISTRIBUTION (IMPROVED HISTOGRAM)
# ---------------------------------------------------------

plt.figure(figsize=(10,5))

# Histogram normalized to probability density
plt.hist(df["wind"], bins=30, density=True)

plt.xlabel("Wind Speed (m/s)")
plt.ylabel("Probability")

plt.title(f"Wind Speed Distribution at {height} m")

plt.tight_layout()

plt.show()

# ---------------------------------------------------------
# 11. DEFINE A WIND TURBINE
# ---------------------------------------------------------

# ---------------------------------------------------------
# TURBINE LIBRARY
# ---------------------------------------------------------

turbines = {

    "Vestas V164 8MW": {
        "rated_power": 8000,
        "cut_in": 3,
        "rated_speed": 12,
        "cut_out": 25
    },

    "Vestas V150 6MW": {
        "rated_power": 6000,
        "cut_in": 3,
        "rated_speed": 11.5,
        "cut_out": 25
    },

    "Siemens SG 6.0-154": {
        "rated_power": 6000,
        "cut_in": 3,
        "rated_speed": 12,
        "cut_out": 25
    },

    "Nordex N149 5MW": {
        "rated_power": 5000,
        "cut_in": 3,
        "rated_speed": 11.5,
        "cut_out": 25
    },

    "GE Haliade-X 12MW": {
        "rated_power": 12000,
        "cut_in": 3,
        "rated_speed": 11,
        "cut_out": 25
    }

}

turbine_name = "Vestas V164 8MW"
turbine = turbines[turbine_name]

# ---------------------------------------------------------
# 12. TURBINE POWER FUNCTION
# ---------------------------------------------------------

def turbine_power(v, turbine):

    # Below cut-in speed → no power
    if v < turbine["cut_in"]:
        return 0

    # Between cut-in and rated speed → cubic power increase
    elif v < turbine["rated_speed"]:
        return turbine["rated_power"] * (v / turbine["rated_speed"])**3

    # Between rated speed and cut-out → constant rated power
    elif v < turbine["cut_out"]:
        return turbine["rated_power"]

    # Above cut-out → turbine stops
    else:
        return 0
    
# ---------------------------------------------------------
# 13. CALCULATE TURBINE POWER OUTPUT
# ---------------------------------------------------------

df["power_kw"] = df["wind"].apply(lambda v: turbine_power(v, turbine))

# ---------------------------------------------------------
# 14. CALCULATE ENERGY PRODUCTION
# ---------------------------------------------------------

# Each measurement represents 10 minutes
time_hours = 10 / 60

df["energy_kwh"] = df["power_kw"] * time_hours

# ---------------------------------------------------------
# 15. TOTAL ENERGY PRODUCTION
# ---------------------------------------------------------

total_energy_kwh = df["energy_kwh"].sum()

total_energy_mwh = total_energy_kwh / 1000

print("\nEstimated energy production:")
print(round(total_energy_mwh,2), "MWh")

# ---------------------------------------------------------
# 16. CAPACITY FACTOR
# ---------------------------------------------------------

total_hours = len(df) * time_hours

max_possible_energy = turbine["rated_power"] * total_hours

capacity_factor = total_energy_kwh / max_possible_energy

print("Capacity factor:", round(capacity_factor*100,2), "%")

# ---------------------------------------------------------
# 17. TURBINE POWER CURVE PLOT
# ---------------------------------------------------------

# Create a list of wind speeds from 0 to 30 m/s
wind_speeds = list(range(0, 31))

# Calculate power output for each wind speed
power_values = [turbine_power(v, turbine) for v in wind_speeds]

plt.figure(figsize=(10,5))

plt.plot(wind_speeds, power_values)

plt.xlabel("Wind Speed (m/s)")
plt.ylabel("Power Output (kW)")

plt.title(f"Power Curve - {turbine_name}")

plt.tight_layout()

plt.show()

# ---------------------------------------------------------
# 18. MONTHLY ENERGY PRODUCTION
# ---------------------------------------------------------

# Sum energy production for each month
monthly_energy = df.groupby("year_month")["energy_kwh"].sum()

# Convert to MWh
monthly_energy_mwh = monthly_energy / 1000

print("\nMonthly Energy Production (MWh):")
print(monthly_energy_mwh)

# ---------------------------------------------------------
# 19. MONTHLY ENERGY PRODUCTION PLOT
# ---------------------------------------------------------

plt.figure(figsize=(10,5))

monthly_energy_mwh.plot(kind="bar")

plt.xlabel("Month")
plt.ylabel("Energy Production (MWh)")

plt.title(f"Monthly Energy Production - {turbine_name}")

plt.xticks(rotation=45)

plt.tight_layout()

plt.show()

# ---------------------------------------------------------
# CHECK DATA COVERAGE PER MONTH
# ---------------------------------------------------------

monthly_counts = df.groupby("year_month").size()

print("\nNumber of measurements per month:")
print(monthly_counts)

# ---------------------------------------------------------
# 20. WIND ROSE
# ---------------------------------------------------------

from windrose import WindroseAxes

fig = plt.figure(figsize=(8,8))

ax = WindroseAxes.from_ax()

ax.bar(
    df["direction"],
    df["wind"],
    bins=[0,4,8,12,16,20,25],
    normed=True,
    opening=0.8
)

ax.set_title(f"Wind Rose at {height} m")

ax.set_legend(title="Wind speed (m/s)")

plt.show()