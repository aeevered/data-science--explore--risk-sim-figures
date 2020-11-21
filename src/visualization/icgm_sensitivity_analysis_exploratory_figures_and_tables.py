# %% REQUIRED LIBRARIES
import os
import pandas as pd
import numpy as np
import warnings
import plotly.graph_objects as go
import plotly.express as px
from plotly.offline import plot
import plotly.io as pio
import datetime as dt
import itertools
from save_view_fig import save_view_fig
import tarfile
import json
from scipy import stats
import tidepool_data_science_metrics as metrics
from plotly.subplots import make_subplots
from risk_scenario_figures_plotly import create_simulation_figure_plotly
from risk_scenario_figures_shared_functions import data_loading_and_preparation
import plotly.figure_factory as ff

# from tidepool_data_science_models.models.icgm_sensor_generator_functions import (
#     calc_mard,
#     preprocess_data,
#     calc_mbe,
#     calc_icgm_sc_table,
#     calc_icgm_special_controls_loss,
# )

utc_string = dt.datetime.utcnow().strftime("%Y-%m-%d-%H-%m-%S")

# Calculate MBE and MARD (https://github.com/tidepool-org/icgm-sensitivity-analysis/blob/jameno/analysis-tables/src/simulator_functions.py)
def add_error_fields(df):
    # default icgm and ysi ranges [40, 400] and [0, 900]
    sensor_bg_range = (40, 400)
    bg_range = (0, 900)
    sensor_min, sensor_max = sensor_bg_range
    bg_min, bg_max = bg_range

    # calculate the icgm error (difference and percentage)
    sensor_bg_values = df["bg_sensor"].values
    bg_values = df["bg"].values
    icgm_error = sensor_bg_values - bg_values

    df["icgmError"] = icgm_error
    abs_difference_error = np.abs(icgm_error)
    df["absError"] = abs_difference_error
    df["absRelDiff"] = 100 * abs_difference_error / bg_values

    df["withinMeasRange"] = (sensor_bg_values >= sensor_min) & (
        sensor_bg_values <= sensor_max
    )

    return df


def calc_mbe(df):

    # default icgm and ysi ranges [40, 400] and [0, 900]

    df = add_error_fields(df)
    return np.mean(df.loc[df["withinMeasRange"], "icgmError"])


def calc_mard(df):
    """ Mean Absolute Relative Deviation (MARD)
    https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5375072/
    """

    df = add_error_fields(df)

    abs_relative_difference_in_measurement_range = df.loc[
        df["withinMeasRange"], "absRelDiff"
    ]
    return np.mean(abs_relative_difference_in_measurement_range)


# Parse out simulation id
def get_sim_id(patient_characteristics_df, filename):
    sensor_num = (
        filename.split("/")[-1]
        .split(".")[2]
        .replace("s", "")
        .replace("Senor", "Sensor")
    )
    vp_id = (
        patient_characteristics_df["patient_scenario_filename"]
        .iloc[0]
        .split("/")[-1]
        .split(".")[0]
        .replace("train_", "")
    )
    bg_test_condition = filename.split(".")[1]
    analysis_type = filename.split(".")[3]
    sim_id = (
        "vp"
        + str(vp_id)
        + ".bg"
        + ".s"
        + str(sensor_num)
        + "."
        + str(bg_test_condition)
        + "."
        + analysis_type
    )
    return sim_id


def get_data_old_format(
    filename, simulation_df, patient_characteristics_df, sensor_characteristics_df = ""
):
    sim_id = get_sim_id(patient_characteristics_df, filename)
    virtual_patient_num = "vp" + str(
        patient_characteristics_df["patient_scenario_filename"]
        .iloc[0]
        .split("/")[-1]
        .split(".")[0]
        .replace("train_", "")
    )
    sensor_num = (
        filename.split("/")[-1]
        .split(".")[2]
        .replace("s", "")
        .replace("Senor", "Sensor")
    )
    patient_scenario_filename = (
        patient_characteristics_df["patient_scenario_filename"].iloc[0].split("/")[-1]
    )
    age = patient_characteristics_df["age"].iloc[0]
    ylw = patient_characteristics_df["ylw"].iloc[0]
    cir = simulation_df["cir"].iloc[0]
    isf = simulation_df["isf"].iloc[0]
    sbr = simulation_df["sbr"].iloc[0]
    starting_bg = simulation_df["bg"].iloc[0]
    starting_bg_sensor = simulation_df["bg_sensor"].iloc[0]
    true_bolus = simulation_df["true_bolus"].iloc[1]

    if "IdealSensor" in filename:
        initial_bias = np.nan
        bias_norm_factor = np.nan
        bias_drift_oscillations = np.nan
        bias_drift_range_start = np.nan
        bias_drift_range_end = np.nan
        noise_coefficient = np.nan
        mard = np.nan
        mbe = np.nan

    else:
        initial_bias = sensor_characteristics_df["initial_bias"].iloc[0]
        bias_norm_factor = sensor_characteristics_df["bias_norm_factor"].iloc[0]
        bias_drift_oscillations = sensor_characteristics_df[
            "bias_drift_oscillations"
        ].iloc[0]
        bias_drift_range_start = sensor_characteristics_df[
            "bias_drift_range_start"
        ].iloc[0]
        bias_drift_range_end = sensor_characteristics_df["bias_drift_range_end"].iloc[0]
        noise_coefficient = sensor_characteristics_df["noise_coefficient"].iloc[0]
        mard = calc_mard(simulation_df)
        mbe = calc_mbe(simulation_df)

    delay = np.nan
    bias_drift_type = np.nan
    bias_type = np.nan
    noise_per_sensor = np.nan
    noise = np.nan
    bias_factor = np.nan
    phi_drift = np.nan
    drift_multiplier = np.nan
    drift_multiplier_start = np.nan
    drift_multiplier_end = np.nan
    noise_max = np.nan

    bg_test_condition = filename.split(".")[1].replace("bg", "")
    analysis_type = filename.split(".")[3]

    LBGI = metrics.glucose.blood_glucose_risk_index(bg_array=simulation_df["bg"])[0]
    LBGI_RS = metrics.glucose.lbgi_risk_score(LBGI)
    DKAI = metrics.insulin.dka_index(simulation_df["iob"], simulation_df["sbr"].iloc[0])
    DKAI_RS = metrics.insulin.dka_risk_score(DKAI)
    HBGI = metrics.glucose.blood_glucose_risk_index(bg_array=simulation_df["bg"])[1]
    BGRI = metrics.glucose.blood_glucose_risk_index(bg_array=simulation_df["bg"])[2]
    percent_lt_54 = metrics.glucose.percent_values_lt_54(bg_array=simulation_df["bg"])

    return [
        filename,
        sim_id,
        virtual_patient_num,
        sensor_num,
        patient_scenario_filename,
        age,
        ylw,
        cir,
        isf,
        sbr,
        starting_bg,
        starting_bg_sensor,
        true_bolus,
        initial_bias,
        bias_norm_factor,
        bias_drift_oscillations,
        bias_drift_range_start,
        bias_drift_range_end,
        noise_coefficient,
        delay,
        bias_drift_type,
        bias_type,
        noise_per_sensor,
        noise,
        bias_factor,
        phi_drift,
        drift_multiplier,
        drift_multiplier_start,
        drift_multiplier_end,
        noise_max,
        mard,
        mbe,
        bg_test_condition,
        analysis_type,
        LBGI,
        LBGI_RS,
        DKAI,
        DKAI_RS,
        HBGI,
        BGRI,
        percent_lt_54,
    ]


def get_data(filename, simulation_df, simulation_characteristics_json_data, baseline=False):
    sim_id = simulation_characteristics_json_data["sim_id"]
    virtual_patient_num = simulation_characteristics_json_data["sim_id"].split(".")[0]
    sensor_num = filename.split(".")[2]
    patient_scenario_filename = (
        filename.split(".")[0]
    )
    age = simulation_characteristics_json_data["controller"]["config"]["age"]
    ylw = simulation_characteristics_json_data["controller"]["config"]["ylw"]
    cir = simulation_characteristics_json_data["patient"]["config"][
        "carb_ratio_schedule"
    ]["schedule"][0]["setting"]
    isf = simulation_characteristics_json_data["patient"]["config"][
        "insulin_sensitivity_schedule"
    ]["schedule"][0]["setting"]
    sbr = simulation_characteristics_json_data["patient"]["config"]["basal_schedule"][
        "schedule"
    ][0]["setting"]

    starting_bg = simulation_df["bg"].iloc[0]
    starting_bg_sensor = simulation_df["bg_sensor"].iloc[0]
    true_bolus = simulation_df["true_bolus"].iloc[1]

    if baseline:
        initial_bias = np.nan
        bias_norm_factor = np.nan
        bias_drift_oscillations = np.nan
        bias_drift_range_start = np.nan
        bias_drift_range_end = np.nan
        noise_coefficient = np.nan
        delay = np.nan
        bias_drift_type = np.nan
        bias_type = np.nan
        noise_per_sensor = np.nan
        noise = np.nan
        bias_factor = np.nan
        phi_drift = np.nan
        drift_multiplier = np.nan
        drift_multiplier_start = np.nan
        drift_multiplier_end = np.nan
        noise_max = np.nan
        mard = np.nan
        mbe = np.nan

    else:
        initial_bias = simulation_characteristics_json_data["patient"]["sensor"][
            "initial_bias"
        ]
        bias_norm_factor = simulation_characteristics_json_data["patient"]["sensor"][
            "bias_norm_factor"
        ]
        bias_drift_oscillations = simulation_characteristics_json_data["patient"][
            "sensor"
        ]["bias_drift_oscillations"]
        bias_drift_range_start = simulation_characteristics_json_data["patient"][
            "sensor"
        ]["bias_drift_range_start"]
        bias_drift_range_end = simulation_characteristics_json_data["patient"][
            "sensor"
        ]["bias_drift_range_end"]
        noise_coefficient = simulation_characteristics_json_data["patient"]["sensor"][
            "noise_coefficient"
        ]

        delay = simulation_characteristics_json_data["patient"]["sensor"]["delay"]
        bias_drift_type = simulation_characteristics_json_data["patient"]["sensor"][
            "bias_drift_type"
        ]
        bias_type = simulation_characteristics_json_data["patient"]["sensor"][
            "bias_type"
        ]
        noise_per_sensor = simulation_characteristics_json_data["patient"]["sensor"][
            "noise_per_sensor"
        ]
        noise = simulation_characteristics_json_data["patient"]["sensor"]["noise"]
        bias_factor = simulation_characteristics_json_data["patient"]["sensor"][
            "bias_factor"
        ]
        phi_drift = simulation_characteristics_json_data["patient"]["sensor"][
            "phi_drift"
        ]
        drift_multiplier = simulation_characteristics_json_data["patient"]["sensor"][
            "drift_multiplier"
        ]
        drift_multiplier_start = simulation_characteristics_json_data["patient"][
            "sensor"
        ]["drift_multiplier_start"]
        drift_multiplier_end = simulation_characteristics_json_data["patient"][
            "sensor"
        ]["drift_multiplier_end"]
        noise_max = simulation_characteristics_json_data["patient"]["sensor"][
            "noise_max"
        ]

        mard = calc_mard(simulation_df)
        mbe = calc_mbe(simulation_df)



    bg_test_condition = filename.split(".")[1].replace("bg", "")
    analysis_type = filename.split(".")[3]

    LBGI = metrics.glucose.blood_glucose_risk_index(bg_array=simulation_df["bg"])[0]
    LBGI_RS = metrics.glucose.lbgi_risk_score(LBGI)
    DKAI = metrics.insulin.dka_index(simulation_df["iob"], simulation_df["sbr"].iloc[0])
    DKAI_RS = metrics.insulin.dka_risk_score(DKAI)
    HBGI = metrics.glucose.blood_glucose_risk_index(bg_array=simulation_df["bg"])[1]
    BGRI = metrics.glucose.blood_glucose_risk_index(bg_array=simulation_df["bg"])[2]
    percent_lt_54 = metrics.glucose.percent_values_lt_54(bg_array=simulation_df["bg"])

    return [
        filename,
        sim_id,
        virtual_patient_num,
        sensor_num,
        patient_scenario_filename,
        age,
        ylw,
        cir,
        isf,
        sbr,
        starting_bg,
        starting_bg_sensor,
        true_bolus,
        initial_bias,
        bias_norm_factor,
        bias_drift_oscillations,
        bias_drift_range_start,
        bias_drift_range_end,
        noise_coefficient,
        delay,
        bias_drift_type,
        bias_type,
        noise_per_sensor,
        noise,
        bias_factor,
        phi_drift,
        drift_multiplier,
        drift_multiplier_start,
        drift_multiplier_end,
        noise_max,
        mard,
        mbe,
        bg_test_condition,
        analysis_type,
        LBGI,
        LBGI_RS,
        DKAI,
        DKAI_RS,
        HBGI,
        BGRI,
        percent_lt_54,
    ]


# %% Visualization Functions
# %% FUNCTIONS
# TODO: us mypy and specify the types

utc_string = dt.datetime.utcnow().strftime("%Y-%m-%d-%H-%m-%S")
# TODO: automatically grab the code version to add to the figures generated
code_version = "v0-1-0"

# adding in some generic methods for tables based on bins
def bin_data(bin_breakpoints):
    # the bin_breakpoints are the points that are greater than or equal to
    return pd.IntervalIndex.from_breaks(bin_breakpoints, closed="left")


