from .chart_datatypes import ChartData, MultiChartData


def multi_mean_tats(all_results: dict[int, dict]) -> ChartData:
    """Chart data for bar chart of overall mean TATs by scenario.

    TODO: Change to grouped bar chart with both overall and lab TAT?
    Does the front-end support this?
    """
    ret = {}
    ret["x"] = [str(scenario_id) for scenario_id in all_results.keys()]
    ret["y"] = [result["overall_tat"] for result in all_results.values()]
    return ret


def multi_mean_util(all_results: dict[int, dict]) -> dict[str, ChartData]:
    """Get mean resource utilisation values from a multi-scenario analysis result list.
    Each resource in the model maps to one barchart, with scenarios as x axis"""
    ret = {}
    kpi = "utilization_by_resource"

    scenario_ids = list(all_results.keys())
    resources = all_results[scenario_ids[0]][kpi]["x"]  # list of resources
    for idx, resource in enumerate(resources):
        chart_data = {}

        # Change scenario_ids to strings for categorical data
        chart_data["x"] = [str(scenario_id) for scenario_id in scenario_ids]

        chart_data["y"] = [result[kpi]["y"][idx] for result in all_results.values()]
        ret[resource] = chart_data

    return ret


def multi_util_hourlies(all_results: dict[int, dict]) -> dict[str, MultiChartData]:
    """Get mean resource utilisation values from a multi-scenario analysis result list.
    Each resource in the model maps to one barchart, with scenarios as line labels."""
    ret = {}
    kpi = "hourly_utilization_by_resource"

    scenario_ids = list(all_results.keys())

    # These should be the same for all scenarios in an analysis, so just read the first one,
    # i.e. scenario_ids[0]
    resources = all_results[scenario_ids[0]][kpi]["labels"]  # list of resources
    hour_series = all_results[scenario_ids[0]][kpi]["x"]  # 1...sim_length

    for idx, resource in enumerate(resources):
        chart_data = {}

        # We assume all results for this KPI have the same x data across all scenarios
        chart_data["x"] = hour_series
        chart_data["labels"] = [str(scenario_id) for scenario_id in scenario_ids]
        chart_data["y"] = [result[kpi]["y"][idx] for result in all_results.values()]
        ret[resource] = chart_data
    return ret
