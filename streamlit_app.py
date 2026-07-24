from __future__ import annotations

from urllib.parse import quote_plus

import altair as alt
import pandas as pd
import streamlit as st

from calculations import (
    capacity_status,
    layer_storage_m3,
    overflow_volume_m3,
    porosity_from_void_ratio,
    rainfall_depth_mm,
    rainfall_volume_m3,
    retained_volume_m3,
    volume_reduction_fraction,
)


st.set_page_config(
    page_title="Porous Lane Stormwater Calculator",
    page_icon="💧",
    layout="wide",
)

DURATION_ORDER = ["3 hr", "2 hr", "1 hr", "30 min", "15 min", "10 min"]
AEP_ORDER = ["50%", "20%", "10%", "5%", "2%", "1%"]


@st.cache_data
def load_rainfall_data() -> pd.DataFrame:
    data = pd.read_csv("rainfall_data.csv")
    data["aep_label"] = data["aep_percent"].astype(int).astype(str) + "%"
    return data


def bom_ifd_url(latitude: float, longitude: float, label: str) -> str:
    return (
        "https://www.bom.gov.au/water/designRainfalls/revised-ifd/"
        "?design=ifds"
        "&sdmin=true"
        "&sdhr=true"
        "&sdday=true"
        "&coordinate_type=dd"
        f"&latitude={latitude}"
        f"&longitude={longitude}"
        f"&user_label={quote_plus(label)}"
        "&values=depths"
        "&update="
    )


def format_result_table(results: pd.DataFrame) -> pd.io.formats.style.Styler:
    view = results[
        [
            "Duration",
            "AEP",
            "Intensity (mm/h)",
            "Rainfall depth (mm)",
            "Rainfall volume (m³)",
            "Total-system status",
            "Total-system reduction (%)",
            "Storage-only status",
            "Storage-only reduction (%)",
            "Overflow (m³)",
        ]
    ].copy()

    def status_colour(value: object) -> str:
        if value == "Overflow":
            return "background-color: #f8d7da; color: #842029;"
        if value == "Within capacity":
            return "background-color: #d1e7dd; color: #0f5132;"
        return ""

    return (
        view.style
        .format(
            {
                "Intensity (mm/h)": "{:.2f}",
                "Rainfall depth (mm)": "{:.2f}",
                "Rainfall volume (m³)": "{:.2f}",
                "Total-system reduction (%)": "{:.1f}%",
                "Storage-only reduction (%)": "{:.1f}%",
                "Overflow (m³)": "{:.2f}",
            }
        )
        .map(
            status_colour,
            subset=["Total-system status", "Storage-only status"],
        )
    )


rainfall_data = load_rainfall_data()

st.title("Porous Lane Stormwater Calculator")
st.caption(
    "Preliminary event runoff-volume calculator based on the "
    "SCENARIO EXAMPLE engineering logic."
)

with st.expander("Important model scope", expanded=False):
    st.write(
        "This version compares event rainfall volume against available "
        "void storage. It does not yet calculate a routed hydrograph or "
        "true peak-flow reduction."
    )

input_tab, results_tab, assumptions_tab = st.tabs(
    ["1. Design inputs", "2. Results", "3. Assumptions"]
)

