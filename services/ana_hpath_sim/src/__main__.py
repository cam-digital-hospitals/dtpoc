import json
import logging

import openpyxl as oxl

from .analytics.report import Report
from .conf import INPUT_EXCEL_FILE, OUTPUT_FILE
from .simulation.input_data import SimulationConfig
from .simulation.model import Model

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print(f"SIM: id=tbd, sim_hours=1?")
    wbook = oxl.load_workbook(INPUT_EXCEL_FILE, data_only=True)
    input_data = SimulationConfig.from_workbook(wbook, 168 * 1, 1)
    model = Model(input_data)
    model.run()

    # If we are able to save the state here....
    # we can continue other simulation/analytics with the state(s)

    # simulation output =>
    #    ana_wip_by_stage
    #    ana_wip_summaries
    #    ana_overall_tat
    #    ana_overall_lab_tat
    #    ana_progress
    #    ana_lab_progress
    #    ana_tat_by_stage
    #    ana_resource_allocation
    #    ana_utilization_by_resource
    #    ana_q_length_by_resource
    #    ana_hourly_utilization_by_resource

    # Because, this allows us to evaluate other types of analytics too... for example:
    # simulation output(lift_0), simulation output(lift_1) =>
    #    ana_overall_tat_ratio: 0.79 (Means lift_1 better than lift_0)

    # Which can later be other complex functions or ML models
    # simulation output(senario_1)....simulation output(senario_n) =>
    #    ana_complex_efficiency_func: [0.4, 0.6 ... 0.7, 0.9]n

    # Things to serialize to be able to do that?:
    # model.wips
    # model.specimen_data
    # model.resources

    # json.dump(model.specimen_data, open("test.out", "w", encoding="utf-8"), indent=2)
    # # json.dump(model.wips, open("test1.out", "w", encoding="utf-8"), indent=2)
    # # json.dump(model.resources, open("test2.out", "w", encoding="utf-8"), indent=2)
    # for res in utils.dc_values(model.resources):
    #     for wip in res.all_monitors():
    #         with open(f"tmp/{wip.name()}.dat", "wb") as f:
    #             pickle.dump(wip.freeze(), f)

    analytics_report = Report.from_model(model).model_dump(mode="json")

    json.dump(analytics_report, open(OUTPUT_FILE, "w"))