def get_metadata_tables(demographic_df, fig_path):
    # %% prepare demographic data for tables

    virtual_patient_group = demographic_df.groupby("virtual_patient_num")
    demographic_reduced_df = virtual_patient_group[
        ["age", "ylw", "CIR", "ISF", "SBR"]
    ].median()

    # get replace age and years living with (ylw) < 0 with np.nan
    demographic_reduced_df[demographic_reduced_df < 0] = np.nan

    # %% Age Breakdown Table
    # TODO: this can be generalized for any time we want to get counts by bins
    age_bin_breakpoints = np.array([0, 7, 14, 25, 50, 100])
    age_bins = bin_data(age_bin_breakpoints)

    # make an age table
    age_table = pd.DataFrame(index=age_bins.astype("str"))
    age_table.index.name = "Age (years old)"

    # cut the data by bin
    demographic_reduced_df["age_bin"] = pd.cut(demographic_reduced_df["age"], age_bins)
    age_table["Count"] = demographic_reduced_df.groupby("age_bin")["age"].count().values

    # add in missing data
    age_table.loc["Missing", "Count"] = demographic_reduced_df["age"].isnull().sum()

    # make sure that counts add up correctly
    # TODO: make a test that checks that the total subjects equal the total counts in the table
    total_virtual_subjects_from_table = age_table["Count"].sum()
    assert total_virtual_subjects_from_table == len(demographic_reduced_df)

    # add total to end of table
    age_table.loc["Total", "Count"] = total_virtual_subjects_from_table

    age_table.reset_index(inplace=True)
    make_table(
        age_table,
        table_name="age-table",
        analysis_name="icgm-sensitivity-analysis",
        cell_height=[30],
        cell_width=[150],
        image_type="png",
        view_fig=True,
        save_fig=True,
        save_fig_path=fig_path,
    )

    # %% Years Living With (YLW) Breakdown Table
    ylw_bin_breakpoints = np.array([0, 1, 5, 100])
    ylw_bins = bin_data(ylw_bin_breakpoints)

    # make an ylw table
    ylw_table = pd.DataFrame(index=ylw_bins.astype("str"))
    ylw_table.index.name = "T1D Duration (years)"

    # cut the data by bin
    demographic_reduced_df["ylw_bin"] = pd.cut(demographic_reduced_df["ylw"], ylw_bins)
    ylw_table["Count"] = demographic_reduced_df.groupby("ylw_bin")["ylw"].count().values

    # add in missing data
    ylw_table.loc["Missing", "Count"] = demographic_reduced_df["ylw"].isnull().sum()

    # make sure that counts add up correctly
    # TODO: make a test that checks that the total subjects equal the total counts in the table
    total_virtual_subjects_from_table = ylw_table["Count"].sum()
    assert total_virtual_subjects_from_table == len(demographic_reduced_df)

    # add total to end of table
    ylw_table.loc["Total", "Count"] = total_virtual_subjects_from_table

    ylw_table.reset_index(inplace=True)
    make_table(
        ylw_table,
        table_name="ylw-table",
        analysis_name="icgm-sensitivity-analysis",
        cell_height=[30],
        cell_width=[200, 150],
        image_type="png",
        view_fig=True,
        save_fig=True,
        save_fig_path=fig_path,
    )
    # %% Carb to Insulin Ratio Table
    cir_bin_breakpoints = np.array(
        [
            demographic_reduced_df["CIR"].min(),
            5,
            10,
            15,
            20,
            25,
            demographic_reduced_df["CIR"].max() + 1,
        ]
    ).astype(int)
    cir_bins = bin_data(cir_bin_breakpoints)

    # make an cir table
    cir_table = pd.DataFrame(index=cir_bins.astype("str"))
    cir_table.index.name = "Carb-to-Insulin-Ratio"

    # cut the data by bin
    demographic_reduced_df["cir_bin"] = np.nan
    demographic_reduced_df["cir_bin"] = pd.cut(demographic_reduced_df["CIR"], cir_bins)
    cir_table["Count"] = demographic_reduced_df.groupby("cir_bin")["CIR"].count().values

    # add in missing data
    cir_table.loc["Missing", "Count"] = demographic_reduced_df["CIR"].isnull().sum()

    # make sure that counts add up correctly
    # TODO: make a test that checks that the total subjects equal the total counts in the table
    total_virtual_subjects_from_table = cir_table["Count"].sum()
    assert total_virtual_subjects_from_table == len(demographic_reduced_df)

    # add total to end of table
    cir_table.loc["Total", "Count"] = total_virtual_subjects_from_table

    cir_table.reset_index(inplace=True)
    make_table(
        cir_table,
        table_name="cir-table",
        analysis_name="icgm-sensitivity-analysis",
        cell_height=[30],
        cell_width=[200, 150],
        image_type="png",
        view_fig=True,
        save_fig=True,
        save_fig_path=fig_path,
    )

    # %% ISF Table
    isf_bin_breakpoints = np.array(
        [
            np.min([demographic_reduced_df["ISF"].min(), 5]),
            10,
            25,
            50,
            75,
            100,
            200,
            np.max([400, demographic_reduced_df["ISF"].max() + 1]),
        ]
    ).astype(int)
    isf_bins = bin_data(isf_bin_breakpoints)

    # make an isf table
    isf_table = pd.DataFrame(index=isf_bins.astype("str"))
    isf_table.index.name = "Insulin Sensitivity Factor"

    # cut the data by bin
    demographic_reduced_df["isf_bin"] = np.nan
    demographic_reduced_df["isf_bin"] = pd.cut(demographic_reduced_df["ISF"], isf_bins)
    isf_table["Count"] = demographic_reduced_df.groupby("isf_bin")["ISF"].count().values

    # add in missing data
    isf_table.loc["Missing", "Count"] = demographic_reduced_df["ISF"].isnull().sum()

    # make sure that counts add up correctly
    # TODO: make a test that checks that the total subjects equal the total counts in the table
    total_virtual_subjects_from_table = isf_table["Count"].sum()
    assert total_virtual_subjects_from_table == len(demographic_reduced_df)

    # add total to end of table
    isf_table.loc["Total", "Count"] = total_virtual_subjects_from_table

    isf_table.reset_index(inplace=True)
    make_table(
        isf_table,
        table_name="isf-table",
        analysis_name="icgm-sensitivity-analysis",
        cell_height=[30],
        cell_width=[250, 150],
        image_type="png",
        view_fig=True,
        save_fig=True,
        save_fig_path=fig_path,
    )

    # %% Basal Rate (BR) Table
    br_bin_breakpoints = np.append(
        np.arange(0, 1.5, 0.25),
        np.arange(1.5, demographic_reduced_df["SBR"].max() + 0.5, 0.5),
    )
    br_bins = bin_data(br_bin_breakpoints)

    # make an br table
    br_table = pd.DataFrame(index=br_bins.astype("str"))
    br_table.index.name = "Basal Rate"

    # cut the data by bin
    demographic_reduced_df["br_bin"] = np.nan
    demographic_reduced_df["br_bin"] = pd.cut(demographic_reduced_df["SBR"], br_bins)
    br_table["Count"] = demographic_reduced_df.groupby("br_bin")["SBR"].count().values

    # add in missing data
    br_table.loc["Missing", "Count"] = demographic_reduced_df["SBR"].isnull().sum()

    # make sure that counts add up correctly
    # TODO: make a test that checks that the total subjects equal the total counts in the table
    total_virtual_subjects_from_table = br_table["Count"].sum()
    assert total_virtual_subjects_from_table == len(demographic_reduced_df)

    # add total to end of table
    br_table.loc["Total", "Count"] = total_virtual_subjects_from_table

    br_table.reset_index(inplace=True)
    make_table(
        br_table,
        table_name="br-table",
        analysis_name="icgm-sensitivity-analysis",
        cell_height=[30],
        cell_width=[200, 150],
        image_type="png",
        view_fig=True,
        save_fig=True,
        save_fig_path=fig_path,
    )


def make_table(
    table_df,
    image_type="png",
    table_name="table-<number-or-name>",
    analysis_name="analysis-<name>",
    cell_height=[30],
    cell_width=[150],
    cell_header_height=[30],
    view_fig=True,
    save_fig=True,
    save_csv=True,
    save_fig_path=os.path.join("..", "..", "reports", "figures"),
):
    # TODO: reduce the number of inputs to: df, style_dict, and save_dict
    table_cols = table_df.columns
    n_rows, n_cols = table_df.shape
    _table = go.Table(
        columnwidth=cell_width,
        header=dict(
            line_color="black",
            values=list(table_cols),
            fill_color="rgb(243, 243, 243)",
            align="center",
            font_size=14,
            height=cell_header_height[0],
        ),
        cells=dict(
            line_color="black",
            values=table_df[table_cols].T,
            fill_color="white",
            align="center",
            font_size=13,
            height=cell_height[0],
        ),
    )

    if len(cell_width) > 1:
        table_width = np.sum(np.asarray(cell_width))
    else:
        table_width = n_cols * cell_width[0]
    table_height = (n_rows + 1.5) * cell_height[0] + cell_header_height[0]
    table_layout = go.Layout(
        margin=dict(l=10, r=10, t=10, b=0), width=table_width, height=table_height
    )
    fig = go.Figure(data=_table, layout=table_layout)

    # print(table_height, table_width)

    save_view_fig(
        fig,
        image_type=image_type,
        figure_name=table_name,
        analysis_name=analysis_name,
        view_fig=view_fig,
        save_fig=save_fig,
        save_fig_path=save_fig_path,
        width=table_width,
        height=table_height,
    )

    """
    if view_fig:
        plot(fig)

    file_name = "{}-{}_{}_{}".format(
        analysis_name, table_name, utc_string, code_version
    )
    if save_fig:
        pio.write_image(
            fig=fig,
            file=os.path.join(save_fig_path, file_name + ".{}".format(image_type)),
            format=image_type,
        )
    """
    file_name = "{}-{}_{}_{}".format(
        analysis_name, table_name, utc_string, code_version
    )

    if save_csv:
        table_df.to_csv(os.path.join(save_fig_path, file_name + ".csv"))

    return


def make_boxplot(
    table_df,
    image_type="png",
    figure_name="<number-or-name>-boxplot",
    analysis_name="analysis-<name>",
    metric="LBGI",
    level_of_analysis="analysis_type",
    notched_boxplot=True,
    y_scale_type="linear",
    view_fig=True,
    save_fig=True,
    save_fig_path=os.path.join("..", "..", "reports", "figures"),
):
    """
    Create a boxplot figure.

    :param table_df: Table name of data to visualize.
    :param image_type: Image type for saving image (eg. png, jpeg).
    :param figure_name: Name of figure (for name of file for saving figure).
    :param analysis_name: Name of analysis (for name of file for saving figure).
    :param metric: Metric from table_df to visualize on the y-axis.
    :param level_of_analysis: Level of analysis breakdown ("all", "bg_test_condition", etc.) for x-axis.
    :param notched_boxplot: True if want the boxplot to be notched boxplot style.
    :param y_scale_type: Log or linear for y axis scale.
    :param view_fig: True if want to view figure.
    :param save_fig: True if want to save figure.
    :param save_fig_path: File path for where to save figure.
    :return:
    """

    # If level_of_analysis is to show all analyses (no breakdown), show as single box.
    if level_of_analysis == "all":
        summary_fig = px.box(
            x=None,
            y=table_df[metric].apply(lambda x: x + 1),
            points=False,
            color_discrete_sequence=px.colors.qualitative.T10,
            notched=notched_boxplot,
            log_y=True,
        )

    # Otherwise show separate boxplot for each breakdown category.
    else:
        table_df = table_df.sort_values([level_of_analysis])

        summary_fig = px.box(
            y=table_df[metric].apply(lambda x: x + 1),
            points=False,
            color=table_df[level_of_analysis + "_label"],
            color_discrete_sequence=px.colors.qualitative.T10,
            # can also explicitly define the sequence: ["red", "green", "blue"],
            notched=notched_boxplot,
            facet_col=table_df[level_of_analysis + "_label"],
            boxmode="overlay",
            log_y=True,
        )

    # TODO: adjust axes back to deal with adding +1 to all y values

    summary_fig.update_layout(
        title="Distribution of "
        + metric
        + " By "
        + level_of_analysis_dict[level_of_analysis],
        showlegend=True,
        # xaxis=dict(title=level_of_analysis_dict[level_of_analysis]),
        yaxis=dict(title=metric),
        plot_bgcolor="#D3D3D3",
        legend_title=level_of_analysis_dict[level_of_analysis],
    )

    summary_fig.update_yaxes(
        type=y_scale_type,
        # range=[0, ],
        tickvals=[1, 2, 3, 6, 11, 26, 51, 101, 251, 501],
        ticktext=["0", "1", "2", "5", "10", "25", "50", "100", "250", "500"],
    )

    summary_fig.update_traces(marker=dict(size=2, opacity=0.3))

    summary_fig.for_each_annotation(
        lambda a: a.update(text=a.text.split("=")[1].replace(" Analysis", ""))
    )

    save_view_fig(
        summary_fig,
        image_type,
        figure_name,
        analysis_name,
        view_fig,
        save_fig,
        save_fig_path,
    )
    return


