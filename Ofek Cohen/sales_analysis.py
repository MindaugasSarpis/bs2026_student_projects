import pandas as pd

data = pd.read_csv("100_Sales_Records.csv")
average_sales = data.groupby("Country")["Total Revenue"].mean()
lowest_countries = average_sales.sort_values().head(3)

for country in lowest_countries.index:
    country_data = data[data["Country"] == country]
    country_data = country_data.sort_values("Total Revenue")
    safe_country_name = country.replace(" ", "_")
    country_data.to_csv(f"{safe_country_name}_sales.csv", index=False)

print("Done. Files created for the 3 lowest-average-sales countries.")
