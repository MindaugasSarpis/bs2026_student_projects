from textwrap import shorten

import matplotlib
import pandas as pd
import matplotlib.pyplot as plt

import numpy as np
import colorsys
import matplotlib.colors as mc

df=pd.read_csv("100_Sales_Records.csv")

################## NEW ATTEMPT WITHOUT STREAMLIT ##################

Total_profit=df.sum()["Total Profit"]
Region_Profit=df.groupby("Region")["Total Profit"].sum().sort_index() ## Sort by region name
Country_Profit = (
    df.groupby(["Region", "Country"])["Total Profit"]
      .sum()
      .sort_index()
)
inner_labels=Region_Profit.index
inner_values=Region_Profit.values
inner_labels_DISPLAY = [
    label.replace("Middle East and North Africa", "Middle East\nand North Africa")
         .replace("Central America and the Caribbean", "Central America\nand the Caribbean")
         .replace("Sub-Saharan Africa", "Sub-Saharan\nAfrica")
         .replace("Australia and Oceania", "Australia\nand Oceania")
    for label in inner_labels
]
outer_labels=Country_Profit.index.get_level_values("Country")
outer_values=Country_Profit.values
outer_color_list = [] ## an empty list to store the colors of the outer pie chart


Region_Colors = {
    "Sub-Saharan Africa": "#A7EF00B5",
    "Middle East and North Africa": "#AB1123",
    "Europe": "#BB6629",
    "Asia": "#23B52A",
    "Australia and Oceania": "#8b16b3",
    "Central America and the Caribbean": "#B2AB26",
    "North America": "#298EB4",
    "South America": "#C73189"
}
## failed attemp to create outer pie chart color gradient
# for region in inner_labels:
#     countries_in_region = Country_Profit.loc[region]
#     n = len(countries_in_region)

#     brightness_levels = np.linspace(1, 0.92, n) ##define brightness range

#     for brightness in brightness_levels:
#         base_color = mc.to_rgb(Region_Colors[region])
#         h, l, s = colorsys.rgb_to_hls(*base_color)
#         new_color = colorsys.hls_to_rgb(h, max(0, min(1, l * brightness)), s)
#         outer_color_list.append(new_color)


## defining outer pie colors as a gradient of the base color of the region
outer_color_list = []
for region in inner_labels:
    countries_in_region = Country_Profit.loc[region]
    n = len(countries_in_region)

    base_color = mc.to_rgb(Region_Colors[region])
    h, l, s = colorsys.rgb_to_hls(*base_color)

    dark_l = max(0, l + 0.05)
    light_l = 0.92

    lightness_levels = np.linspace(dark_l, light_l, n)

    for new_l in lightness_levels:
        new_color = colorsys.hls_to_rgb(h, new_l, s)
        outer_color_list.append(new_color)

Regions=df["Region"].unique()
Countries=df["Country"].unique()

fig, ax = plt.subplots(figsize=(9,9))
ax.set(aspect="equal")

Region_Colors_list = [Region_Colors[region] for region in inner_labels]
 
##explode list for countries with less than 0.5% contribution to total profit
Explode_List = []
for value in outer_values:
    Percentage = (value / sum(outer_values)) * 100
    if Percentage == 0:
        Explode_List.append(0.3)
    elif Percentage < 0.1 and Percentage > 0:
        Explode_List.append(0.2)
    elif Percentage <0.5 and Percentage >=0.1:
        Explode_List.append(0.1)
    else:
        Explode_List.append(0)


##OUTER PIE CHART (COUNTRIES)
Outer_Wedges, Outer_Texts,Outer_Autotexts =ax.pie(
    outer_values,
    labels=outer_labels,
    labeldistance=1.025,
    radius=1,
    colors=outer_color_list,
    autopct="%1.1f%%",
    pctdistance=0.935,
    rotatelabels=True,
    wedgeprops={"width": 0.35, "edgecolor": "white", "linewidth": 2},
    textprops={"fontsize": 8, "color": "black"},
    explode=Explode_List,
)

##INNER PIE CHART (REGIONS)
Inner_Wedges, Inner_Texts, Inner_Autotext = ax.pie(
    inner_values,
    labels=inner_labels_DISPLAY,
    radius=0.8,
    rotatelabels=True,
    autopct="%1.1f%%",
    labeldistance=0.4,
    pctdistance=0.275,
    wedgeprops={"width": 0.5, "edgecolor": "white", "linewidth": 2},
    colors=Region_Colors_list,
    textprops={"fontsize": 8, "fontweight": "bold","color": "white"},
)
Wedge_To_Autotext = {}
Wedge_To_Percent = {}
Wedge_To_Label = {}

for wedge, label in zip(Outer_Wedges, Outer_Texts):
    Wedge_To_Label[wedge] = label