def make_bubble_plot(
    table_df,
    image_type="png",
    figure_name="<number-or-name>-bubbleplot",
    analysis_name="analysis-<name>",
    metric="LBGI",
    level_of_analysis="analysis_type",
    view_fig=True,
    save_fig=True,
    save_fig_path=os.path.join("..", "..", "reports", "figures"),
):
    if level_of_analysis == "all":

        df = table_df[[metric, metric + " String"]]
        grouped_df = (
            df.groupby([metric, metric + " String"])
            .size()
            .reset_index(name="count")
            .sort_values(by=metric, ascending=True)
        )
        grouped_df["percentage"] = (
            grouped_df["count"] / grouped_df["count"].sum()
        ).apply(lambda x: "{:.1%}".format(x))

        # For adding in rows that don't exist
        metric_values = [0, 1, 2, 3, 4]
        for metric_value in metric_values:
            if not ((grouped_df[metric] == metric_value)).any():
                data = [[metric_value, score_dict[metric_value], 0.001, ""]]
                df2 = pd.DataFrame(
                    data, columns=[metric, metric + " String", "count", "percentage"]
                )
                grouped_df = pd.concat([grouped_df, df2], axis=0, ignore_index=True)

        grouped_df = grouped_df.sort_values(by=[metric], ascending=True)

        summary_fig = px.scatter(
            x=[1] * len(grouped_df[metric]),
            y=grouped_df[metric],
            size=grouped_df["count"],
            color=grouped_df[metric + " String"],
            # text=grouped_df["percentage"],
            color_discrete_map=color_dict,
            size_max=25,
        )

        for index, row in grouped_df.iterrows():
            if row["count"] >= 1:
                summary_fig.add_annotation(
                    x=1,
                    y=row[metric]
                    + 0.15
                    + float(row["percentage"].replace("%", "")) * 0.0015,
                    text=row["percentage"],
                    font=dict(size=12),
                    showarrow=False,
                )

        layout = go.Layout(
            showlegend=True,
            title="Distribution of "
            + metric
            + " Across "
            + level_of_analysis_dict[level_of_analysis],
            yaxis=dict(title=metric, tickvals=[0, 1, 2, 3, 4], range=[-0.25, 4.4]),
            xaxis=dict(
                title="", tickvals=[0, 1, 2], range=[0, 2], showticklabels=False
            ),
            plot_bgcolor="#D3D3D3",
            legend_title="Tidepool " + metric + "<br>",
            legend={"traceorder": "reversed"},
        )

    else:

        df = table_df[
            [
                level_of_analysis,
                level_of_analysis + "_label",
                metric,
                metric + " String",
            ]
        ]
        grouped_df = (
            df.groupby(
                [
                    level_of_analysis,
                    level_of_analysis + "_label",
                    metric,
                    metric + " String",
                ]
            )
            .size()
            .reset_index(name="count")
            .sort_values(
                by=[level_of_analysis, level_of_analysis + "_label", metric],
                ascending=True,
            )
        )

        sum_df = grouped_df.groupby(level_of_analysis)["count"].transform("sum")
        grouped_df["percentage"] = (
            grouped_df["count"].div(sum_df).apply(lambda x: "{:.1%}".format(x))
        )
        grouped_df["percentage"] = grouped_df["percentage"].apply(
            lambda x: x[: len(x) - 3] + "%" if x[len(x) - 3 :] == ".0%" else x
        )

        # For adding in rows that don't exist

        metric_values, analysis_levels, analysis_labels = (
            [0, 1, 2, 3, 4],
            grouped_df[level_of_analysis].unique(),
            grouped_df[level_of_analysis + "_label"].unique(),
        )

        for metric_value, level in itertools.product(metric_values, analysis_levels):
            if not (
                (grouped_df[metric] == metric_value)
                & (grouped_df[level_of_analysis] == level)
            ).any():
                data = [[level, metric_value, score_dict[metric_value], 0.001, ""]]
                df2 = pd.DataFrame(
                    data,
                    columns=[
                        level_of_analysis,
                        metric,
                        metric + " String",
                        "count",
                        "percentage",
                    ],
                )
                df2[level_of_analysis + "_label"] = df2[level_of_analysis].replace(
                    analysis_type_labels
                )
                grouped_df = pd.concat([grouped_df, df2], axis=0, ignore_index=True)

        grouped_df = grouped_df.sort_values(
            by=[level_of_analysis, level_of_analysis + "_label", metric], ascending=True
        )

        summary_fig = px.scatter(
            x=grouped_df[level_of_analysis + "_label"],
            y=grouped_df[metric],
            # text=grouped_df["percentage"],
            size=grouped_df["count"],
            color=grouped_df[metric + " String"],
            color_discrete_map=color_dict,
            # color=grouped_df["count"],
            # colorscale="RdYlGn",
            size_max=25,
        )

        if level_of_analysis == "bg_test_condition":
            annotation_font_size = 9
            height_parameter = 0.1
        else:
            annotation_font_size = 12
            height_parameter = 0.15

        for index, row in grouped_df.iterrows():
            if row["count"] >= 1:
                summary_fig.add_annotation(
                    x=row[level_of_analysis + "_label"],
                    y=row[metric]
                    + height_parameter
                    + float(row["percentage"].replace("%", "")) * 0.0015,
                    text=row["percentage"],
                    font=dict(size=annotation_font_size),
                    showarrow=False,
                )

        if level_of_analysis == "analysis_type":
            tickangle = 45
        else:
            tickangle = 0

        layout = go.Layout(
            showlegend=True,
            title="Distribution of "
            + metric
            + " Across "
            + level_of_analysis_dict[level_of_analysis],
            yaxis=dict(title=metric, tickvals=[0, 1, 2, 3, 4], range=[-0.25, 4.4]),
            xaxis=dict(
                title=level_of_analysis_dict[level_of_analysis],
                type="category",
                tickangle=tickangle,
            ),
            plot_bgcolor="#D3D3D3",
            legend_title="Tidepool " + metric + "<br>",
            legend={"traceorder": "reversed"},
        )

    summary_fig.update_layout(layout)

    save_view_fig(
        summary_fig,
        image_type,
        figure_name,
        analysis_name,
        view_fig,
        save_fig,
        save_fig_path,
    )

    return


def make_histogram(
    table_df,
    image_type="png",
    figure_name="<number-or-name>-histogram",
    analysis_name="analysis-<name>",
    metric="LBGI",
    level_of_analysis="analysis_type",
    view_fig=True,
    save_fig=True,
    save_fig_path=os.path.join("..", "..", "reports", "figures"),
):
    if level_of_analysis == "all":

        df = table_df[[metric]]
        grouped_df = df.groupby([metric]).size().reset_index(name="count")

        summary_fig = px.histogram(
            x=grouped_df[metric],
            nbins=500,
            # log_x=True,
            color_discrete_sequence=px.colors.qualitative.T10,
        )

        layout = go.Layout(
            showlegend=True,
            title="Distribution of "
            + metric
            + " By "
            + level_of_analysis_dict[level_of_analysis],
            plot_bgcolor="#D3D3D3",
            xaxis=dict(title=metric),
            legend_title=level_of_analysis_dict[level_of_analysis],
        )

    else:

        df = table_df[[level_of_analysis, metric]]
        grouped_df = (
            df.groupby([level_of_analysis, metric]).size().reset_index(name="count")
        )

        if level_of_analysis == "analysis_type":
            summary_fig = px.histogram(
                x=grouped_df[metric],
                # log_x=True,
                facet_row=grouped_df[level_of_analysis],
                nbins=500,
                color_discrete_sequence=px.colors.qualitative.T10,
                color=grouped_df[level_of_analysis],
            )
        else:
            summary_fig = px.histogram(
                x=grouped_df[metric],
                # log_x=True,
                facet_col=grouped_df[level_of_analysis],
                facet_col_wrap=3,
                nbins=500,
                color_discrete_sequence=px.colors.qualitative.T10,
                color=grouped_df[level_of_analysis],
            )

        layout = go.Layout(
            showlegend=True,
            title="Distribution of "
            + metric
            + " Across "
            + level_of_analysis_dict[level_of_analysis],
            plot_bgcolor="#D3D3D3",
            # xaxis=dict(title=metric),
            legend_title=level_of_analysis_dict[level_of_analysis],
        )

    summary_fig.update_layout(layout)

    summary_fig.for_each_annotation(
        lambda a: a.update(text=a.text.split("=")[1].replace(" Analysis", ""))
    )

    save_view_fig(
        summary_fig,
        image_type,
        figure_name,
        analysis_name,
        view_fig,
        save_fig,
        save_fig_path,
    )

    return


def make_distribution_table(
    table_df,
    image_type="png",
    table_name="<number-or-name>-table",
    analysis_name="analysis-<name>",
    metric="LBGI",
    level_of_analysis="analysis_type",
    view_fig=True,
    save_fig=True,
    save_csv=True,
    save_fig_path=os.path.join("..", "..", "reports", "figures"),
):

    if level_of_analysis == "all":
        df = table_df[[metric]]
        distribution_df = df[metric].describe().to_frame().transpose()
        distribution_df.insert(0, "", ["All Analyses Combined"], True)
    else:
        df = table_df[[level_of_analysis, metric]]
        distribution_df = (
            df.groupby(level_of_analysis)[[metric]].describe().reset_index()
        )
        distribution_df.columns = distribution_df.columns.droplevel(0)

    if level_of_analysis == "bg_test_condition":
        distribution_df.iloc[:, 0] = distribution_df.iloc[:, 0].apply(
            lambda x: "BG Test Condition {}".format(x)
        )
        # ret = distribution_df.index.map(lambda x: "BG Test Condition {}".format(x))
        # distribution_df.insert(1, "", ret, True)
        # distribution_df.columns = distribution_df.columns.droplevel(0)

    distribution_df = distribution_df.round(2)

    distribution_df = distribution_df.rename(
        columns={
            "mean": "Mean",
            "50%": "Median",
            "std": "Standard Deviation",
            "min": "Minimum",
            "max": "Maximum",
            "count": "Number of Simulations",
        }
    )

    distribution_df = distribution_df.replace(
        "correction_bolus", "Correction Bolus Analyses"
    )
    distribution_df = distribution_df.replace("meal_bolus", "Meal Bolus Analyses")
    distribution_df = distribution_df.replace("temp_basal_only", "Temp Basal Analyses")

    make_table(
        distribution_df,
        image_type=image_type,
        table_name=table_name,
        analysis_name=analysis_name,
        cell_height=[30],
        cell_width=[240, 130, 100, 100, 100, 100, 100, 100],
        cell_header_height=[60],
        view_fig=view_fig,
        save_fig=save_fig,
        save_csv=save_csv,
        save_fig_path=save_fig_path,
    )
    return


# %% Summary Table
def prepare_results_for_summary_table(results_df):

    # %% first remove any/all iCGM sensor batches that did not meet iCGM special controls

    # summary_df_reduced = results_df[results_df["ICGM_PASS%"] == 100]
    summary_df_reduced = results_df.copy()

    # first do all analyses
    all_analyses_summary_df = get_summary_stats(
        summary_df_reduced, "All Analyses Combined"
    )

    # break up by analysis type
    # rename the analysis types
    summary_df_reduced.replace({"temp_basal_only": "Temp Basal Analysis"}, inplace=True)
    summary_df_reduced.replace(
        {"correction_bolus": "Correction Bolus Analysis"}, inplace=True
    )
    summary_df_reduced.replace({"meal_bolus": "Meal Bolus Analysis"}, inplace=True)

    for analysis_type in summary_df_reduced["analysis_type"].unique():
        temp_df = summary_df_reduced[
            summary_df_reduced["analysis_type"] == analysis_type
        ]
        temp_summary = get_summary_stats(temp_df, analysis_type)
        all_analyses_summary_df = pd.concat([all_analyses_summary_df, temp_summary])

    # break up by bg test condition
    summary_df_reduced = summary_df_reduced.sort_values(by=["bg_test_condition"])
    for bg_test_condition in summary_df_reduced["bg_test_condition"].unique():
        temp_df = summary_df_reduced[
            summary_df_reduced["bg_test_condition"] == bg_test_condition
        ]
        temp_summary = get_summary_stats(
            temp_df, "BG Test Condition {}".format(bg_test_condition)
        )

        all_analyses_summary_df = pd.concat([all_analyses_summary_df, temp_summary])

    return all_analyses_summary_df


def get_summary_stats(df, level_of_analysis_name):

    # Commented out risk score columsn pending whether want to show
    # median values for the categorical risk score measures

    # create a summary table
    # NOTE: there is a known bug with plotly tables https://github.com/plotly/plotly.js/issues/3251
    outcome_table_cols = [
        "Median LBGI<br>" "     (IQR)",  # adding in spacing because of bug
        # "Median LBGI Risk Score<br>"
        # "             (IQR)",  # adding in spacing because of bug
        "Median DKAI<br>" "     (IQR)",  # adding in spacing because of bug
        # "Median DKAI Risk Score<br>"
        # "             (IQR)",  # adding in spacing because of bug
    ]
    outcome_names = [
        "LBGI",
        "DKAI",
    ]  # ["LBGI", "LBGI Risk Score", "DKAI", "DKAI Risk Score"]
    count_name = " Number of<br>Simulations"
    summary_table_cols = [count_name] + outcome_table_cols
    summary_table = pd.DataFrame(columns=summary_table_cols)
    summary_table.index.name = "Level of Analysis"

    for outcome, outcome_table_col in zip(outcome_names, outcome_table_cols):
        summary_stats = pd.Series(df[outcome].describe())
        summary_table.loc[level_of_analysis_name, count_name] = summary_stats["count"]
        summary_table.loc[
            level_of_analysis_name, outcome_table_col
        ] = "{} (IQR={}-{})".format(
            summary_stats["50%"].round(1),
            summary_stats["25%"].round(1),
            summary_stats["75%"].round(1),
        )
    return summary_table


