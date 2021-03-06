# Figures for Data Science Risk Analyses

#### -- Project Status: Active
#### -- Project Disclaimer: This work is for Exploration
 ## Project Objective
The purpose of this project is to create figures, tables, and animation for exploratory 
analysis of Tidepool Data Science Team risk analyses results. 

## Definition of Done
This phase of the project will be done when exploratory analysis for these projects is completed and final figures are 
approved. This project can then become a more permanent (non-exploratory) repository for final report figures.

## Project Description
This project includes:
- Figure code for the analysis of **missed insulin pulses** (`insulin_pulses_animation.py`, `insulin_pulses_figures.py`)

- **Replay loop exploratory figure code** (`replay_loop_exploratory_figure_examples.py`). 
This code is very work and progress and left just in case anyone goes back to thinking about ways to visualize that.

- **Code for iCGM sensitivity analysis figures**, including the code used for exploratory analysis 
(labeled [ARCHIVE]) and a more recent and up to date file that can be run for aggregated data 
and figures for the iCGM sensitivity analysis (`icgm_sensitivity_analysis_report_figures_and_tables.py`).

- Generalized visualization **code for creating matplotlib and plotly 
animations/static visualizations of simulation output** that more or less match
Tidepool style guidelines. Files for those visualizations include `simulation_figure_matplotlib.py`, `simulation_figure_plotly.py`, 
`simulation_figures_shared_functions`, `simulation_figures_demo_examples`. 
Example output of the demo code is shown below.

![](simulation_example_gif.gif)

### Technologies (Update this list)
* Python (99% of the time)
* [Anaconda](https://www.anaconda.com/) for our virtual environments
* Pandas for working with data (99% of the time)
* Google Colab for sharing examples
* Plotly for visualization
* Pytest for testing
* Travis for continuous integration testing
* Black for code style
* Flake8 for linting
* [Sphinx](https://www.sphinx-doc.org/en/master/) for documentation
* Numpy docstring format
* pre-commit for githooks

## Getting Started with the Conda Virtual Environment
1. Install [Miniconda](https://conda.io/miniconda.html). CAUTION for python virtual env users: Anaconda will automatically update your .bash_profile
so that conda is launched automatically when you open a terminal. You can deactivate with the command `conda deactivate`
or you can edit your bash_profile.
2. If you are new to [Anaconda](https://docs.anaconda.com/anaconda/user-guide/getting-started/)
check out their getting started docs.
3. If you want the pre-commit githooks to install automatically, then following these
[directions](https://pre-commit.com/#automatically-enabling-pre-commit-on-repositories).
4. Clone this repo (for help see this [tutorial](https://help.github.com/articles/cloning-a-repository/)).
5. In a terminal, navigate to the directory where you cloned this repo.
6. Run `conda update -n base -c defaults conda` to update to the latest version of conda
7. Run `conda env create -f conda-environment.yml --name [input-your-env-name-here]`. This will download all of the package dependencies
and install them in a conda (python) virtual environment. (Insert your conda env name in the brackets. Do not include the brackets)
8. Run `conda env list` to get a list of conda environments and select the environment
that was created from the environmental.yml file (hint: environment name is at the top of the file)
9. Run `conda activate <conda-env-name>` or `source activate <conda-env-name>` to start the environment.
10. If you did not setup your global git-template to automatically install the pre-commit githooks, then
run `pre-commit install` to enable the githooks.
11. Run `deactivate` to stop the environment.

## Maintaining Compatability with venv and virtualenv
This may seem counterintuitive, but when you are loading new packages into your conda virtual environment,
load them in using `pip`, and export your environment using `pip-chill > requirements.txt`.
We take this approach to make our code compatible with people that prefer to use venv or virtualenv.
This may also make it easier to convert existing packages into pypi packages. We only install packages directly
in conda using the conda-environment.yml file when packages are not available via pip (e.g., R and plotly-orca).

## Getting Started with this project
Raw Data is being kept [here, for iCGM Sensitivity Analysis Scenario and Results Files](https://drive.google.com/drive/u/2/folders/1QDGB5s8YVw9Iy-P_a0xl8nIZZCRm8E5W).

The rest of the data, if not already in the repository, can be found on Google Drive at
[sample_data_for_data-science--explore--risk-sim-figures](https://drive.google.com/drive/folders/1IFIbc0Z6mOtT-hw6K6obJcd9QaYW1uEG?usp=sharing).
This includes:

    - `replay_loop.csv` for `replay_loop_exploratory_figure_examples.py`
    - `risk_scenarios_do_nothing.csv` and `risk_scenarios_PyLoopkit v0.1.csv for simulation_figures_demo_examples.py`
    - The files in `insulin-pulses-sample-files-2020-07-02` for `insulin_pulses_animation.py` and `insulin_pulses_figures.py`

## Contributing Guide
1. All are welcome to contribute to this project.
1. Naming convention for notebooks is
`[short_description]-[initials]-[date_created]-[version]`,
e.g. `initial_data_exploration-jqp-2020-04-25-v-0-1-0.ipynb`.
A short `_` delimited description, the creator's initials, date of creation, and a version number,
1. Naming convention for data files, figures, and tables is
`[PHI (if applicable)]-[short_description]-[date created or downloaded]-[code_version]`,
e.g. `raw_project_data_from_mnist-2020-04-25-v-0-1-0.csv`,
or `project_data_figure-2020-04-25-v-0-1-0.png`.

NOTE: PHI data is never stored in github and the .gitignore file includes this requirement as well.

## Featured Notebooks/Analysis/Deliverables

## Tidepool Data Science Team
|Name (with github link)    |  [Tidepool Slack](https://tidepoolorg.slack.com/)   |
|---------|-----------------|
|[Ed Nykaza](https://github.com/ed-nykaza)| @ed        |
|[Jason Meno](https://github.com/jameno) |  @jason    |
|[Cameron Summers](https://github.com/scaubrey) |  @Cameron Summers    |
|[Anne Evered](https://github.com/aeevered) |  @anne    |