outer_total = sum(outer_values)
for wedge, value in zip(Outer_Wedges, outer_values):
    Wedge_To_Percent[wedge] = (value / outer_total) * 100

inner_total = sum(inner_values)
for wedge, value in zip(Inner_Wedges, inner_values):
    Wedge_To_Percent[wedge] = (value / inner_total) * 100

for wedge, autotext in zip(Outer_Wedges, Outer_Autotexts):
    Wedge_To_Autotext[wedge] = autotext

for wedge, autotext in zip(Inner_Wedges, Inner_Autotext):
    Wedge_To_Autotext[wedge] = autotext

## Adjust the rotation of inner labels to align with the wedges
for wedge, autotext in zip(Inner_Wedges, Inner_Autotext):
    angle = (wedge.theta1 + wedge.theta2) / 2
    if 90 < angle < 270:
        angle += 180
    autotext.set_rotation(angle)
    autotext.set_rotation_mode("anchor")
    autotext.set_color("black")
    autotext.set_fontweight("bold")

##failed attempt to auto change the text color over dark wedges.
# for wedge, autotext in zip(Inner_Wedges, Inner_Autotext):
#     r, g, b, a = wedge.get_facecolor()
#     h, l, s = colorsys.rgb_to_hls(r, g, b)

#     if l < 0.5:
#         autotext.set_color("white")
#     else:
#         autotext.set_color("black")

fig.canvas.draw()

## check for overlapping labels and shorten the longer if needed
for i in range(len(Outer_Texts)):
    for j in range(i + 1, len(Outer_Texts)):
        box1 = Outer_Texts[i].get_window_extent()
        box2 = Outer_Texts[j].get_window_extent()

        if box1.overlaps(box2):

            print(f"Overlap found between: {Outer_Texts[i].get_text()} and {Outer_Texts[j].get_text()}")
            width1 = box1.x1 - box1.x0
            width2 = box2.x1 - box2.x0

            if width1 >= width2:
               shorten
               i
            else:
                shorten
                j

#### Unecessary code. This was an initial attempt to avoid ovelapping, but I opted to have the highlighting instead.
# ## defining a function how to shorten the label text
# def shorten_label(text_obj, keep=6):
#     label = text_obj.get_text()

#     if len(label) <= keep + 3:
#         return False
#     elif (label).find(" ") != -1:
#         return False
#     new_label = label[:keep] + "..."
#     text_obj.set_text(new_label)
#     return True

# ## defining a function to choose which label to shorten based on its length
# def choose_label_to_shorten(text1, text2):
#     box1 = text1.get_window_extent()
#     box2 = text2.get_window_extent()

#     width1 = box1.x1 - box1.x0
#     width2 = box2.x1 - box2.x0

#     if width1 >= width2:
#         return text1
#     else:
#         return text2
# fig.canvas.draw()

# for i in range(len(Outer_Texts)):
#     for j in range(i + 1, len(Outer_Texts)):
#         box1 = Outer_Texts[i].get_window_extent()
#         box2 = Outer_Texts[j].get_window_extent()

#         if box1.overlaps(box2):
#             Overlap_Detected = choose_label_to_shorten(Outer_Texts[i], Outer_Texts[j])
#             Shortened = shorten_label(Overlap_Detected, keep=6)

#             if Shortened:
#                 fig.canvas.draw()


## Creating conditions for hover effect on wedges
All_Wedges = list(Outer_Wedges) + list(Inner_Wedges)
All_Autotexts = list(Outer_Autotexts) + list(Inner_Autotext)

Original_Design = {}    ## Save base design of each wedge
for wedge in All_Wedges:
    Original_Design[wedge] = {
        "Original_Radius": wedge.r,
        "Original_Width": wedge.width,
        "Original_Facecolor": wedge.get_facecolor(),
        "Original_Edgecolor": wedge.get_edgecolor(),
        "Original_Linewidth": wedge.get_linewidth(),
        "Original_Zorder": wedge.get_zorder(),
    }
Original_Autotext_Design = {}
for Autotext in All_Autotexts:
    Original_Autotext_Design[Autotext] = {
        "Original_Fontsize": Autotext.get_fontsize(),
        "Original_Color": Autotext.get_color(),
        "Original_Fontweight": Autotext.get_fontweight(),
        "Original_Zorder": Autotext.get_zorder(),
        "Original_Position": Autotext.get_position(),
        "Original_Rotation": Autotext.get_rotation(),
        "Original_Rotation_Mode": Autotext.get_rotation_mode(),
    }

Original_Label_Design = {}  ##Save base design of each outer label
for label in Outer_Texts:
    Original_Label_Design[label] = {
        "Original_Fontsize": label.get_fontsize(),
        "Original_Color": label.get_color(),
        "Original_Fontweight": label.get_fontweight(),
        "Original_Zorder": label.get_zorder(),
        "Original_Position": label.get_position(),
        "Original_Rotation": label.get_rotation(),
        "Original_Rotation_Mode": label.get_rotation_mode(),
    }