def make_frequency_table(
    results_df,
    image_type="png",
    table_name="<number-or-name>-frequency-table",
    analysis_name="analysis-<name>",
    cell_header_height=[60],
    cell_height=[30],
    cell_width=[200, 100, 150, 150],
    metric="LBGI",
    level_of_analysis="analysis_type",
    view_fig=True,
    save_fig=True,
    save_csv=True,
    save_fig_path=os.path.join("..", "..", "reports", "figures"),
):
    level_of_analysis_dict = {
        "all": "All Analyses Combined",
        "analysis_type": "Analysis Type",
        "bg_test_condition": "BG Test Condition",
    }

    if level_of_analysis == "all":
        results_df_reduced = results_df[[metric + " String"]]
        frequency_df = results_df_reduced[metric + " String"].value_counts().to_frame()
        frequency_df = frequency_df.T

        # TODO: update this; not python way to do
        percentage_df = frequency_df.apply(lambda x: x / x.sum(), axis=1)
        for row in range(len(frequency_df)):
            for col in range(len(frequency_df.columns)):
                frequency_df.iloc[row, col] = (
                    str(frequency_df.iloc[row, col])
                    + " ("
                    + str("{:.1%}".format(percentage_df.iloc[row, col]))
                    + ")"
                )
        column_names = [""] + list(color_dict.keys())

        frequency_df.insert(0, "", ["All Analyses Combined"], True)
    else:
        frequency_df = pd.crosstab(
            results_df[level_of_analysis], results_df[metric + " String"]
        ).reset_index()

        # TODO: update this; not python way to do
        percentage_df = frequency_df.loc[
            :, frequency_df.columns != level_of_analysis
        ].apply(lambda x: x / x.sum(), axis=1)
        for row in range(len(frequency_df)):
            for col in range(len(frequency_df.columns) - 1):
                frequency_df.iloc[row, col + 1] = (
                    str(frequency_df.iloc[row, col + 1])
                    + " ("
                    + str("{:.1%}".format(percentage_df.iloc[row, col]))
                    + ")"
                )

        frequency_df = frequency_df.rename(
            columns={level_of_analysis: level_of_analysis_dict[level_of_analysis]}
        )
        column_names = [level_of_analysis_dict[level_of_analysis]] + list(
            color_dict.keys()
        )

    if level_of_analysis == "bg_test_condition":
        frequency_df.iloc[:, 0] = frequency_df.iloc[:, 0].apply(
            lambda x: "BG Test Condition {}".format(x)
        )

    # frequency_df = frequency_df.round(2)

    frequency_df = frequency_df.replace("correction_bolus", "Correction Bolus Analyses")
    frequency_df = frequency_df.replace("meal_bolus", "Meal Bolus Analyses")
    frequency_df = frequency_df.replace("temp_basal_only", "Temp Basal Analyses")

    for metric_value in score_dict.keys():
        if score_dict[metric_value] not in frequency_df.columns:
            frequency_df[score_dict[metric_value]] = "0 (0.0%)"

    frequency_df = frequency_df.reindex(columns=column_names)

    frequency_df = frequency_df.rename(
        columns={"Analysis Type": "", "BG Test Condition": ""}
    )

    make_table(
        frequency_df,
        image_type=image_type,
        table_name=table_name,
        analysis_name=analysis_name,
        cell_height=cell_height,
        cell_width=cell_width,
        cell_header_height=cell_header_height,
        view_fig=view_fig,
        save_fig=save_fig,
        save_csv=save_csv,
        save_fig_path=save_fig_path,
    )
    return


# Functions of cdfs
def ecdf(x):
    x = np.sort(x)

    def result(v):
        return np.searchsorted(x, v, side="right") / x.size

    return result


def create_cdf(
    data,
    title="CDF",
    image_type="png",
    figure_name="<number-or-name>-boxplot",
    analysis_name="analysis-<name>",
    view_fig=True,
    save_fig=True,
    save_fig_path=os.path.join("..", "..", "reports", "figures"),
):

    fig = go.Figure()
    fig.add_scatter(x=np.unique(data), y=ecdf(data)(np.unique(data)))
    fig.update_layout(title=title)

    save_view_fig(
        fig, image_type, figure_name, analysis_name, view_fig, save_fig, save_fig_path,
    )
    return


########## Spearman Correlation Coefficient Table #################
def spearman_correlation_table(
    results_df,
    image_type="png",
    table_name="spearman-correlation-table",
    analysis_name="icgm-sensitivity-analysis",
    cell_header_height=[60],
    cell_height=[30],
    cell_width=[250, 150, 150, 150, 150],
    view_fig=True,
    save_fig=True,
    save_csv=True,
    save_fig_path=os.path.join("..", "..", "reports", "figures"),
):

    rows = [
        "bias_factor",
        "bias_drift_oscillations",
        "bias_drift_range_start",
        "bias_drift_range_end",
        "noise_coefficient",
        "mard",
        "mbe",
    ]
    cols = ["LBGI", "LBGI Risk Score", "DKAI", "DKAI Risk Score"]

    data = {}

    for col in cols:
        row_data = []
        for row in rows:
            rho, pval = stats.spearmanr(results_df[row], results_df[col])
            row_data.append("(" + str(round(rho, 3)) + ", " + str(round(pval, 3)) + ")")
        data[col] = row_data

    spearman_correlation_df = pd.DataFrame(data)
    spearman_correlation_df.insert(
        0,
        "",
        [
            "Bias Factor",
            "Bias Drift Oscillations",
            "Bias Drift Range Start",
            "Bias Drift Range End",
            "Noise Coefficient",
            "Mean Absolute Relative Difference",
            "Mean Bias Error",
        ],
    )

    make_table(
        spearman_correlation_df,
        image_type=image_type,
        table_name=table_name,
        analysis_name=analysis_name,
        cell_height=cell_height,
        cell_width=cell_width,
        cell_header_height=cell_header_height,
        view_fig=view_fig,
        save_fig=save_fig,
        save_csv=save_csv,
        save_fig_path=save_fig_path,
    )
    return


# Function for checking distributions
def create_scatter(
    df,
    x_value="cir",
    y_value="LBGI",
    color_value="",
    image_type="png",
    analysis_name="icgm_sensitivity_analysis",
    view_fig=False,
    save_fig=True,
    title="",
    fig_name="",
    save_fig_path=os.path.join("..", "..", "reports", "figures"),
):

    if color_value != "":
        df = df.sort_values(by=color_value, ascending=True)
        fig = px.scatter(
            data_frame=df,
            x=x_value,
            y=y_value,
            opacity=0.3,
            color=color_value,
            title=title,
            color_continuous_scale=px.colors.sequential.Viridis,
        )  # , color_continuous_scale=px.colors.diverging.RdYlGn)
        fig.update_traces(marker=dict(size=3))
    else:
        fig = px.scatter(data_frame=df, x=x_value, y=y_value, opacity=0.3, title=title)

        fig.update_traces(marker=dict(size=3))

    save_view_fig(
        fig, image_type, fig_name, analysis_name, view_fig, save_fig, save_fig_path,
    )
    return


def generate_all_check_distribution_scatterplots(
    df, fig_path=os.path.join("..", "..", "reports", "figures")
):
    settings = ["CIR", "ISF", "SBR"]
    outcome_metrics = ["LBGI", "DKAI", "HBGI"]
    sensor_characteristics = [
        "bias_drift_oscillations",
        "bias_drift_range_start",
        "bias_drift_range_end",
        "noise_coefficient",
    ]
    analysis_levels = ["bg_test_condition_label", "analysis_type_label"]

    for x, y in itertools.product(sensor_characteristics, outcome_metrics):
        create_scatter(
            df=df,
            x_value=x,
            y_value=y,
            title="Distribution of " + y + " by " + x,
            fig_name="distribution_" + y + "_" + x,
            save_fig_path=fig_path,
        )

    # Investigate high LBGI risk scores
    create_scatter(
        df=df,
        x_value="starting_bg",
        y_value="LBGI",
        color_value="LBGI Risk Score String",
        title="Distribution of LBGI by Simulation Starting BG",
        fig_name="distribution_LBGI_by_starting_bg",
        save_fig_path=fig_path,
    )

    # Check distributions
    unusual_settings_results_df = df[df["CIR"] < 4]
    rest_results_df = df[df["CIR"] >= 4]
    for x, y in itertools.product(sensor_characteristics, ["HBGI", "LBGI"]):
        create_scatter(
            df=unusual_settings_results_df,
            x_value=x,
            y_value=y,
            title="Distribution of " + y + " by " + x + "<br>Where CIR < 4",
            fig_name="distribution_" + y + "_" + x + "_cir<4",
            save_fig_path=fig_path,
        )
        create_scatter(
            df=rest_results_df,
            x_value=x,
            y_value=y,
            title="Distribution of " + y + " by " + x + "<br>Where CIR >= 4",
            fig_name="distribution_" + y + "_" + x + "_cir>=4",
            save_fig_path=fig_path,
        )

    unusual_settings_results_df = df[df["SBR"] < 0.5]
    rest_results_df = df[df["SBR"] >= 0.5]
    for x, y in itertools.product(sensor_characteristics, ["HBGI", "LBGI"]):
        create_scatter(
            df=unusual_settings_results_df,
            x_value=x,
            y_value=y,
            title="Distribution of " + y + " by " + x + "<br>Where SBR < 0.5",
            fig_name="distribution_" + y + "_" + x + "_sbr<0.5",
            save_fig_path=save_fig_path,
        )
        create_scatter(
            df=rest_results_df,
            x_value=x,
            y_value=y,
            title="Distribution of " + y + " by " + x + "<br>Where SBR >= 0.5",
            fig_name="distribution_" + y + "_" + x + "_sbr>=0.5",
            save_fig_path=fig_path,
        )

    for x, y in itertools.product(sensor_characteristics, outcome_metrics):
        for setting in settings:
            create_scatter(
                df=df,
                x_value=x,
                y_value=y,
                color_value=setting,
                title="Distribution of "
                + y
                + " by "
                + x
                + "<br>(Color-coded by "
                + setting
                + ")",
                fig_name="distribution_" + y + "_" + x + "_color_" + setting,
                save_fig_path=fig_path,
            )
        for analysis_level in analysis_levels:
            create_scatter(
                df=df,
                x_value=x,
                y_value=y,
                color_value=analysis_level,
                title="Distribution of "
                + y
                + " by "
                + x
                + "<br>(Color-coded by "
                + analysis_level
                + ")",
                fig_name="distribution_" + y + "_" + x + "_color_" + analysis_level,
                save_fig_path=fig_path,
            )

    for x, y in itertools.product(settings, outcome_metrics):
        for analysis_level in analysis_levels:
            create_scatter(
                df=df,
                x_value=x,
                y_value=y,
                color_value=analysis_level,
                title="Distribution of "
                + y
                + " by "
                + x
                + "<br>(Color-coded by "
                + analysis_level
                + ")",
                fig_name="distribution_" + y + "_" + x + "_color_" + analysis_level,
                save_fig_path=fig_path,
            )

    # Check distributions
    for x, y in itertools.product(settings, outcome_metrics):
        create_scatter(df=df, x_value=x, y_value=y, save_fig_path=fig_path)

    for x, y in itertools.product(settings, settings):
        for color in outcome_metrics:
            create_scatter(
                df=df, x_value=x, y_value=y, color_value=color, save_fig_path=fig_path
            )

    return


def run_pairwise_comparison(results_df, baseline_df, save_fig_folder_name):
    # Add ratio to each row
    # Need to look up for each row into the baseline_df by virtual patient and by
    fig_path = os.path.join(
        "..",
        "..",
        "reports",
        "figures",
        "icgm-sensitivity-paired-comparison-figures",
        save_fig_folder_name,
    )

    if not os.path.exists(fig_path):
        print("making directory " + fig_path + "...")
        os.makedirs(fig_path)

    combined_df = results_df.merge(
        baseline_df,
        how="left",
        left_on=["virtual_patient_num", "analysis_type", "bg_test_condition"],
        right_on=["virtual_patient_num", "analysis_type", "bg_test_condition"],
        suffixes=("_icgm", "_baseline"),
    )

    combined_df["LBGI Ratio"] = combined_df["LBGI_icgm"] / combined_df["LBGI_baseline"]
    combined_df["HBGI Ratio"] = combined_df["HBGI_icgm"] / combined_df["HBGI_baseline"]
    combined_df["DKAI Ratio"] = combined_df["DKAI_icgm"] / combined_df["DKAI_baseline"]
    combined_df["BGRI Ratio"] = combined_df["BGRI_icgm"] / combined_df["BGRI_baseline"]
    combined_df["Percent <54 Ratio"] = (
        combined_df["percent_lt_54_icgm"] / combined_df["percent_lt_54_baseline"]
    )

    combined_df["LBGI Percent Change"] = (
        (combined_df["LBGI_icgm"] - combined_df["LBGI_baseline"]) * 100
    ) / combined_df["LBGI_baseline"]
    combined_df["HBGI Percent Change"] = (
        (combined_df["HBGI_icgm"] - combined_df["HBGI_baseline"]) * 100
    ) / combined_df["HBGI_baseline"]
    combined_df["DKAI Percent Change"] = (
        (combined_df["DKAI_icgm"] - combined_df["DKAI_baseline"]) * 100
    ) / combined_df["DKAI_baseline"]
    combined_df["BGRI Percent Change"] = (
        (combined_df["BGRI_icgm"] - combined_df["BGRI_baseline"]) * 100
    ) / combined_df["BGRI_baseline"]
    combined_df["Percent <54 Percent Change"] = (
        (combined_df["percent_lt_54_icgm"] - combined_df["percent_lt_54_baseline"])
        * 100
    ) / combined_df["percent_lt_54_baseline"]

    combined_df["LBGI Difference"] = (
        combined_df["LBGI_icgm"] - combined_df["LBGI_baseline"]
    )
    combined_df["HBGI Difference"] = (
        combined_df["HBGI_icgm"] - combined_df["HBGI_baseline"]
    )
    combined_df["DKAI Difference"] = (
        combined_df["DKAI_icgm"] - combined_df["DKAI_baseline"]
    )
    combined_df["BGRI Difference"] = (
        combined_df["BGRI_icgm"] - combined_df["BGRI_baseline"]
    )
    combined_df["Percent <54 Difference"] = (
        combined_df["percent_lt_54_icgm"] - combined_df["percent_lt_54_baseline"]
    )

    combined_df.to_csv(
        path_or_buf=os.path.join(
            fig_path, "pairwise_comparison_combined_df_" + save_fig_folder_name +".csv"
        ),
        index=False,
    )

    run_pairwise_comparison_figures(save_fig_folder_name)

    return


