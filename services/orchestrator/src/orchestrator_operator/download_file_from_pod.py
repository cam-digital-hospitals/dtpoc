import tempfile
import shutil
from kubernetes import client, config
from kubernetes.stream import stream


def touch_file(namespace, pod_name, container_name="output-data-access", file_path="/orchestrator-done"):
    # Initialize CoreV1Api
    core_v1 = client.CoreV1Api()

    # Command to touch the orchestrator-done file
    exec_command = ["touch", file_path]

    # Execute the command on the specified pod
    resp = stream(
        core_v1.connect_get_namespaced_pod_exec,
        pod_name,
        namespace,
        container=container_name,
        command=exec_command,
        stderr=True,
        stdin=False,
        stdout=True,
        tty=False,
    )

    print(f"Executed touch command on {pod_name}/{container_name} to create {file_path}")

def read_output_file(namespace, pod_name, file_path, container_name="main"):
    # Initialize CoreV1Api
    core_v1 = client.CoreV1Api()
    
    # Check if the pod is completed
    pod = core_v1.read_namespaced_pod(name=pod_name, namespace=namespace)
    if pod.status.phase not in ['Running', 'Succeeded', 'Failed']:
        print(f"Pod {pod_name} is not in a suitable state for file retrieval. Current status: {pod.status.phase}")
        return None

    # Command to create a tar archive of the output file
    exec_command = ["tar", "cf", "-", file_path]

    # Execute the command on the specified pod
    resp = stream(
        core_v1.connect_get_namespaced_pod_exec,
        pod_name,
        namespace,
        container=container_name,
        command=exec_command,
        stderr=True,
        stdin=False,
        stdout=True,
        tty=False,
        _preload_content=False,
    )

    # Create a temporary file to store the tar archive
    with tempfile.NamedTemporaryFile(delete=False) as tar_file:
        while resp.is_open():
            resp.update(timeout=1)
            if resp.peek_stdout():
                tar_file.write(str(resp.read_stdout()).encode())
            if resp.peek_stderr():
                print("Error:", resp.read_stderr())

    tar_file.close()

    # Create a temporary directory to extract the tar archive
    output_dir = tempfile.mkdtemp()
    shutil.unpack_archive(tar_file.name, output_dir, "tar")

    return output_dir

# Load kubeconfig
config.load_kube_config()

# Example usage
namespace = "default"
pod_name = "668496619e4290459f741b40-5k9k6"
file_path = "output"
output_dir = read_output_file(namespace, pod_name, file_path, container_name="output-data-access")
touch_file(namespace, pod_name)
print(f"Downloaded folder: {output_dir}/output")