Active_Wedge = None
Active_Autotext = None
Active_Label = None

## Define function to reset the style of the active wedge
def Reset_Wedge_and_Autotext_and_Label(wedge, autotext=None, label=None):
    style = Original_Design[wedge]

    wedge.set_radius(style["Original_Radius"])

    if style["Original_Width"] is not None:
        wedge.set_width(style["Original_Width"])
    wedge.set_facecolor(style["Original_Facecolor"])
    wedge.set_edgecolor(style["Original_Edgecolor"])
    wedge.set_linewidth(style["Original_Linewidth"])
    wedge.set_zorder(style["Original_Zorder"])

    if autotext is not None:
        autotext_style = Original_Autotext_Design[autotext]
        autotext.set_fontsize(autotext_style["Original_Fontsize"])
        autotext.set_color(autotext_style["Original_Color"])
        autotext.set_fontweight(autotext_style["Original_Fontweight"])
        autotext.set_zorder(autotext_style["Original_Zorder"])
        autotext.set_position(autotext_style["Original_Position"])
        autotext.set_rotation(autotext_style["Original_Rotation"])
        autotext.set_rotation_mode(autotext_style["Original_Rotation_Mode"])
    if label is not None:
        label_style = Original_Label_Design[label]
        label.set_fontsize(label_style["Original_Fontsize"])
        label.set_color(label_style["Original_Color"])
        label.set_fontweight(label_style["Original_Fontweight"])
        label.set_zorder(label_style["Original_Zorder"])
        label.set_position(label_style["Original_Position"])
        label.set_rotation(label_style["Original_Rotation"])
        label.set_rotation_mode(label_style["Original_Rotation_Mode"])
        label.set_bbox(None)
        

## failed attempt to highlight the wedges in a nice way
## Define a function to highlight a wedge 
# def Highlight_Wedge(wedge):
#     style = Original_Design[wedge]
#     Original_Width = style["Original_Width"]
#     Original_Radius = style["Original_Radius"]

#     if wedge in Inner_Wedges: ## keep outer rim fixed, highlight inwards
#         wedge.set_radius(Original_Radius)

#         if Original_Width is not None:
#             wedge.set_width(Original_Width * 1.1)

#     elif wedge in Outer_Wedges: ## keep inner rim fixed, highlight outward
#         if Original_Width is not None:
#             old_inner_rim = Original_Radius - Original_Width
#             new_radius = Original_Radius * 1.05
#             new_width = new_radius - old_inner_rim

#             wedge.set_radius(new_radius)
#             wedge.set_width(new_width)
#         else:
#             wedge.set_radius(Original_Radius * 1.05)

#     wedge.set_facecolor("deepskyblue")
#     wedge.set_edgecolor("blue")
#     wedge.set_linewidth(2.5)
#     wedge.set_zorder(10)


def Highlight_Wedge_and_Autotext_and_Label(wedge):
    style = Original_Design[wedge]
    Original_Width = style["Original_Width"]
    Autotext = Wedge_To_Autotext[wedge]

    if wedge in Inner_Wedges:
        wedge.set_radius(style["Original_Radius"])
        if Original_Width is not None:
            wedge.set_width(Original_Width * 1.1)
    elif wedge in Outer_Wedges:
        if Original_Width is not None:
            wedge.set_radius(style["Original_Radius"] * 1.1)
            wedge.set_width(Original_Width * 1.1)
    else:
        wedge.set_radius(style["Original_Radius"])

    label = None
    if wedge in Outer_Wedges:
        label = Wedge_To_Label[wedge]
    
    wedge.set_facecolor("deepskyblue")
    wedge.set_edgecolor("blue")
    wedge.set_linewidth(2.5)
    wedge.set_zorder(10)
    Autotext.set_fontsize(Original_Autotext_Design[Autotext]["Original_Fontsize"] * 1.8)
    Autotext.set_fontweight("bold")
    Autotext.set_zorder(11)
    raw_angle = (wedge.theta1 + wedge.theta2) / 2
    theta = np.deg2rad(raw_angle)

    text_angle = raw_angle
    if 90 < text_angle < 270:
        text_angle += 180

    Autotext.set_rotation(text_angle)
    Autotext.set_rotation_mode("anchor")

    percent = Wedge_To_Percent[wedge]

    if wedge.width is not None:
        if percent < 1.3:
            Text_Radius= wedge.r-0.55
        else:
            Text_Radius = wedge.r - wedge.width / 2
    else:
        if percent < 1.3:
            Text_Radius = wedge.r-0.55
        else:
            Text_Radius = wedge.r / 2

    if label is not None:
        label.set_fontsize(Original_Label_Design[label]["Original_Fontsize"] * 1.2)
        label.set_fontweight("bold")
        label.set_color("black")
        label.set_zorder(30)
        label.set_bbox(dict(facecolor="#0AC2FF", edgecolor="none", pad=8))
        label.set_rotation(text_angle)
        label.set_rotation_mode("anchor")
        label_radius = wedge.r + 0.08
        lx = wedge.center[0] + label_radius * np.cos(theta)
        ly = wedge.center[1] + label_radius * np.sin(theta)
        label.set_position((lx, ly))

    if 90 < text_angle < 270:
        text_angle += 180

    cx, cy = wedge.center
    x = cx + Text_Radius * np.cos(theta)
    y = cy + Text_Radius * np.sin(theta)

    Autotext.set_position((x, y))