def run_pairwise_comparison_figures(save_fig_folder_name):

    fig_path = os.path.join(
        "..",
        "..",
        "reports",
        "figures",
        "icgm-sensitivity-paired-comparison-figures",
        save_fig_folder_name,
    )
    combined_df = pd.read_csv(
        os.path.join(
            "..",
            "..",
            "reports",
            "figures",
            "icgm-sensitivity-paired-comparison-figures",
            save_fig_folder_name,
            "pairwise_comparison_combined_df_" + save_fig_folder_name + ".csv",
        )
    )

    # combined_df['sensor_num_icgm'] = combined_df['sensor_num_icgm'].apply(lambda x: int(x))
    # combined_df = combined_df.sort_values(by=['sensor_num_icgm'])

    # combined_df['sensor_num_icgm_string'] = combined_df['sensor_num_icgm'].apply(lambda x: "Sensor "+str(x))

    # Make Paired Comparison Box Plot
    # create_paired_comparison_box_plots(combined_df, fig_path=fig_path)

    # Make Paired Comparison Scatter Plot
    create_paired_comparison_scatter_plots(
        combined_df,
        fig_path=os.path.join(fig_path, "distributions-sensor-characteristic-outcome"),
    )

    # Generate crosstab of risk scores
    create_table_paired_risk_score_bins(
       combined_df, fig_path=os.path.join(fig_path, "risk-score-crosstabs")
    )

    create_sensor_characteristic_scatters(
        combined_df, fig_path=os.path.join(fig_path, "sensor_characteristic_distributions")
    )

    ########## Below are additional figures that could be run as needed ##########

    # Make Paired Comparison Histogram/KDE
    # create_paired_comparison_histogram_kde(
    #     combined_df,
    #     fig_path=os.path.join(fig_path, "histogram_kde_plots"),
    # )

    # combined_df["initial_bias_cutpoint_5"] = np.where(combined_df['initial_bias_icgm']>5, "Initial Bias > 5", "Initial Bias <= 5")
    # create_paired_comparison_scatter_plots(combined_df, fig_path=os.path.join(fig_path, "distributions-sensor-characteristic-outcome_by_inital_bias_cutpoint"),  color_value="initial_bias_cutpoint_5")

    # Generate graphs for all of the visualizations that do not match risk scores
    # create_visualization_simulations_changed_rs(combined_df)

    # Print counts that meet a number of different criteria
    # print_counts_simulations_different_criteria(combined_df)

    # Generate a table that shows each of the sensors and all of the characteristics
    # create_sensor_characteristics_table(combined_df, fig_path=fig_path)

    # Generate scatterplots showing distribution of outcome metrics by sensor
    # create_paired_comparison_by_sensor_scatter_plots(combined_df, fig_path)

    # Generate scatterplots showing distribution of outcome metrics by analysis level
    # create_paired_comparison_by_analysis_level_scatter_plots(combined_df,  fig_path=os.path.join(fig_path, "distributions-sensor-characteristic-analysis-level"), analysis_level="analysis_type_label")
    # create_paired_comparison_by_analysis_level_scatter_plots(combined_df,  fig_path=os.path.join(fig_path, "distributions-sensor-characteristic-analysis-level"), analysis_level="bg_test_condition_label")

    # Generate scatterplots showing distribution of outcome metrics across sensor characteristic space
    # create_paired_comparison_bivariate_sensor_characteristic_scatter(combined_df, fig_path=os.path.join(fig_path, "distributions-sensor-characteristc-bivariate-space"))

    return


def create_paired_comparison_histogram_kde(df, fig_path, color_value=""):
    if not os.path.exists(fig_path):
        print("making directory " + fig_path + "...")
        os.makedirs(fig_path)

    comparison_types = [" Difference"] #" Ratio", " Percent Change", " Difference"]

    outcome_metrics = ["LBGI"] #"DKAI", "HBGI", "Percent <54"]

    #Specify the cutoffs want to check
    threshold_dict = {"LBGI Difference" : [2]}

    for comparison_type, outcome_metric in itertools.product(
        comparison_types, outcome_metrics
    ):
        distribution_metric = outcome_metric + comparison_type
        for threshold in threshold_dict[distribution_metric]:
            #Add column so can look at distributions above and below threshold
            df["threshold_column"] = np.where(df[distribution_metric] > threshold, True, False)

            #Histogram with distribution above and below threshold

            #Another method
            # fig = px.histogram(df, x=distribution_metric, color="threshold_column", marginal="box")

            hist_data = [df[df["threshold_column"]==True][distribution_metric], df[df["threshold_column"]==False][distribution_metric]]
            group_labels = [distribution_metric + " > " + str(threshold), distribution_metric + " <= " + str(threshold)]
            fig = ff.create_distplot(hist_data, group_labels, bin_size=.05, histnorm = "probability")
            fig.show()
            #save fig - in the title, want to have distribution_metric, threshold in title

            # Histogram with distribution above threshold
            hist_data = [df[df["threshold_column"]==True][distribution_metric]]
            group_labels = [distribution_metric + " > " + str(threshold)]
            fig = ff.create_distplot(hist_data, group_labels, bin_size=.05, histnorm = "probability")
            fig.show()

            # Histogram with distribution below threshold
            hist_data = [df[df["threshold_column"]==False][distribution_metric]]
            group_labels = [distribution_metric + " <= " + str(threshold)]
            fig = ff.create_distplot(hist_data, group_labels, bin_size=.05, histnorm = "probability")
            fig.show()

            # KDEF with overall distribution but with a line for threshold
            hist_data = [df[distribution_metric]]
            group_labels = ["All Data"]
            fig = ff.create_distplot(hist_data, group_labels, bin_size=.05, histnorm = "probability")
            #Add in the line at the threshold
            fig.show()

            # CDF with distribution above and below threshold
            fig = go.Figure(data=[go.Histogram(x=df[distribution_metric], cumulative_enabled=True, histnorm='probability')])

            fig.add_trace(go.Scatter(x=[2,2], y=[0,1]))


            fig.show()
            #Add in the line at the threshold

    return

def print_counts_simulations_different_criteria(df):

    filenames = df.loc[
        (
            (df["true_bolus_icgm"] != df["true_bolus_baseline"])
            & (
                df["true_bolus_baseline"] == 0
            )  # ((combined_df["true_bolus_icgm"] == 0) | (combined_df["true_bolus_baseline"]==0))
            & (df["analysis_type"] == "meal_bolus")
        )
    ]

    print(filenames[0:10])
    print(len(filenames))

    # Check for the HBGI cases where high difference and the boluses are the same - should return zero
    filenames = df.loc[
        ((df["HBGI Difference"] > 20) | (df["HBGI Difference"] < -20))
        & (df["true_bolus_icgm"] == df["true_bolus_baseline"])
        & (df["analysis_type"] == "meal_bolus")
    ]

    print(filenames[0:10])
    print(len(filenames))

    return


def create_table_paired_risk_score_bins(df, fig_path):
    if not os.path.exists(fig_path):
        print("making directory " + fig_path + "...")
        os.makedirs(fig_path)

    for metric in ["DKAI", "LBGI"]:
        frequency_df = pd.crosstab(
            df[metric + " Risk Score String_baseline"],
            df[metric + " Risk Score String_icgm"],
        )  # .reset_index()

        # TODO: update this; not pythonic way to do
        percentage_df = frequency_df.loc[
            :, frequency_df.columns != metric + " Risk Score String_baseline"
        ].apply(lambda x: x / x.sum(), axis=1)
        for row in range(len(frequency_df)):
            for col in range(len(frequency_df.columns)):
                frequency_df.iloc[row, col] = (
                    str("{:,}".format(frequency_df.iloc[row, col]))
                    + " ("
                    + str("{:.1%}".format(percentage_df.iloc[row, col]))
                    + ")"
                )

        frequency_df = frequency_df.reset_index()

        frequency_df = frequency_df.rename(
            columns={
                metric
                + " Risk Score String_baseline": metric
                + " Risk Score<br>Rows: Baseline; Columns: iCGM"
            }
        )

        make_table(
            frequency_df,
            table_name=metric + "_paired_risk_score_cross_tab",
            analysis_name="icgm-sensitivity-analysis",
            cell_header_height=[60],
            cell_height=[30],
            cell_width=[250, 125, 125, 125, 125, 125, 125],
            image_type="png",
            view_fig=False,
            save_fig=True,
            save_fig_path=fig_path,
        )

        for bg_test_condition in df["bg_test_condition"].unique():
            reduced_df = df[df["bg_test_condition"] == bg_test_condition]
            frequency_df = pd.crosstab(
                reduced_df[metric + " Risk Score String_baseline"],
                reduced_df[metric + " Risk Score String_icgm"],
            )  # .reset_index()

            # TODO: update this; not pythonic way to do
            percentage_df = frequency_df.loc[
                :, frequency_df.columns != metric + " Risk Score String_baseline"
            ].apply(lambda x: x / x.sum(), axis=1)
            for row in range(len(frequency_df)):
                for col in range(len(frequency_df.columns)):
                    frequency_df.iloc[row, col] = (
                        str("{:,}".format(frequency_df.iloc[row, col]))
                        + " ("
                        + str("{:.1%}".format(percentage_df.iloc[row, col]))
                        + ")"
                    )

            frequency_df = frequency_df.reset_index()

            frequency_df = frequency_df.rename(
                columns={
                    metric
                    + " Risk Score String_baseline": metric
                    + " Risk Score: BG Test Condition "
                    + str(bg_test_condition)
                    + "<br>Rows: Baseline; Columns: iCGM"
                }
            )

            make_table(
                frequency_df,
                table_name=metric
                + "_paired_risk_score_cross_tab_bg_test_condition"
                + str(bg_test_condition),
                analysis_name="icgm-sensitivity-analysis",
                cell_header_height=[60],
                cell_height=[30],
                cell_width=[250, 125, 125, 125, 125, 125, 125],
                image_type="png",
                view_fig=False,
                save_fig=True,
                save_fig_path=fig_path,
            )

        for analysis_type in df["analysis_type_label_icgm"].unique():
            reduced_df = df[df["analysis_type_label_icgm"] == analysis_type]
            frequency_df = pd.crosstab(
                reduced_df[metric + " Risk Score String_baseline"],
                reduced_df[metric + " Risk Score String_icgm"],
            )  # .reset_index()

            # TODO: update this; not pythonic way to do
            percentage_df = frequency_df.loc[
                :, frequency_df.columns != metric + " Risk Score String_baseline"
            ].apply(lambda x: x / x.sum(), axis=1)
            for row in range(len(frequency_df)):
                for col in range(len(frequency_df.columns)):
                    frequency_df.iloc[row, col] = (
                        str("{:,}".format(frequency_df.iloc[row, col]))
                        + " ("
                        + str("{:.1%}".format(percentage_df.iloc[row, col]))
                        + ")"
                    )

            frequency_df = frequency_df.reset_index()

            frequency_df = frequency_df.rename(
                columns={
                    metric
                    + " Risk Score String_baseline": metric
                    + " Risk Score: "
                    + str(analysis_type)
                    + "<br>Rows: Baseline; Columns: iCGM"
                }
            )

            make_table(
                frequency_df,
                table_name=metric
                + "_paired_risk_score_cross_tab_"
                + str(analysis_type),
                analysis_name="icgm-sensitivity-analysis",
                cell_header_height=[60],
                cell_height=[30],
                cell_width=[250, 125, 125, 125, 125, 125, 125],
                image_type="png",
                view_fig=True,
                save_fig=True,
                save_fig_path=fig_path,
            )

    return

def create_sensor_characteristic_scatters(df, fig_path):
    if not os.path.exists(fig_path):
        print("making directory " + fig_path + "...")
        os.makedirs(fig_path)

    sensor_characteristics = [
        "noise_per_sensor",
        "initial_bias",
        "bias_factor",
        "phi_drift",
        "drift_multiplier_start",
        "drift_multiplier_end",
        "noise_max",
    ]

    sensor_characteristics_dict = {
        "noise_per_sensor": "Noise Per Sensor",
        "initial_bias": "Initial Bias",
        "bias_factor": "Bias Factor",
        "phi_drift": "Phi Drift",
        "drift_multiplier_start": "Drift Multiplier Start",
        "drift_multiplier_end": "Drift Multiplier End",
        "noise_max": "Noise Max",
    }

    # Create a plot for each of the sensor characteristics specified
    for i, sensor_characteristic_y in enumerate(sensor_characteristics):
        for j, sensor_characteristic_x in enumerate(sensor_characteristics):

            fig = px.scatter(df, x=sensor_characteristic_x + "_icgm", y=sensor_characteristic_y + "_icgm")
            fig.show()

            save_view_fig(
                fig,
                image_type="png",
                figure_name=sensor_characteristic_x + "_" + sensor_characteristic_y + "_sensor_characteristic_distributions",
                analysis_name="icgm-sensitivity-analysis",
                view_fig=False,
                save_fig=True,
                save_fig_path=fig_path
            )

    return