with input_tab:
    st.subheader("A. Location and design function")

    c1, c2 = st.columns(2)

    with c1:
        location = st.selectbox(
            "Location — select from validated BoM datasets",
            sorted(rainfall_data["location"].unique()),
            help=(
                "The current prototype contains the exact Melbourne and "
                "Adelaide rainfall tables used in the uploaded workbook."
            ),
        )

    selected_location = rainfall_data[
        rainfall_data["location"] == location
    ]
    latitude = float(selected_location["latitude"].iloc[0])
    longitude = float(selected_location["longitude"].iloc[0])

    with c2:
        design_function = st.selectbox(
            "Design function",
            [
                "Trafficable Mix",
                "Pedestrian Mix",
            ],
            help=(
                "Trafficable Mix: car parks and driveways. "
                "Pedestrian Mix: footpaths, tree surrounds, bike lanes, "
                "shared paths, golf-cart paths and nature strips."
            ),
        )

    pavement_thickness_mm = (
        50.0 if design_function == "Trafficable Mix" else 40.0
    )

    loc1, loc2, loc3 = st.columns(3)
    loc1.metric("Latitude", f"{latitude:.3f}")
    loc2.metric("Longitude", f"{longitude:.3f}")
    loc3.metric(
        "Pavement thickness — automatic",
        f"{pavement_thickness_mm:.0f} mm",
    )

    st.link_button(
        "Open this location in the BoM IFD system",
        bom_ifd_url(latitude, longitude, location),
    )

    st.divider()
    st.subheader("B. Site area — manual inputs")

    a1, a2 = st.columns(2)
    with a1:
        catchment_area_m2 = st.number_input(
            "Total contributing catchment area (m²)",
            min_value=0.01,
            value=1604.10,
            step=1.0,
            help=(
                "Manual input from the client design. The model assumes "
                "all rainfall runoff from this area reaches Porous Lane."
            ),
        )
    with a2:
        pavement_area_m2 = st.number_input(
            "Porous Lane pavement area (m²)",
            min_value=0.0,
            value=420.70,
            step=1.0,
            help="Manual input from the proposed layout.",
        )

    if pavement_area_m2 > catchment_area_m2:
        st.error(
            "Porous Lane area cannot exceed the total contributing "
            "catchment area."
        )
        st.stop()

    st.divider()
    st.subheader("C. Pavement layer")

    pavement_void_ratio = 0.42
    pavement_porosity = porosity_from_void_ratio(pavement_void_ratio)
    pavement_storage = layer_storage_m3(
        pavement_area_m2,
        pavement_thickness_mm,
        pavement_porosity,
    )

    p1, p2, p3, p4 = st.columns(4)
    p1.metric(
        "Thickness — automatic",
        f"{pavement_thickness_mm:.0f} mm",
    )
    p2.metric("Void ratio — automatic", f"{pavement_void_ratio:.2f}")
    p3.metric("Porosity — automatic", f"{pavement_porosity:.3f}")
    p4.metric("Pavement void storage", f"{pavement_storage:.2f} m³")

    st.divider()
    st.subheader("D. Screening / storage layer")

    include_storage = st.toggle(
        "Include a screening/storage layer",
        value=True,
        help=(
            "When selected, its plan area is automatically set equal "
            "to the Porous Lane pavement area, following the workbook."
        ),
    )

    if include_storage:
        storage_area_m2 = pavement_area_m2
        storage_thickness_mm = st.number_input(
            "Storage-layer thickness (mm) — manual input",
            min_value=0.0,
            value=300.0,
            step=5.0,
        )
        storage_void_ratio = 0.50
    else:
        storage_area_m2 = 0.0
        storage_thickness_mm = 0.0
        storage_void_ratio = 0.50

    storage_porosity = porosity_from_void_ratio(storage_void_ratio)
    storage_capacity = layer_storage_m3(
        storage_area_m2,
        storage_thickness_mm,
        storage_porosity,
    )
    total_capacity = pavement_storage + storage_capacity

    geocell_message = (
        "Need geocell"
        if include_storage and storage_thickness_mm > 75
        else "Geocell not triggered by the current rule"
    )

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Storage area — automatic", f"{storage_area_m2:.2f} m²")
    s2.metric("Void ratio — automatic", f"{storage_void_ratio:.2f}")
    s3.metric("Porosity — automatic", f"{storage_porosity:.3f}")
    s4.metric("Storage-layer capacity", f"{storage_capacity:.2f} m³")

    st.info(f"Geocell check — automatic: **{geocell_message}**")

    st.divider()
    st.subheader("E. Subgrade")

    subgrade = st.selectbox(
        "Subgrade type",
        ["Clay", "Sand"],
        help=(
            "This is recorded to follow the workbook. In the current "
            "calculation it does not alter the result because ground "
            "exfiltration is assumed to be zero."
        ),
    )

    st.caption(
        f"Selected subgrade: {subgrade}. Current exfiltration allowance: 0."
    )

    st.divider()
    st.subheader("Automatic design summary")
    k1, k2, k3 = st.columns(3)
    k1.metric("Pavement storage", f"{pavement_storage:.2f} m³")
    k2.metric("Storage-layer capacity", f"{storage_capacity:.2f} m³")
    k3.metric("Total system capacity", f"{total_capacity:.2f} m³")


