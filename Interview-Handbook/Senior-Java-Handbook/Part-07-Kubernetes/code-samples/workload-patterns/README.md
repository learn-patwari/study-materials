# Code samples — Chapter 07.02: Workloads, Resource Management & Production Deployment Patterns

Kubernetes manifests referenced throughout the chapter. This sandbox has no
live cluster and no `kubectl`/`helm` binary, so the strongest verification
available offline is: valid YAML, and every document carries the required
top-level Kubernetes object keys (`apiVersion`, `kind`, `metadata`). Run:

```bash
./validate.sh
```

If you have `kubectl` available (pointed at any cluster, even `kind`/`minikube`),
prefer real API-server-side validation on top of this:

```bash
kubectl apply --dry-run=server -f deployment-rolling-update.yaml
```

| File | What it demonstrates |
|---|---|
| `deployment-rolling-update.yaml` | Safe rolling update (`maxUnavailable: 0`), readiness-gated traffic, `preStop` drain hook, container-aware `JAVA_TOOL_OPTIONS` |
| `deployment-canary.yaml` | Replica-ratio canary using two Deployments behind one Service — no mesh required |
| `hpa-and-pdb.yaml` | `HorizontalPodAutoscaler` on CPU + a custom RPS metric, and a `PodDisruptionBudget` bounding voluntary disruption |
| `qos-class-examples.yaml` | The three QoS classes (Guaranteed/Burstable/BestEffort) derived purely from `resources.requests`/`resources.limits` shape |
