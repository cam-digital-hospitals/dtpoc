# DT POC Developer Documentation

### Prerequisites

Before you begin, make sure you have the following ready:

1. **Kubernetes Cluster**
   - You need a Kubernetes cluster running. This could be:
     - A local setup using Docker Desktop with the Kubernetes feature enabled. [Learn how to set it up here](https://docs.docker.com/desktop/kubernetes/).
     - A Kubernetes cluster (version 1.28.3 or higher) running on a server. [Learn how to set it up here](https://kubernetes.io/docs/setup/).

2. **Helm Installation**
   - Helm is a tool to manage Kubernetes applications. Ensure you have Helm installed on your computer. [Install Helm by following this guide](https://helm.sh/docs/intro/install/).

3. **Source code**
   - Clone the dtpoc repository:
     ```bash
     git clone https://github.com/cam-digital-hospitals/dtpoc.git
     ```

## Services Overview

### Orchestrator Operator

The Orchestrator is a [Kubernetes operator](https://kubernetes.io/docs/concepts/extend-kubernetes/operator/) that watches specific Kubernetes resources called custom resource definitions (CRDs) which describe analytics jobs, and acts on them automatically.

#### Creating a Sample Analytics Resource

Here's how to set up a sample Analytics job in your Kubernetes cluster:

1. **Expected Service Object**

    The operator expects a service with the same ID as the analytics job name in the MongoDB services collection. Here is an example of what that service object looks like:

    ```json
    {
        "_id": "669a52d1364a1b751c550d56",
        "image": "ghcr.io/cam-digital-hospitals/digital-hosp-des",
        "version": "latest",
        "description": "An analytics module that uses the Histopathology BIM runner times to simulate sample flow and reports KPIs",
        "mount_files": {
            "669a4eee364a1b751c550b02": "input.xlsx"
        },
        "reps": 2,
        "env": {
            "INPUT_EXCEL_FILE": "/input/input.xlsx",
            "OUTPUT_FOLDER": "/output",
            "SIM_HOURS": "1176",
            "NUM_REPS": "2"
        }
    }
    ```

2. **Create a Configuration File**

   Create a file named `ana-digital-hosp-des.yaml` and paste the following content into it:

   ```yaml
   apiVersion: eng.cam.ac.uk/v1alpha1
   kind: Analytics
   metadata:
     name: 669a52d1364a1b751c550d56
   spec:
     image: ghcr.io/cam-digital-hospitals/digital-hosp-des:latest
     description: "An analytics module that uses the Histopathology BIM runner times to simulate sample flow and reports KPIs"
     jobType: ondemand
     reps: 2
     env:
       INPUT_EXCEL_FILE: /input/input.xlsx
       OUTPUT_FOLDER: /output
       SIM_HOURS: "1176"
       NUM_REPS: "2"
   ```

3. **Apply the Configuration**

   Open your terminal and run the following command to apply the configuration:

   ```bash
   kubectl apply -f ana-digital-hosp-des.yaml
   ```

   This command will set up the Analytics resource in your cluster, which will make the operator's main program (`main.py -> analytics_handler` function) create the necessary Kubernetes resources (like Pod/Job/CronJob) based on the `jobType`.

4. **Monitor the status of the job**:

    ```bash
    kubectl get jobs
    ```

    The operator also includes a timer function (`main.py -> check_output`). This asynchronous function runs for each job to check for any output files, uploads the files to the Orchestrator MongoDB GridFS database, and updates the services collection with the newly uploaded file IDs.


### Orchestrator API

The Orchestrator API allows users to launch, monitor, and terminate services such as simulation and analytics jobs. It also provides functionalities to get, create, and modify files in the MongoDB GridFS database.

#### API Endpoints

- **Health Check**: Check the health of the API.
  ```http
  GET /api/orchestrator/v1alpha1/healthz
  ```

- **List Services**: Retrieve a list of services.
  ```http
  GET /api/orchestrator/v1alpha1/service/
  ```

- **Launch Service**: Launch a new service. Creates a new service in the services MongoDB collection & then creates an Analytics CRD resource in the Kubernetes cluster.
  ```http
  POST /api/orchestrator/v1alpha1/service/launch
  ```

- **Service Status**: Get the status of a specific service.
  ```http
  GET /api/orchestrator/v1alpha1/service/{id}/status
  ```

- **Service Output**: Retrieve the output of a specific multirun job.
  ```http
  GET /api/orchestrator/v1alpha1/service/{id}/output/{idx}
  ```

- **Terminate Service**: Terminate a specific service.
  ```http
  DELETE /api/orchestrator/v1alpha1/service/{id}/terminate
  ```

- **List Files**: List files stored in the GridFS database.
  ```http
  GET /api/orchestrator/v1alpha1/files
  ```

- **Upload File**: Upload a new file to the GridFS database.
  ```http
  POST /api/orchestrator/v1alpha1/files/upload
  ```

- **Get File**: Retrieve a specific file from the GridFS database.
  ```http
  GET /api/orchestrator/v1alpha1/files/{file_id}
  ```

- **Delete File**: Delete a specific file from the GridFS database.
  ```http
  DELETE /api/orchestrator/v1alpha1/files/{file_id}
  ```

## Infrastructure as YAML

### Deployment Procedure

1. Apply any CRDs found in the `infra/crds` folder.
   ```bash
   kubectl apply -f infra/crds
   ```

2. Update `infra/values.yaml`.
   ```yaml
   # Node affinity for PVCs (this is for the demo,
   # ideal solutions would provision and manage PVCs)
   persistence:
     dataRoot: /path/to/data
     nodeAffinity:
       key: kubernetes.io/hostname
       operator: In
       values:
         # Node name from `kubectl get nodes`
         - "docker-desktop"

   orchestrator:
     operator:
       image: ghcr.io/cam-digital-hospitals/orchestrator-operator
       version: latest
     api:
       image: ghcr.io/cam-digital-hospitals/orchestrator-api
       version: latest

   ingress-nginx:
     controller:
       replicaCount: 1
   ```

3. Make required data folders for persistence:
   ```bash
   mkdir -p data/mongodb_data/
   mkdir -p data/influxdb_data/
   mkdir -p data/orchestrator_data/
   ```

4. Install the Helm chart:
   ```bash
   helm install -n default dtpoc ./infra
   ```

### Upgrade

To upgrade/install the Helm release:
```bash
helm upgrade --install -n default dtpoc ./infra
```

Note: This will break for PV/PVC modification as they are immutable.

You can delete pods using `kubectl delete pod -l app=app-name` (useful for deployments that do not restart on config change)

### Cleanup

To uninstall the Helm release:
```bash
helm uninstall -n default dtpoc
```

### Components

#### Data Input:
- **Node-RED**
- **Telegraf**
  - light
  - temp

#### Data Storage:
- **InfluxDB**
- **MongoDB**
- **Mosquitto**

#### Management and Control Plane:
- **Orchestrator Operator**
- **Orchestrator API** (svc: orchestrator-api-svc ing: /api)

#### UI:
- **Mongo Express** (svc: mongo-express:8081)
- **Grafana** (svc: grafana:80)
- **Digital Hospital Frontend** (svc: digital-hosp-frontend-svc:8000 ing: /)

### Adding New UI Modules

To add a new UI module, create a YAML file named `sample-ui` in the `infra/templates/ui` folder with the following content:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-ui-deployment
  labels:
    app: my-ui
spec:
  replicas: 1
  selector:
    matchLabels:
      app: my-ui
  template:
    metadata:
      labels:
        app: my-ui
    spec:
      containers:
        - name: main
          image: nginx:alpine
          ports:
            - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: my-ui-svc
  labels:
    app: my-ui
spec:
  type: ClusterIP
  ports:
    - port: 80
      targetPort: 80
      protocol: TCP
  selector:
    app: my-ui
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ui-ingress
spec:
  ingressClassName: nginx
  rules:
    - host: example.com
      http:
        paths:
          - path: /my-ui-subroute
            pathType: Prefix
            backend:
              service:
                name: my-ui-svc
                port:
                  number: 80
```

### Adding New Databases

#### Persistent Volume (PV) Template

To create a persistent volume, use the following template:

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: example-pv
spec:
  capacity:
    storage: 10Gi
  volumeMode: Filesystem
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: standard
  hostPath:
    path: {{ .Values.persistence.dataRoot }}/example_data/
  nodeAffinity:
    required:
      nodeSelectorTerms:
        - matchExpressions:
            - key: {{ .Values.persistence.nodeAffinity.key }}
              operator: {{ .Values.persistence.nodeAffinity.operator }}
              values: {{ toYaml .Values.persistence.nodeAffinity.values | nindent 14 }}
```

#### Persistent Volume Claim (PVC) Template

To create a persistent volume claim, use the following template:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: example-pvc
  namespace: {{ .Release.Namespace }}
spec:
  volumeName: example-pv
  storageClassName: standard
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

You now have access to `example-pvc` and can use this volume to deploy the database of your choice.

### Adding New Data Input Services with Telegraf

To add a new data input service with Telegraf, create a YAML file in the `infra/templates/data_input/telegraf` folder with the following content:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: di-my-sensor-config
  namespace: {{ .Release.Namespace }}
data:
  telegraf.conf: |
    [global_tags]
      dc = "eu-west-2"

    [agent]
      interval = "10s"
      round_interval = true
      metric_buffer_limit = 10000
      collection_jitter = "0s"
      flush_jitter = "0s"
      precision = ""
      debug = false
      quiet = false
      logfile = ""
    
    [[inputs.mqtt_consumer]]
      servers = ["tcp://test.mosquitto.org:1883"]
      topics = ["CamDT/DC1/IfM/#"]
      data_format = "json_v2"
      topic_tag = ""
      qos = 1

    [[inputs.mqtt_consumer.json_v2]]
      measurement_name = "light_reading"
      timestamp_path = "timestamp"
      timestamp_format = "2006-01-02T15:04:05.000Z"
      
      [[inputs.mqtt_consumer.json_v2.field]]
        path = "lux"
        type = "float"
      [[inputs.mqtt_consumer.json_v2.tag]]
        path = "machine"
        type = "string"
    
    [[outputs.file]]
      files = ["stdout"]

    [[outputs.influxdb_v2]]
      urls = ["http://influxdb.default.svc.cluster.local:8086"]
      token = "super-secret-token"
      organization = "camdt"
      bucket = "default"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: di-my-sensor
  namespace: {{ .Release.Namespace }}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: di-my-sensor
  template:
    metadata:
      labels:
        app: di-my-sensor
    spec:
      containers:
      - name: di-my-sensor
        image: telegraf:latest
        volumeMounts:
        - name: telegraf-config
          mountPath: /etc/telegraf/telegraf.conf
          subPath: telegraf.conf
      volumes:
      - name: telegraf-config
        configMap:
          name: di-my-sensor-config
```

This configuration listens for the topic `CamDT/DC1/IfM/#` on the MQTT broker at `tcp://test.mosquitto.org:1883` and expects the message in the topic to be in JSON format. The data is then forwarded to InfluxDB.