def create_paired_comparison_bivariate_sensor_characteristic_scatter(df, fig_path):
    if not os.path.exists(fig_path):
        print("making directory " + fig_path + "...")
        os.makedirs(fig_path)

    sensor_characteristics = [
        "initial_bias",
        "bias_drift_oscillations",
        "bias_drift_range_start",
        "bias_drift_range_end",
        "noise_coefficient",
        "delay",
        "bias_drift_type",
        "bias_type",
        "noise_per_sensor",
        "noise",
        "bias_factor",
        "phi_drift",
        "drift_multiplier",
        "drift_multiplier_start",
        "drift_multiplier_end",
        "noise_max",
    ]

    outcome_metrics = ["LBGI", "HBGI", "DKAI"]

    comparison_types = [" Difference", " Ratio"]

    for (
        comparison_type,
        outcome_metric,
        sensor_characteristic_x,
        sensor_characteristic_y,
    ) in itertools.product(
        comparison_types, outcome_metrics, sensor_characteristics, ["initial_bias"]
    ):
        if sensor_characteristic_x != sensor_characteristic_y:
            df_reduced = df.replace([np.inf, -np.inf], np.nan).dropna(
                subset=[outcome_metric + comparison_type], how="all"
            )
            print(df_reduced[outcome_metric + comparison_type].unique())
            create_scatter(
                df=df_reduced,
                x_value=sensor_characteristic_x + "_icgm",
                y_value=sensor_characteristic_y + "_icgm",
                color_value=outcome_metric + comparison_type,
                title=outcome_metric
                + comparison_type
                + " Baseline vs. iCGM Sensors<br>"
                + sensor_characteristic_x
                + " by "
                + sensor_characteristic_y,
                fig_name="distribution_"
                + outcome_metric
                + comparison_type
                + "_"
                + sensor_characteristic_x
                + "_by_"
                + sensor_characteristic_y,
                save_fig_path=fig_path,
            )

    # Create a plot for each of the sensor characteristics specified
    for comparison_type in []:  # comparison_types:
        for outcome_metric in []:  # outcome_metrics:
            n_cols = len(sensor_characteristics)
            n_rows = len(sensor_characteristics)
            subplot_titles = []

            sensor_characteristics_dict = {
                "sensor_num": "iCGM Sensor Number",
                "initial_bias": "Initial Bias",
                "bias_factor": "Bias Factor",
                "bias_drift_oscillations": "Bias Factor Oscillations",
                "bias_drift_range_start": "Bias Drift Range Start",
                "bias_drift_range_end": "Bias Drift Range End",
                "noise_coefficient": "Noise Coefficient",
            }

            for sensor_characteristics_y in sensor_characteristics:
                for sensor_characteristics_x in sensor_characteristics:
                    subplot_titles.append(
                        sensor_characteristics_dict[sensor_characteristics_y]
                        + " By "
                        + sensor_characteristics_dict[sensor_characteristics_x]
                    )

            fig = make_subplots(
                rows=n_rows,
                cols=n_cols,
                subplot_titles=subplot_titles,
                horizontal_spacing=0.1,
            )

            for i, sensor_characteristic_y in enumerate(sensor_characteristics):
                for j, sensor_characteristic_x in enumerate(sensor_characteristics):

                    fig.add_trace(
                        go.Scatter(
                            x=df[sensor_characteristic_x + "_icgm"],
                            y=df[sensor_characteristic_y + "_icgm"],
                            # color=df[sensor_characteristic_y+"_icgm"],
                            mode="markers",
                            marker=dict(
                                size=3,
                                opacity=0.4,
                                color=df[outcome_metric + comparison_type],
                            ),
                            showlegend=False,
                        ),
                        row=i + 1,
                        col=j + 1,
                    )

                    fig.update_xaxes(
                        title_text=sensor_characteristics_dict[sensor_characteristic_x],
                        row=i + 1,
                        col=j + 1,
                    )
                    fig.update_yaxes(
                        title_text=sensor_characteristics_dict[sensor_characteristic_y],
                        row=i + 1,
                        col=j + 1,
                    )

            fig.update_layout(
                title=outcome_metric
                + comparison_type
                + "<br>Baseline vs. iCGM Sensors Across Sensor Characteristic Space",
                legend_title=outcome_metric + comparison_type,
                showlegend=True,
                font_size=5,
            )

            for i in fig["layout"]["annotations"]:
                i["font"] = dict(size=7)

            save_view_fig(
                fig,
                image_type="png",
                figure_name="distribution_"
                + outcome_metric
                + comparison_type
                + "_across_sensor_characteristic_space",
                analysis_name="icgm-sensitivity-analysis",
                view_fig=True,
                save_fig=True,
                save_fig_path=fig_path,
                width=200 * n_cols,
                height=200 * n_rows,
            )

    return


def create_paired_comparison_scatter_plots(combined_df, fig_path, color_value=""):
    if not os.path.exists(fig_path):
        print("making directory " + fig_path + "...")
        os.makedirs(fig_path)

    comparison_types = [" Ratio", " Percent Change", " Difference"]

    outcome_metrics = ["LBGI", "DKAI", "HBGI"]  # "Percent <54"]

    sensor_characteristics = [
        "mard_icgm",
        "mbe_icgm",
        "initial_bias_icgm",
        "bias_norm_factor_icgm",
        "bias_drift_oscillations_icgm",
        "bias_drift_range_start_icgm",
        "bias_drift_range_end_icgm",
        "noise_coefficient_icgm",
        "delay_icgm",
        "bias_drift_type_icgm",
        "bias_type_icgm",
        "noise_per_sensor_icgm",
        "noise_icgm",
        "bias_factor_icgm",
        "phi_drift_icgm",
        "drift_multiplier_icgm",
        "drift_multiplier_start_icgm",
        "drift_multiplier_end_icgm",
        "noise_max_icgm",
    ]

    for comparison_type, outcome_metric, sensor_characteristic in itertools.product(
        comparison_types, outcome_metrics, sensor_characteristics
    ):
        create_scatter(
            df=combined_df,
            x_value=sensor_characteristic,
            y_value=outcome_metric + comparison_type,
            color_value=color_value,
            title="Distribution of "
            + outcome_metric
            + comparison_type
            + "<br>By "
            + sensor_characteristic,
            fig_name="distribution_"
            + outcome_metric
            + "_"
            + comparison_type
            + "_by_"
            + sensor_characteristic,
            save_fig_path=fig_path,
        )

    return


def create_paired_comparison_box_plots(combined_df, fig_path):
    if not os.path.exists(fig_path):
        print("making directory " + fig_path + "...")
        os.makedirs(fig_path)

    graph_metrics = [
        "LBGI Ratio",
        "HBGI Ratio",
        "DKAI Ratio",
        "BGRI Ratio",
        "Percent <54 Ratio",
        "LBGI Percent Change",
        "HBGI Percent Change",
        "DKAI Percent Change",
        "BGRI Percent Change",
        "Percent <54 Percent Change",
        "LBGI Difference",
        "HBGI Difference",
        "DKAI Difference",
        "BGRI Difference",
        "Percent <54 Difference",
    ]

    for metric in [graph_metrics]:

        fig = px.box(
            combined_df,
            x="sensor_num_icgm_string",
            y=metric,
            color="sensor_num_icgm_string",
            labels={"sensor_num_icgm_string": "Sensor Number"},
            title=metric + " (Between Baseline and iCGM Simulations)",
            points=False,
        )

        fig.update_xaxes(tick0=0, dtick=1)
        fig.update_layout(showlegend=False)

        save_view_fig(
            fig,
            image_type="png",
            figure_name=metric + "_pairwise_comparison_boxplot",
            analysis_name="icgm-sensitivity-analysis",
            view_fig=True,
            save_fig=True,
            save_fig_path=fig_path,
        )

    return


def create_paired_comparison_by_analysis_level_scatter_plots(
    combined_df, fig_path, analysis_level="analysis_type_label"
):
    if not os.path.exists(fig_path):
        print("making directory " + fig_path + "...")
        os.makedirs(fig_path)

    sensor_characteristics = [
        "initial_bias"
    ]  # "bias_factor", "bias_drift_oscillations", "bias_drift_range_start", "bias_drift_range_end","noise_coefficient"]

    outcome_metrics = ["LBGI", "HBGI", "DKAI"]

    comparison_types = [" Ratio"]  # [" Difference",

    combined_df = combined_df.sort_values(by=["bg_test_condition_label_icgm"])

    analysis_level_unique_values = combined_df[analysis_level + "_icgm"].unique()

    # Create a plot for each of the sensor characteristics specified
    for comparison_type in comparison_types:
        for sensor_characteristic in sensor_characteristics:
            n_cols = len(outcome_metrics)
            n_rows = len(analysis_level_unique_values)
            subplot_titles = []

            for analysis_level_value in analysis_level_unique_values:
                for metric in outcome_metrics:
                    if analysis_level == "bg_test_condition":
                        subplot_titles.append(
                            "BG Test Condition "
                            + str(analysis_level_value)
                            + ", "
                            + metric
                            + comparison_type
                        )
                    else:
                        subplot_titles.append(
                            str(analysis_level_value) + ", " + metric + comparison_type
                        )

            fig = make_subplots(
                rows=n_rows,
                cols=n_cols,
                subplot_titles=subplot_titles,
                horizontal_spacing=0.1,
            )

            for i, analysis_level_value in enumerate(analysis_level_unique_values):
                for j, metric in enumerate(outcome_metrics):

                    df = combined_df[
                        combined_df[analysis_level + "_icgm"] == analysis_level_value
                    ]
                    print(
                        df[[sensor_characteristic + "_icgm", metric + comparison_type]]
                    )

                    fig.add_trace(
                        go.Scatter(
                            x=df[sensor_characteristic + "_icgm"],
                            y=df[metric + comparison_type],
                            customdata=df["filename_icgm"],
                            mode="markers",
                            marker=dict(size=4, opacity=0.6),
                            showlegend=False,
                        ),
                        row=i + 1,
                        col=j + 1,
                    )

            y_columns = [metric + comparison_type for metric in outcome_metrics]
            y_max_value = max(combined_df[y_columns])
            x_max_value = max(combined_df[sensor_characteristic + "_icgm"])
            x_min_value = min(combined_df[sensor_characteristic + "_icgm"])

            analysis_level_dict = {
                "bg_test_condition_label": "BG Test Condition",
                "analysis_type_label": "Analysis Type",
            }

            fig.update_layout(
                title="Outcome Metric "
                + comparison_type
                + ": Baseline vs. iCGM Sensors<br>By "
                + analysis_level_dict[analysis_level],
                legend_title="Risk Scores",
                showlegend=True,
                font_size=6,
            )

            sensor_characteristics_dict = {
                "sensor_num": "iCGM Sensor Number",
                "initial_bias": "Initial Bias",
                "bias_factor": "Bias Factor",
                "bias_drift_oscillations": "Bias Factor Oscillations",
                "bias_drift_range_start": "Bias Drift Range Start",
                "bias_drift_range_end": "Bias Drift Range End",
                "noise_coefficient": "Noise Coefficient",
            }

            fig.update_yaxes(range=[0, 200])

            fig.update_xaxes(
                title=sensor_characteristics_dict[sensor_characteristic],
                range=[x_min_value, x_max_value],
            )

            for i in fig["layout"]["annotations"]:
                i["font"] = dict(size=7)

            save_view_fig(
                fig,
                image_type="png",
                figure_name="distribution_"
                + comparison_type
                + "_"
                + analysis_level
                + "_sensor_characteristic"
                + "_pairwise_comparison_scatter",
                analysis_name="icgm-sensitivity-analysis",
                view_fig=False,
                save_fig=True,
                save_fig_path=fig_path,
                width=200 * n_cols,
                height=200 * n_rows,
            )

    return


