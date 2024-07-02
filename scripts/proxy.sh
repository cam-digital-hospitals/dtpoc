#!/bin/bash
# Helper script to easily port-forward kubernetes services during development

select_namespace() {
  echo "Fetching namespaces..."
  namespaces=$(kubectl get namespaces -o jsonpath="{.items[*].metadata.name}")

  PS3="Please select a namespace: "
  select namespace in $namespaces; do
    if [ -n "$namespace" ]; then
      printf "Selected namespace: %s\n" "$namespace"
      break
    else
      echo "Invalid selection. Please try again."
    fi
  done
}

select_service() {
  echo "Fetching services in namespace $namespace..."
  services=$(kubectl get services -n "$namespace" -o jsonpath="{.items[*].metadata.name}")

  PS3="Please select a service: "
  select service in $services; do
    if [ -n "$service" ]; then
      printf "Selected service: %s\n" "$service"
      break
    else
      echo "Invalid selection. Please try again."
    fi
  done
}

select_port() {
  echo "Fetching ports for service $service..."
  ports=$(kubectl get service "$service" -n "$namespace" -o jsonpath="{.spec.ports[*].port}")

  PS3="Please select a port to forward: "
  select port in $ports; do
    if [ -n "$port" ]; then
      printf "Selected port: %s\n" "$port"
      break
    else
      echo "Invalid selection. Please try again."
    fi
  done
}

port_forward() {
  read -rp "Enter the local port you want to forward to $port: " local_port
  kubectl port-forward svc/"$service" "$local_port":"$port" -n "$namespace" &
  port_forward_pid=$!
  echo "Port forwarding started. You can access the service at: http://localhost:$local_port"
  echo "Press [Enter] to stop port forwarding..."
  read -r
  kill $port_forward_pid
  echo "Port forwarding stopped."
}

select_namespace
select_service
select_port
port_forward