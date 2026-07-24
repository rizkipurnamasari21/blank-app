import streamlit as st

st.set_page_config(
    page_title="Porous Lane Calculator",
    page_icon="💧",
    layout="wide",
)

st.title("Porous Lane Stormwater Calculator")
st.write(
    "Preliminary calculator for estimating stormwater "
    "runoff-volume reduction."
)

st.header("Project inputs")

catchment_area = st.number_input(
    "Total catchment area (m²)",
    min_value=0.0,
    value=1604.10,
    step=1.0,
)

pavement_area = st.number_input(
    "Porous Lane area (m²)",
    min_value=0.0,
    value=420.70,
    step=1.0,
)

rainfall_depth = st.number_input(
    "Rainfall depth (mm)",
    min_value=0.0,
    value=30.0,
    step=0.1,
)

pavement_depth = st.number_input(
    "Pavement thickness (mm)",
    min_value=0.0,
    value=50.0,
    step=5.0,
)

pavement_void_ratio = st.number_input(
    "Pavement void ratio",
    min_value=0.0,
    value=0.42,
    step=0.01,
)

storage_depth = st.number_input(
    "Storage-layer thickness (mm)",
    min_value=0.0,
    value=300.0,
    step=10.0,
)

storage_void_ratio = st.number_input(
    "Storage-layer void ratio",
    min_value=0.0,
    value=0.50,
    step=0.01,
)

if pavement_area > catchment_area:
    st.error("Porous Lane area cannot exceed the catchment area.")
else:
    pavement_porosity = (
        pavement_void_ratio / (1 + pavement_void_ratio)
    )

    storage_porosity = (
        storage_void_ratio / (1 + storage_void_ratio)
    )

    pavement_storage = (
        pavement_area
        * pavement_depth
        / 1000
        * pavement_porosity
    )

    storage_layer_capacity = (
        pavement_area
        * storage_depth
        / 1000
        * storage_porosity
    )

    total_storage = (
        pavement_storage + storage_layer_capacity
    )

    rainfall_volume = (
        catchment_area
        * rainfall_depth
        / 1000
    )

    retained_volume = min(
        rainfall_volume,
        total_storage,
    )

    overflow_volume = max(
        0.0,
        rainfall_volume - total_storage,
    )

    reduction = (
        min(1.0, total_storage / rainfall_volume)
        if rainfall_volume > 0
        else 0.0
    )

    st.header("Results")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Received rainfall",
        f"{rainfall_volume:.2f} m³",
    )

    col2.metric(
        "Total storage",
        f"{total_storage:.2f} m³",
    )

    col3.metric(
        "Runoff-volume reduction",
        f"{reduction:.1%}",
    )

    col4, col5, col6 = st.columns(3)

    col4.metric(
        "Pavement-layer storage",
        f"{pavement_storage:.2f} m³",
    )

    col5.metric(
        "Storage-layer capacity",
        f"{storage_layer_capacity:.2f} m³",
    )

    col6.metric(
        "Potential overflow",
        f"{overflow_volume:.2f} m³",
    )

    if overflow_volume > 0:
        st.error("Storage exceeded")
    else:
        st.success("Within storage capacity")

    with st.expander("Calculation assumptions"):
        st.write(
            "- All runoff from the catchment reaches "
            "the Porous Lane treatment area."
        )
        st.write(
            "- No exfiltration into the underlying "
            "native subgrade is included."
        )
        st.write(
            "- The result represents event runoff-volume "
            "reduction, not peak-flow reduction."
        )