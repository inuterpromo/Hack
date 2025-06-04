



import pandas as pd
import geopandas as gpd
import folium
from math import sqrt
from shapely.geometry import LineString


# -------------------------- PART1: Highlight Sanctioned Countries --------------------------

#Load the Natural Earth dataset using Geopandas
world = gpd.read_file ("C:\\Users\\AKaushik\\Desktop\\Hack_Work\\SHP\\ne_110m_admin_0_countries.shp")
#CRS (EPSG: 4326) - WGS84 coordinate system to use latitude and longitude
world = world.to_crs(epsg=4326)

# List of Sanctioned Countries
countries_to_highlight = [
    "Afghanistan", "Belarus", "Burma", "Cuba", "North Korea", "Iran", "Iraq", "Libya", "Russia", "South Sudan", "Sudan", "Syria", "Ukraine", "Venezuela", "Yemen"
]

#Filter the dataset for the Sanctioned Countries.
selected_countries = world[world["NAME"].isin(countries_to_highlight)]

# -------------------------- PART2: Process Transaction Data --------------------------

#Load the file of transactions
df = pd.read_excel("C:\\Users\\AKaushik\\Desktop\\Hack_Work\\synthetic_transactions_complete.xlsx", engine = 'openpyxl')
#df = pd.read_csv("C:\\Users\\AKaushik\\Desktop\\transactions_xyz_company.csv")

#Determine the external partner country:
# For Receipt the money come from the Origin_country;
# For Payment the money goes to the Destination_country.
df['Other_Country'] = df.apply(
    lambda row: row['Origin_country'] if row['Receipt/Payment'] == 'Receipt' else row['Destination_country'], axis = 1
)

# Define risk ranking and a custom aggregation function to retain the worst risk in a group.
risk_ranking= {'Low':1, 'Medium':2, 'High':3}

def aggregate_risk(risks):
    max_val = risks.map(risk_ranking).max()
    for key,value in risk_ranking.items():
        if value == max_val:
            return key

#Aggregate transactions byu external country and Receipt/Payment type, summing amounts and aggregating risk.
agg_df = df.groupby(['Other_Country','Receipt/Payment']).agg({'Amount':'sum', 'Risk': aggregate_risk}).reset_index() 

# -------------------------- PART3: Setup Country Centroid and Hub Location --------------------------

#Create a dictionary mapping country names (from the shapefile) to their centroid coordinates.
country_centroids = {}
for idx, row in world.iterrows():
    centroid = row["geometry"].centroid
    country_centroids[row["NAME"]] = (centroid.y, centroid.x)

#DEtermine hub location: Company Location
hub = None
for key in country_centroids.keys():
    if key in ["United Kingdom", "UK"]:
        hub = country_centroids[key]
        break
#Fallback Location if not found
if hub is None:
    hub = (51.5072, -0.1276)

# -------------------------- PART4: Create Map and Add Base Layers --------------------------

#Create Folium map. Zoom_start that is used before
m = folium.Map(location=hub, zoom_start=4)

#Add GeoJson layer to highlight sanctioned countries in red.
folium.GeoJson(
    selected_countries, 
    style_function=lambda feature:{
        "fillColor": "red",
        "color": "black",
        "weight": 1.5,
        "fillOpacity": 0.3,
    },
    tooltip = folium.features.GeoJsonTooltip(fields=["NAME"], aliases=["Country:"])
).add_to(m)

#Mark the hub (company) with blue pin
folium.Marker(
    location=hub,
    popup="Viva Solutions Ltd. (UK)",
    icon=folium.Icon(color="blue",icon="info-sign")
).add_to(m)

# -------------------------- PART5: Draw the transaction graph lines with offset --------------------------

#Define risk color mapping
color_mapping = {'Low': 'green', 'Medium': 'orange', 'High': 'red'}

def bezier_curve(p0, p1, p2, num_points=20):
    return [
        (
            (1 - t)**2 * p0[0] + 2 * (1 - t) * t * p1[0] + t**2 * p2[0],
            (1 - t)**2 * p0[1] + 2 * (1 - t) * t * p1[1] + t**2 * p2[1]
        )
        for t in [i / num_points for i in range(num_points + 1)]
    ]

#We group aggregated transactions by partner country(Other_Country).
# if both type exist for a partner, we add a curve by offsetting the midpoint
for other_country, group in agg_df.groupby('Other_Country'):
    partner_coords = None
    for country,coord in country_centroids.items():
        if country.lower() == other_country.lower():
            partner_coords = coord
            break
    if partner_coords is None:
        continue # skip if no country found
    
    hub_lat, hub_lon = hub
    partner_lat, partner_lon = partner_coords

    # Vector from hub to partner and its distance
    dx = partner_lat - hub_lat
    dy = partner_lon - hub_lon
    distance = sqrt(dx**2 + dy**2)
    # If group has more than one transaction type, we assign offset
    use_offset = len(group) >1

    # For eachtransaction type for the particular partner country.
    for idx,row in group.iterrows():
        #Default: straight line if no offset to be applied.
        if not use_offset or distance == 0:
            line_coords = [hub, partner_coords]
        else:
            #Calculate offset magnitude as 10% of the distance
            offset_magnitude = distance*0.1
            #Calculate a perpendicular vector (-dy, dx)
            norm = sqrt(dy**2 + dx**2)
            v_perp = (-dy/norm, dx/norm) if norm!= 0 else (0,0)
            #Use sign: +1 for Receipt, -1 for Payment
            sign = 1 if row["Receipt/Payment"] == "Receipt" else -1
            #Compute the midpoint by scaled perpendicula vector
            mid_lat = (hub_lat + partner_lat)/2
            mid_lon = (hub_lon + partner_lon)/2
            offset_mid = (mid_lat + sign * v_perp[0] * offset_magnitude, 
                          mid_lon + sign * v_perp[1] * offset_magnitude)
            # Create a curved polyline using hub, offset midpoint and partner.
            line_coords = bezier_curve(hub, offset_mid, partner_coords)

            #Choose Linestyle: solid for Receipt, dotted for payment.
            dash_pattern = None if row["Receipt/Payment"] == "Receipt" else "5,10"
            #Get risk based color
            line_color = color_mapping.get(row["Risk"],"blue")
            #Build tooltip text with basic transaction details
            tooltip_text = (
                f"Type: {row['Receipt/Payment']}<br>"
                f"Amount: {row['Amount']:.2f}<br>"
                f"Risk: {row['Risk']}"
            )

            #Draw the polyline on map
            folium.PolyLine(
                locations=line_coords, 
                color=line_color, 
                weight=3, 
                dash_array=dash_pattern, 
                tooltip=tooltip_text
            ).add_to(m)

#Save the map on html file
m.save("Txn_Map2.html")
m









