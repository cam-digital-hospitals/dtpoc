from fastapi import FastAPI

from ..conf import VERSION

app = FastAPI(
    root_path=f"/api/ana-hpath-sim/{VERSION}",
)

# Ideal Workflow description:
# simulation(p1,p2,p3) salabim model -> json
# load state json -> simulation(p4,p5,p6) -> salabim model -> json
# Simulation
# POST orchestrator/sim/launch simulation_input --runs--> simulation(sim_id) -> output.json (salabim model -> json) -> orchestrator -> orchestrator/sim/{sim_id}/output

# Analytics
# POST orchestrator/ana/launch sim_id1 -> orchestrator --runs--> analytics(ana_id) --> output.json -> orchestrator
# orchestrator -> /{ana_id}/overall_tat, /{ana_id}/utilisation_means, /{ana_id}/q_length_hourlies
# orchestrator -> POST /multi_scenario_hourlies compare_sims=[sim_id1, sim_id2] -> analytics(ana_id1) -> output.json -> orchestrator
# orchestrator -> /{ana_id1}/output


# Current Proposed Workflow

# Sensor

# lift_sen1, lift_sen2, lift_sen3 -> outages (/download_json)
# Analytics

# excel_file -> json
# excel_file, schedule_json, asset_json, inv_json -> orchestrator --runs--> ana_hpath_sim(ana_id) -> hpath_sim -> do some calculation -> output.json -> orchestrator -> ana/{id}/output
# POST /multi_scenario_hourlies compare_sims=[ana_id1, ana_id2], ana_multisenario ->

# m-w, w-f

# yinchi, rohit