## define a function how to handle hover events
def On_Hover(event):
    global Active_Wedge, Active_Autotext, Active_Label

    if event.inaxes != ax:
        if Active_Wedge is not None:
            Reset_Wedge_and_Autotext_and_Label(Active_Wedge, Active_Autotext, Active_Label)
            Active_Wedge = None
            Active_Autotext = None
            Active_Label = None
            fig.canvas.draw_idle()
        return

    Hovered_Wedge = None
    for wedge in All_Wedges:
        contains, _ = wedge.contains(event)
        if contains:
            Hovered_Wedge = wedge
            break

    hovered_autotext = None
    hovered_label = None

    if Hovered_Wedge is not None:
        hovered_autotext = Wedge_To_Autotext[Hovered_Wedge]
        if Hovered_Wedge in Outer_Wedges:
            hovered_label = Wedge_To_Label[Hovered_Wedge]

    if Hovered_Wedge is Active_Wedge:
        return

    if Active_Wedge is not None:
        Reset_Wedge_and_Autotext_and_Label(Active_Wedge, Active_Autotext, Active_Label)

    if Hovered_Wedge is not None:
        Highlight_Wedge_and_Autotext_and_Label(Hovered_Wedge)

    Active_Wedge = Hovered_Wedge
    Active_Autotext = hovered_autotext
    Active_Label = hovered_label
    fig.canvas.draw_idle()

fig.canvas.mpl_connect("motion_notify_event", On_Hover)

        
plt.show()

############### ################# ################# ################
## Failed Attempt:
# BAR GRAPH
## X AXIS info
# x=df["Item Type"].unique()
## Y AXIS info
# y=df.groupby("Item Type")["Total Profit"].sum()

# plt.bar(x,y)
# plt.xlabel("Item Type")
# plt.ylabel("Total Profit")
# plt.title("Total Profit by Item Type")
# plt.xticks(rotation=45)
# plt.tight_layout()

# ## choosing countries for display on sidebar
# optional_countries = sorted(df["Country"].unique())
# optional_types = sorted(df["Item Type"].unique())

# selected_countries = st.sidebar.multiselect("Select Countries", optional_countries)
# selected_types = st.sidebar.multiselect("Select Item Type", optional_types)

# # final filtered data
# filtered_df = df.copy()

# if selected_countries:
#     filtered_df = filtered_df[filtered_df["Country"].isin(selected_countries)]

# if selected_types:
#     filtered_df = filtered_df[filtered_df["Item Type"].isin(selected_types)]

# if filtered_df.empty:
#     st.warning("No data for this combination. Try a different filter.")
# else:
#     x=filtered_df["Item Type"].unique()
#     y=filtered_df.groupby("Item Type")["Total Profit"].sum()
#     plt.bar(x,y)
#     plt.xlabel("Item Type")
#     plt.ylabel("Total Profit")
#     plt.title("Total Profit by Item Type")
# plt.xticks(rotation=45)
# plt.tight_layout()
# st.pyplot(plt)



##failed attempt:
    # Country_Profit,
    # labels=Country_Profit.index.get_level_values("Country"),
    # autopct="%1.1f%%",
    # colors=["#ff9999", "#66b3ff", "#99ff99", "#ffcc99", "#c2c2f0", "#ffb3e6", "#c2f0c2", "#ff6666", "#ffcc99"],
    # radius=1.2,
    # wedgeprops={"edgecolor": "white", "linewidth": 2},
    # textprops={"fontsize": 10, "color": "black"})

# ##inner pie chart (regions)
# plt.pie(
#     Region_Profit,
#     labels=Region_Profit.index.get_level_values("Region"),
#     autopct="%1.1f%%",
#     colors=["#ff9999", "#66b3ff", "#99ff99", "#ffcc99", "#c2c2f0", "#ffb3e6", "#c2f0c2", "#ff6666", "#ffcc99"],
#     radius=0.5,
#     wedgeprops={"edgecolor": "white", "linewidth": 2},
#     textprops={"fontsize": 10, "color": "black"}
#     )