# Calculate all 36 combinations automatically.
records: list[dict[str, object]] = []

for row in selected_location.itertuples(index=False):
    event_depth = rainfall_depth_mm(
        float(row.intensity_mm_h),
        float(row.duration_min),
    )
    rain_volume = rainfall_volume_m3(
        catchment_area_m2,
        event_depth,
    )

    total_reduction = volume_reduction_fraction(
        total_capacity,
        rain_volume,
    )
    storage_only_reduction = volume_reduction_fraction(
        storage_capacity,
        rain_volume,
    )

    records.append(
        {
            "Duration": row.duration_label,
            "Duration (min)": int(row.duration_min),
            "AEP": row.aep_label,
            "AEP (%)": int(row.aep_percent),
            "Intensity (mm/h)": float(row.intensity_mm_h),
            "Rainfall depth (mm)": event_depth,
            "Rainfall volume (m³)": rain_volume,
            "Total-system status": capacity_status(
                rain_volume,
                total_capacity,
            ),
            "Total-system reduction (%)": total_reduction * 100.0,
            "Storage-only status": capacity_status(
                rain_volume,
                storage_capacity,
            ),
            "Storage-only reduction (%)": (
                storage_only_reduction * 100.0
            ),
            "Retained volume (m³)": retained_volume_m3(
                rain_volume,
                total_capacity,
            ),
            "Overflow (m³)": overflow_volume_m3(
                rain_volume,
                total_capacity,
            ),
        }
    )

results = pd.DataFrame(records)
results["Duration"] = pd.Categorical(
    results["Duration"],
    categories=DURATION_ORDER,
    ordered=True,
)
results["AEP"] = pd.Categorical(
    results["AEP"],
    categories=AEP_ORDER,
    ordered=True,
)
results = results.sort_values(["Duration", "AEP"]).reset_index(drop=True)

