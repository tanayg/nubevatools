#!/bin/bash

cd "$(dirname "$0")"

kubectl apply -f service_account.yaml
kubectl apply -f role.yaml
kubectl apply -f role_binding.yaml
kubectl apply -f cluster_role_binding.yaml
kubectl apply -f nukates.nuos.io_nukates_crd.yaml
kubectl apply -f nukates.nuos.io_nuconfigs_crd.yaml
kubectl apply -f operator.yaml

echo "CREATE: Operator"
kubectl apply -f NuComplete.yaml

echo "CREATE: NuKates that deploys all microservices"
kubectl apply -f nukates.yaml