def create_paired_comparison_by_sensor_scatter_plots(combined_df, fig_path):
    if not os.path.exists(fig_path):
        print("making directory " + fig_path + "...")
        os.makedirs(fig_path)

    graph_metrics = ["LBGI", "DKAI", "HBGI", "BGRI"]
    n_rows = 5
    n_cols = 6
    subplot_titles = []

    for i in range(n_rows):
        for j in range(n_cols):
            sensor_num = i * n_cols + j
            subplot_titles.append("Sensor " + str(sensor_num))

    for metric in graph_metrics:
        fig = make_subplots(
            rows=n_rows,
            cols=n_cols,
            subplot_titles=subplot_titles,
            horizontal_spacing=0.05,
        )
        max_value = (
            max(
                max(combined_df[metric + "_baseline"]),
                max(combined_df[metric + "_icgm"]),
            )
            + 2
        )

        fill_color_dict = {
            "0 - None": "rgba(15, 115, 198, 0.2)",
            "1 - Negligible": "rgba(6, 180, 6, 0.2)",
            "2 - Minor": "rgba(208, 192, 127, 0.2)",
            "3 - Serious": "rgba(225, 131, 37, 0.2)",
            "4 - Critical": "rgba(154, 58, 57, 0.2)",
        }

        for i in range(n_rows):
            for j in range(n_cols):

                # Add in risk score lines for LBGI and HBGI
                if metric in ["LBGI", "DKAI"]:

                    if (i == 0) & (j == 0):
                        show_legend = True
                    else:
                        show_legend = False

                    if metric == "LBGI":
                        thresholds = [0, 2.5, 2.5, 5, max_value]

                    elif metric == "DKAI":
                        thresholds = [2, 6, 8, 5, max_value]

                    risk_levels = [
                        "0 - None",
                        "1 - Negligible",
                        "2 - Minor",
                        "3 - Serious",
                        "4 - Critical",
                    ]

                    for risk_level, threshold in zip(risk_levels, thresholds):
                        fig.add_trace(
                            go.Scatter(
                                x=[0, max_value],
                                y=[threshold, threshold],
                                hoverinfo="skip",
                                name=risk_level,
                                mode="lines",
                                fillcolor=fill_color_dict[risk_level],
                                line=dict(width=0.5, color=fill_color_dict[risk_level]),
                                showlegend=show_legend,
                                stackgroup="one",
                            ),
                            row=i + 1,
                            col=j + 1,
                        )

                # Filter the dataset for the particular sensor
                sensor_num = i * n_cols + j
                df = combined_df[combined_df["sensor_num_icgm"] == sensor_num]
                df["hovertext"] = df["filename_icgm"] + "<br>Baseline: " + df[
                    metric + "_baseline"
                ].astype(str) + "<br>iCGM: " + df[metric + "_icgm"].astype(
                    str
                ) + "<br>iCGM Sensor Characteristics: " "<br>Initial Bias: " + df[
                    "initial_bias_icgm"
                ].astype(
                    str
                ) + "<br>Bias Factor: " + df[
                    "bias_factor_icgm"
                ].astype(
                    str
                ) + "<br>Bias Drift Oscillations: " + df[
                    "bias_drift_oscillations_icgm"
                ].astype(
                    str
                ) + "<br>Bias Drift Range Start: " + df[
                    "bias_drift_range_start_icgm"
                ].astype(
                    str
                ) + "<br>Bias Drift Range End: " + df[
                    "bias_drift_range_end_icgm"
                ].astype(
                    str
                ) + "<br>Noise Coefficient: " + df[
                    "noise_coefficient_icgm"
                ].astype(
                    str
                )

                if metric in ["LBGI", "DKAI"]:
                    marker_dict = dict(color="gray", size=5, opacity=0.6)
                else:
                    marker_dict = dict(size=5, opacity=0.6, color="gray")

                fig.add_trace(
                    go.Scatter(
                        name="Sensor " + str(sensor_num),
                        x=df[metric + "_baseline"],
                        y=df[metric + "_icgm"],
                        customdata=df["filename_icgm"],
                        hovertext=df["hovertext"],
                        mode="markers",
                        showlegend=False,
                        marker=marker_dict,
                    ),
                    row=i + 1,
                    col=j + 1,
                )

                fig.add_trace(
                    go.Scatter(
                        x=[0, max_value],
                        y=[0, max_value],
                        mode="lines",
                        showlegend=False,
                        opacity=0.4,
                        line=dict(width=1, color="black"),
                    ),
                    row=i + 1,
                    col=j + 1,
                )

        fig.update_layout(
            title=metric + ": Baseline vs. iCGM Sensors",
            legend_title="Risk Scores",
            showlegend=True,
            font_size=8,
        )

        fig.update_yaxes(title="iCGM", range=[0, max_value])

        fig.update_xaxes(title="Baseline", range=[0, max_value])

        for i in fig["layout"]["annotations"]:
            i["font"] = dict(size=10)

        save_view_fig(
            fig,
            image_type="png",
            figure_name=metric + "_pairwise_comparison_scatter",
            analysis_name="icgm-sensitivity-analysis",
            view_fig=False,
            save_fig=True,
            save_fig_path=fig_path,
            width=200 * n_cols,
            height=200 * n_rows,
        )

    return


def visualize_individual_sim_result(df, icgm_path, baseline_path, save_fig_path, save_fig_folder_name, animation_filenames = []):
    # animation_filenames = df.loc[
    #     ((df["HBGI Difference"] > 20) | (df["HBGI Difference"] < -20)), "filename_icgm"
    # ]
    # df.loc[((df['DKAI Difference'] > 5) | (df['LBGI Difference'] > 5)), 'filename_icgm']

    # For testing
    # animation_filenames = ["vp12.bg9.s1.correction_bolus.csv"]
    # print(len(animation_filenames))

    for i, filename in enumerate(animation_filenames[0:10]):

        print(i, filename)

        baseline_filename = df.loc[
            df["filename_icgm"] == filename, "filename_baseline"
        ].iloc[0]

        icgm_DKAI_RS = df.loc[
            df["filename_icgm"] == filename, "DKAI Risk Score_icgm"
        ].iloc[0]
        icgm_LBGI_RS = df.loc[
            df["filename_icgm"] == filename, "LBGI Risk Score_icgm"
        ].iloc[0]

        baseline_DKAI_RS = df.loc[
            df["filename_icgm"] == filename, "DKAI Risk Score_baseline"
        ].iloc[0]
        baseline_LBGI_RS = df.loc[
            df["filename_icgm"] == filename, "LBGI Risk Score_baseline"
        ].iloc[0]

        mard_icgm = df.loc[
            df["filename_icgm"] == filename, "mard_icgm"
        ].iloc[0]

        initial_bias_icgm = df.loc[
            df["filename_icgm"] == filename, "initial_bias_icgm"
        ].iloc[0]

        icgm_simulation_df = data_loading_and_preparation(
            os.path.join(icgm_path, filename)
        )

        baseline_simulation_df = data_loading_and_preparation(
            os.path.join(baseline_path, baseline_filename)
        )

        # List of dictionaries
        traces = [
            {0: ["bg", "bg_sensor"], 1: ["sbr", "temp_basal_sbr_if_nan"]},
            {2: ["bg", "bg_sensor"], 3: ["sbr", "temp_basal_sbr_if_nan"]},
        ]

        print(baseline_simulation_df.columns)
        print(icgm_simulation_df.columns)

        max_basal = (
            max(
                np.nanmax(baseline_simulation_df["sbr"]),
                np.nanmax(icgm_simulation_df["sbr"]),
                np.nanmax(baseline_simulation_df["temp_basal"]),
                np.nanmax(icgm_simulation_df["temp_basal"]),
            )
            + 0.5
        )
        max_bg = (
            max(
                np.nanmax(baseline_simulation_df["bg"]),
                np.nanmax(icgm_simulation_df["bg"]),
                np.nanmax(baseline_simulation_df["bg_sensor"]),
                np.nanmax(icgm_simulation_df["bg_sensor"]),
            )
            + 20
        )
        min_bg = (
            min(
                np.nanmin(baseline_simulation_df["bg"]),
                np.nanmin(icgm_simulation_df["bg"]),
                np.nanmin(baseline_simulation_df["bg_sensor"]),
                np.nanmin(icgm_simulation_df["bg_sensor"]),
            )
            - 10
        )


        create_simulation_figure_plotly(
            files_need_loaded=False,
            data_frames=[icgm_simulation_df, baseline_simulation_df],
            file_location=os.path.join("..", "..", "data", "processed"),
            file_names=[filename, baseline_filename],
            traces=traces,
            show_legend=False,
            subplots=4,
            time_range=(0, 8),
            subtitle="",
            main_title="iCGM: DKAI RS "
             + str(icgm_DKAI_RS)
             + ", LBGI RS "
             + str(icgm_LBGI_RS)
            + ",  MARD: "
            + str(int(mard_icgm))
           + ",  Initial Bias: "
           + str(int(initial_bias_icgm))
            + " ; Baseline: DKAI RS "
            + str(int(baseline_DKAI_RS))
            + ", LBGI RS "
            + str(int(baseline_LBGI_RS))
            + "<br>"
            + filename,
            subplot_titles=[
                "BG Values (iCGM)",
                "Scheduled Basal Rate and Loop Decisions (iCGM)",
                "BG Values (Baseline)",
                "Scheduled Basal Rate and Loop Decisions (Baseline)",
            ],
            save_fig_path=os.path.join(
                save_fig_path,
                "example_simulations",
                save_fig_folder_name,
            ),
            figure_name= filename,
            analysis_name="icgm_sensitivity_analysis",
            animate=False,
            custom_axes_ranges=[
                (min(50, min_bg), max(260, max_bg)),
                (0, max_basal),
                (min(50, min_bg), max(260, max_bg)),
                (0, max_basal),
            ],
            custom_tick_marks=[
                [54, 70, 140, 180, 250, 300, 350, 400],
                np.arange(0, max_basal, 0.5),
                [54, 70, 140, 180, 250],
                +np.arange(0, max_basal, 0.5),
            ],
        )

    return


def create_sensor_characteristics_table(df, fig_path):
    columns = [
        "sensor_num_icgm",
        "initial_bias_icgm",
        "bias_factor_icgm",
        "bias_drift_oscillations_icgm",
        "bias_drift_range_start_icgm",
        "bias_drift_range_end_icgm",
        "noise_coefficient_icgm",
    ]
    sensor_characteristics_df = df[columns].drop_duplicates()

    sensor_characteristics_df = sensor_characteristics_df.sort_values(
        by=["sensor_num_icgm"]
    )

    sensor_characteristics_df = sensor_characteristics_df.rename(
        columns={
            "sensor_num_icgm": "iCGM Sensor Number",
            "initial_bias_icgm": "Initial Bias",
            "bias_factor_icgm": "Bias Factor",
            "bias_drift_oscillations_icgm": "Bias Factor Oscillations",
            "bias_drift_range_start_icgm": "Bias Drift Range Start",
            "bias_drift_range_end_icgm": "Bias Drift Range End",
            "noise_coefficient_icgm": "Noise Coefficient",
        }
    )

    print(sensor_characteristics_df)

    return

def generate_all_results_figures(
    df, fig_path=os.path.join("..", "..", "reports", "figures")
):
    # Create Spearman Correlation Coefficient Table
    spearman_correlation_table(df, save_fig_path=fig_path)

    # Iterate through each metric and analysis_level category shown below and create boxplot
    # figure with both log scale and linear scale.
    metrics = ["LBGI", "DKAI"]
    analysis_levels = ["bg_test_condition", "analysis_type", "all"]
    y_axis_scales = ["log"]  # , "linear"]

    for analysis_level, metric, axis_scale in itertools.product(
        analysis_levels, metrics, y_axis_scales
    ):
        make_boxplot(
            df,
            figure_name="boxplot-" + analysis_level + "-" + metric,
            analysis_name="icgm-sensitivity-analysis",
            metric=metric,
            level_of_analysis=analysis_level,
            notched_boxplot=False,
            y_scale_type=axis_scale,
            image_type="png",
            view_fig=False,
            save_fig=True,
            save_fig_path=fig_path,
        )

        """
        make_histogram(
            df,
            figure_name="histogram-" + analysis_level + "-" + metric,
            analysis_name="icgm-sensitivity-analysis",
            metric=metric,
            level_of_analysis=analysis_level,
            image_type="png",
            view_fig=False,
            save_fig=True,
            save_fig_path=fig_path
        )

        """
        make_distribution_table(
            df,
            table_name="distribution-table-" + analysis_level + "-" + metric,
            analysis_name="icgm-sensitivity-analysis",
            metric=metric,
            level_of_analysis=analysis_level,
            image_type="png",
            view_fig=False,
            save_fig=True,
            save_fig_path=fig_path,
        )

    metrics = ["LBGI Risk Score", "DKAI Risk Score"]
    analysis_levels = ["bg_test_condition", "analysis_type", "all"]

    for analysis_level, metric in itertools.product(analysis_levels, metrics):
        make_bubble_plot(
            df,
            image_type="png",
            figure_name="bubbleplot-" + analysis_level + "-" + metric,
            analysis_name="icgm-sensitivity-analysis",
            metric=metric,
            level_of_analysis=analysis_level,
            view_fig=False,
            save_fig=True,
            save_fig_path=fig_path,
        )

    ########### SUMMARY TABLE #################

    all_analyses_summary_df = prepare_results_for_summary_table(df)

    # make table
    make_table(
        all_analyses_summary_df.reset_index(),
        table_name="summary-risk-table",
        analysis_name="icgm-sensitivity-analysis",
        cell_header_height=[60],
        cell_height=[30],
        cell_width=[200, 150, 150, 150],
        image_type="png",
        view_fig=False,
        save_fig=True,
        save_fig_path=fig_path,
    )

    ########### DEMOGRAPHICS TABLE #################

    get_metadata_tables(df, fig_path=fig_path)

    ########## CDF Plots #################

    metrics = ["LBGI", "DKAI", "LBGI Risk Score", "DKAI Risk Score"]

    for metric in metrics:
        create_cdf(
            data=df[metric],
            title="CDF for " + metric,
            image_type="png",
            figure_name="cdf-" + metric,
            analysis_name="icgm-sensitivity-analysis",
            view_fig=False,
            save_fig=True,
            save_fig_path=fig_path,
        )

    ########## Proportion/Frequency Tables #################

    metrics = ["LBGI Risk Score", "DKAI Risk Score"]
    analysis_levels = ["bg_test_condition", "analysis_type", "all"]

    for analysis_level, metric in itertools.product(analysis_levels, metrics):
        make_frequency_table(
            df,
            image_type="png",
            table_name="frequency-table-" + metric + "-" + analysis_level,
            analysis_name="icgm-sensitivity-analysis",
            cell_header_height=[30],
            cell_height=[30],
            cell_width=[250, 130, 135, 120, 120, 120],
            metric=metric,
            level_of_analysis=analysis_level,
            view_fig=False,
            save_fig=True,
            save_csv=True,
            save_fig_path=fig_path,
        )
        return


def settings_outside_clinical_bounds(cir, isf, sbr):

    return ((float(isf) < 10) | (float(isf) > 500) | (float(cir) < 2) | (float(cir) > 150) | (float(sbr) < 0.05) | (
                float(sbr) > 30))