with results_tab:
    st.subheader(f"All design rainfall results — {location}")

    r1, r2, r3 = st.columns(3)
    r1.metric("Pavement void storage", f"{pavement_storage:.2f} m³")
    r2.metric("Storage-layer capacity", f"{storage_capacity:.2f} m³")
    r3.metric("Total system capacity", f"{total_capacity:.2f} m³")

    st.markdown("#### Flow-reduction heatmap — total system")

    heatmap_base = alt.Chart(results).encode(
        x=alt.X(
            "AEP:N",
            sort=AEP_ORDER,
            title="Annual Exceedance Probability (AEP)",
        ),
        y=alt.Y(
            "Duration:N",
            sort=DURATION_ORDER,
            title="Storm duration",
        ),
        tooltip=[
            alt.Tooltip("Duration:N"),
            alt.Tooltip("AEP:N"),
            alt.Tooltip(
                "Rainfall depth (mm):Q",
                format=".2f",
            ),
            alt.Tooltip(
                "Rainfall volume (m³):Q",
                format=".2f",
            ),
            alt.Tooltip(
                "Total-system reduction (%):Q",
                format=".1f",
            ),
            alt.Tooltip("Total-system status:N"),
        ],
    )

    heatmap = heatmap_base.mark_rect().encode(
        color=alt.Color(
            "Total-system reduction (%):Q",
            title="Reduction (%)",
            scale=alt.Scale(
                domain=[0, 50, 100],
                range=["#d73027", "#fee08b", "#1a9850"],
            ),
        )
    )

    labels = heatmap_base.mark_text(
        baseline="middle",
        fontSize=12,
    ).encode(
        text=alt.Text(
            "Total-system reduction (%):Q",
            format=".0f",
        ),
        color=alt.condition(
            "datum['Total-system reduction (%)'] < 60",
            alt.value("white"),
            alt.value("black"),
        ),
    )

    st.altair_chart(
        (heatmap + labels).properties(height=380),
        use_container_width=True,
    )

    st.markdown("#### Rainfall volume versus storage capacity")

    selected_duration = st.selectbox(
        "Choose a duration for the comparison chart",
        DURATION_ORDER,
        index=0,
    )

    chart_data = results[
        results["Duration"].astype(str) == selected_duration
    ].copy()

    rainfall_bars = (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X(
                "AEP:N",
                sort=AEP_ORDER,
                title="Annual Exceedance Probability (AEP)",
            ),
            y=alt.Y(
                "Rainfall volume (m³):Q",
                title="Volume (m³)",
            ),
            tooltip=[
                alt.Tooltip("AEP:N"),
                alt.Tooltip(
                    "Rainfall volume (m³):Q",
                    format=".2f",
                ),
            ],
        )
    )

    capacity_data = pd.DataFrame(
        {
            "Capacity": [
                "Total system",
                "Storage layer only",
            ],
            "Volume (m³)": [
                total_capacity,
                storage_capacity,
            ],
        }
    )

    capacity_lines = (
        alt.Chart(capacity_data)
        .mark_rule(strokeDash=[7, 5], strokeWidth=3)
        .encode(
            y=alt.Y("Volume (m³):Q"),
            color=alt.Color(
                "Capacity:N",
                title="Capacity line",
            ),
            tooltip=[
                alt.Tooltip("Capacity:N"),
                alt.Tooltip("Volume (m³):Q", format=".2f"),
            ],
        )
    )

    st.altair_chart(
        (rainfall_bars + capacity_lines)
        .properties(
            height=380,
            title=f"{selected_duration} event",
        ),
        use_container_width=True,
    )

    st.markdown("#### Detailed results table")
    st.dataframe(
        format_result_table(results),
        use_container_width=True,
        hide_index=True,
        height=620,
    )

    csv_download = results.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download results as CSV",
        data=csv_download,
        file_name="porous_lane_stormwater_results.csv",
        mime="text/csv",
    )

with assumptions_tab:
    st.subheader("Current assumptions and limitations")
    st.write(
        "1. All rainfall runoff from the entire contributing catchment "
        "is assumed to reach the Porous Lane treatment area."
    )
    st.write(
        "2. No water is credited as exfiltrating into the native "
        "subgrade."
    )
    st.write(
        "3. The storage-layer area is equal to the pavement area when "
        "the layer is included."
    )
    st.write(
        "4. Pavement void ratio is fixed at 0.42 and storage-layer void "
        "ratio is fixed at 0.50, following the workbook test values."
    )
    st.write(
        "5. Pavement thickness is automatically 50 mm for Trafficable "
        "Mix and 40 mm for Pedestrian Mix."
    )
    st.write(
        "6. The geocell message uses the workbook rule: thickness above "
        "75 mm triggers 'Need geocell'."
    )
    st.write(
        "7. The result is theoretical event runoff-volume reduction, "
        "not true peak-flow reduction."
    )
    st.write(
        "8. The current location list uses locally stored, validated BoM "
        "IFD data. It does not scrape the BoM webpage."
    )

    st.warning(
        "Before this is used as a public design tool, Porous Lane should "
        "confirm the default material values, valid ranges, exfiltration "
        "method, slope effect, clogging allowance, and engineering "
        "disclaimer."
    )