def create_data_frame_for_figures(
    results_path,
    save_path,
    results_folder_name,
    old_format=False,
    patient_characteristics_path=os.path.join(
        "..",
        "..",
        "data",
        "processed",
        "icgm-sensitivity-analysis-results-2020-09-19-nogit",
    ),
    is_baseline = False
):
    # scenarios_outside_clinical_bounds_df = pd.read_csv(
    #     os.path.join(
    #         "..", "..", "data", "processed", "scenarios_outside_clinical_bounds.csv"
    #     )
    # )
    # vp_outside_clinical_bounds = list(
    #     scenarios_outside_clinical_bounds_df[
    #         "scenarios_with_settings_outside_clinical_bounds"
    #     ].apply(lambda x: x.split("_")[1].split(".")[0])
    # )
    #
    # print("vp id outside clinical bounds: " + str(vp_outside_clinical_bounds))

    if old_format:
        for i, filename in enumerate(sorted(os.listdir(results_path))): #[0:100]):
            if filename.endswith(".csv"):
                print(i, filename)

                simulation_df = pd.read_csv(os.path.join(results_path, filename))
                filename_components = filename.split(".")

                f = open(
                    os.path.join(
                        patient_characteristics_path, (filename_components[0] + ".json")
                    ),
                    "r",
                )
                json_data = json.loads(f.read())
                patient_characteristics_df = pd.DataFrame(json_data, index=["i",])

                vp_id = (
                    patient_characteristics_df["patient_scenario_filename"]
                    .iloc[0]
                    .split("/")[-1]
                    .split(".")[0]
                    .replace("train_", "")
                )

                if filename_components[2] == "sIdealSensor":
                    f = open(
                        os.path.join(results_path, "sIdealSensor.json"), "r"
                    )  # Add this file with the correct parameters
                    json_data = json.loads(f.read())
                else:
                    f = open(
                        os.path.join(
                            results_path,
                            (
                                filename_components[0]
                                + "."
                                + filename_components[1]
                                + "."
                                + filename_components[2]
                                + ".json"
                            ),
                        ),
                        "r",
                    )
                    json_data = json.loads(f.read())

                sensor_characteristics_df = pd.DataFrame(json_data, index=["i",])

                # Add in the data, filtering out the virtual patients outside of clinical bounds
                #if vp_id not in vp_outside_clinical_bounds:
                if filename_components[2] == "sIdealSensor":
                    data.append(
                        get_data_old_format(
                            filename,
                            simulation_df,
                            patient_characteristics_df
                        )
                    )
                else:
                    data.append(
                        get_data_old_format(
                            filename,
                            simulation_df,
                            patient_characteristics_df,
                            sensor_characteristics_df,
                        )
                    )

    else:
        removed_scenarios = []

        for i, filename in enumerate(sorted(os.listdir(results_path))): #[0:100])):
            if filename.endswith(".tsv"):

                print(i, filename)
                simulation_df = pd.read_csv(
                    os.path.join(results_path, filename), sep="\t"
                )

                #Check that the first two bg values are equal
                assert (simulation_df.loc[0]["bg"] == simulation_df.loc[1][
                    "bg"]), "First two BG values of simulation are not equal"

                f = open(
                    os.path.join(results_path, filename.replace(".tsv", ".json")), "r"
                )
                simulation_characteristics_json_data = json.loads(f.read())

                vp_id = filename.split(".")[0].replace("vp", "")

                cir = simulation_characteristics_json_data["patient"]["config"]["carb_ratio_schedule"]["schedule"][0]["setting"].replace(" g", "")
                isf = simulation_characteristics_json_data["patient"]["config"]["insulin_sensitivity_schedule"]["schedule"][0]["setting"].replace(
                    " m", "")
                sbr = simulation_characteristics_json_data["patient"]["config"]["basal_schedule"]["schedule"][0]["setting"].replace(" U", "")

                # Add in the data
                #if vp_id not in vp_outside_clinical_bounds:
                if settings_outside_clinical_bounds(cir, isf, sbr):
                    print(filename + " has settings outside clinical bounds.")
                    removed_scenarios.append([filename, cir, isf, sbr])

                else:
                    data.append(
                        get_data(
                            filename,
                            simulation_df,
                            simulation_characteristics_json_data,
                            baseline=is_baseline,
                        )
                    )

        removed_scenarios_df = pd.DataFrame(removed_scenarios, columns=["filename", "cir", "isf", "sbr"])
        removed_scenarios_df.to_csv(
            path_or_buf=os.path.join(save_path, results_folder_name + "_removed_scenarios_df.csv"),
            index=False,
        )

    columns = [
        "filename",
        "sim_id",
        "virtual_patient_num",
        "sensor_num",
        "patient_scenario_filename",
        "age",
        "ylw",
        "CIR",
        "ISF",
        "SBR",
        "starting_bg",
        "starting_bg_sensor",
        "true_bolus",
        "initial_bias",
        "bias_norm_factor",
        "bias_drift_oscillations",
        "bias_drift_range_start",
        "bias_drift_range_end",
        "noise_coefficient",
        "delay",
        "bias_drift_type",
        "bias_type",
        "noise_per_sensor",
        "noise",
        "bias_factor",
        "phi_drift",
        "drift_multiplier",
        "drift_multiplier_start",
        "drift_multiplier_end",
        "noise_max",
        "mard",
        "mbe",
        "bg_test_condition",
        "analysis_type",
        "LBGI",
        "LBGI Risk Score",
        "DKAI",
        "DKAI Risk Score",
        "HBGI",
        "BGRI",
        "percent_lt_54",
    ]

    results_df = pd.DataFrame(data, columns=columns)

    # Exclude scenarios that were found to not meet the special controls (leaving this code in case end up needing again)
    # special_controls_pass_rate_df = pd.read_csv(os.path.join("..", "..", "data", "processed", "icgm-sensitivity-analysis-scenarios-2020-07-10-nogit", "percent_pass_per_scenario_icgm-sensitivity-analysis-scenarios-2020-07-10-nogit.csv"))
    # scenarios_meeting_special_controls = special_controls_pass_rate_df[special_controls_pass_rate_df["percent_pass"] == 100]["training_scenario_filename"].unique()

    # print(results_df.shape)
    # print(scenarios_meeting_special_controls)
    # print(len(scenarios_meeting_special_controls))
    # print(all_results_df["patient_scenario_filename"][0:10])

    # results_df = all_results_df[all_results_df["patient_scenario_filename"].isin(scenarios_meeting_special_controls)]

    # print(results_df.shape)

    results_df = clean_up_results_df(results_df)

    results_df.to_csv(
        path_or_buf=os.path.join(save_path, results_folder_name + "_results_df.csv"),
        index=False,
    )

    return results_df

def clean_up_results_df(results_df):

    results_df[["age", "ylw"]] = results_df[["age", "ylw"]].apply(pd.to_numeric)

    # rename the analysis types
    results_df.replace({"tempBasal": "Temp Basal Analysis"}, inplace=True)
    results_df.replace({"correctionBolus": "Correction Bolus Analysis"}, inplace=True)

    results_df["analysis_type_label"] = results_df["analysis_type"].replace(
        analysis_type_labels
    )
    results_df["bg_test_condition_label"] = results_df["bg_test_condition"].replace(
        analysis_type_labels
    )
    results_df["DKAI Risk Score String"] = results_df["DKAI Risk Score"].replace(
        score_dict
    )
    results_df["LBGI Risk Score String"] = results_df["LBGI Risk Score"].replace(
        score_dict
    )

    return results_df


########## DICTIONARIES ###################
score_dict = {
    0: "0 - None",
    1: "1 - Negligible",
    2: "2 - Minor",
    3: "3 - Serious",
    4: "4 - Critical",
}
color_dict = {
    "0 - None": "#0F73C6",
    "1 - Negligible": "#06B406",
    "2 - Minor": "#D0C07F",
    "3 - Serious": "#E18325",
    "4 - Critical": "#9A3A39",
}

analysis_type_labels = {
    "correction_bolus": "Correction Bolus",
    "meal_bolus": "Meal Bolus",
    "temp_basal_only": "Temp Basal Only",
}

level_of_analysis_dict = {
    "all": "All Analyses",
    "analysis_type": "Analysis Type",
    "bg_test_condition": "BG Test Condition",
}

#### LOAD IN DATA #####

# Load in the iCGM Data
data = []
icgm_folder_name = "icgm-sensitivity-analysis-results-2020-11-02-nogit"
results_files_path = os.path.join("..", "..", "data", "processed", icgm_folder_name)

# Set where to save figures
save_fig_folder_name = icgm_folder_name

results_save_fig_path = os.path.join(
    "..",
    "..",
    "reports",
    "figures",
    "icgm-sensitivity-paired-comparison-figures",
    save_fig_folder_name,
)

not_pairwise_save_fig_path = os.path.join(
    "..",
    "..",
    "reports",
    "figures",
    "icgm-sensitivity-analysis-results-figures",
    save_fig_folder_name,
)

if not os.path.exists(results_save_fig_path):
    print("making directory " + results_save_fig_path + "...")
    os.makedirs(results_save_fig_path)

# icgm_results_df = create_data_frame_for_figures(
#     results_path=results_files_path,
#     old_format=False,
#     save_path=results_save_fig_path,
#     results_folder_name=icgm_folder_name,
# )


# Load in the Ideal Sensor Data
data = []
ideal_sensor_folder_name = "icgm-sensitivity-analysis-results-2020-11-05-nogit"
baseline_files_path = os.path.join(
    "..", "..", "data", "processed", ideal_sensor_folder_name
)

# baseline_sensor_df = create_data_frame_for_figures(
#     is_baseline = True,
#     results_path=baseline_files_path,
#     old_format=False,
#     save_path=results_save_fig_path,
#     results_folder_name=ideal_sensor_folder_name,
# )

# If want to load in the ideal sensors again, otherwise use above
# baseline_sensor_df = pd.read_csv(os.path.join(save_path, ideal_sensor_folder_name + "_results_df.csv"))

#### CREATE FIGURES #####

# Create all check distribution figures
# generate_all_check_distribution_scatterplots(icgm_results_df, fig_path=save_fig_path)

# Create all results figures (not pairwise) from the baseline df
# generate_all_results_figures(baseline_sensor_df, fig_path=results_save_fig_path)



# Create all results figures (not pairwise) from the results data frame
icgm_results_df = pd.read_csv(os.path.join(results_save_fig_path, icgm_folder_name + "_results_df.csv"))
generate_all_results_figures(icgm_results_df, fig_path=results_save_fig_path)

# Create pairwise figures
#run_pairwise_comparison(results_df=icgm_results_df, baseline_df=baseline_sensor_df, save_fig_folder_name=save_fig_folder_name)
#run_pairwise_comparison_figures(save_fig_folder_name=save_fig_folder_name)

########### Run some visualizations of specific scenario examples ###########

def create_sim_examples():

    fig_path = os.path.join(
        "..",
        "..",
        "reports",
        "figures",
        "icgm-sensitivity-paired-comparison-figures",
        save_fig_folder_name,
        "risk_score_change_example_figures"
    )
    combined_df = pd.read_csv(
        os.path.join(
            "..",
            "..",
            "reports",
            "figures",
            "icgm-sensitivity-paired-comparison-figures",
            save_fig_folder_name,
            "pairwise_comparison_combined_df_" + save_fig_folder_name + ".csv",
        )
    )

    #1. Examples of high MARD (MARD >20)
    animation_filenames = combined_df.loc[
            (combined_df["mard_icgm"] > 40), "filename_icgm"
        ].tolist()[0:10]


    print("High MARD files:" + str(animation_filenames))
    print(len(animation_filenames))

    visualize_individual_sim_result(df = combined_df, icgm_path = results_files_path,
                                    baseline_path = baseline_files_path, save_fig_path = results_save_fig_path, save_fig_folder_name = "mard>40", animation_filenames = animation_filenames)


    #2. Examples of risk score bin changes > 2 buckets
    animation_filenames = combined_df.loc[
            (combined_df["LBGI Risk Score_icgm"] > combined_df["LBGI Risk Score_baseline"].apply(lambda x: x+1)), "filename_icgm"
        ].tolist()[0:10]

    print("LBGI jumps 2 risk bins files:" + str(animation_filenames))
    print(len(animation_filenames))

    visualize_individual_sim_result(df = combined_df, icgm_path = results_files_path,
                                    baseline_path = baseline_files_path, save_fig_path = results_save_fig_path, save_fig_folder_name = "LBGI_2_risk_bin_jumps", animation_filenames = animation_filenames)



    #3. Examples of really high LBGI

    animation_filenames = combined_df.loc[
            (combined_df["LBGI Difference"] > 8), "filename_icgm"
        ].tolist()[0:10]

    print("High LBGI files:" + str(animation_filenames))
    print(len(animation_filenames))

    visualize_individual_sim_result(df = combined_df, icgm_path = results_files_path,
                                    baseline_path = baseline_files_path, save_fig_path = results_save_fig_path
                                    , save_fig_folder_name = "LBGI_difference>8", animation_filenames = animation_filenames)


    #4. low bias high risk

    animation_filenames = combined_df.loc[
            ((combined_df["LBGI Difference"] > 6) & (combined_df["initial_bias_icgm"] < 5)), "filename_icgm"
        ].tolist()[0:10]


    visualize_individual_sim_result(df = combined_df, icgm_path = results_files_path,
                                    baseline_path = baseline_files_path, save_fig_path = results_save_fig_path
                                    , save_fig_folder_name = "low_bias_high_risk", animation_filenames = animation_filenames)



    #5. High MARD low risk

    animation_filenames = combined_df.loc[
        ((combined_df["LBGI Difference"] < 1) & (combined_df["mard_icgm"] > 30)), "filename_icgm"
        ].tolist()[0:10]

    visualize_individual_sim_result(df = combined_df, icgm_path = results_files_path,
                                    baseline_path = baseline_files_path, save_fig_path = results_save_fig_path
                                    , save_fig_folder_name = "high_mard_low_risk", animation_filenames = animation_filenames)




    #6. Any individual file want to look at
    # animation_filenames = []
    # visualize_individual_sim_result(df = combined_df, icgm_path = results_files_path,
    #                                 baseline_path = baseline_files_path, save_fig_path = results_save_fig_path
    #                                 , save_fig_folder_name = "other_misc_scenarios", animation_filenames = animation_filenames)


    return