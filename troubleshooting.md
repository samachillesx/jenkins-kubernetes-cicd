# Troubleshooting

This document records issues encountered while building the Jenkins → Docker Hub → MicroK8s CI/CD workflow, why they happened, and how to diagnose them.

## 1. Python reports `externally-managed-environment`

### Symptom

Installing dependencies with `pip` into the system Python fails with an `externally-managed-environment` message.

### Cause

The Linux distribution protects its system-managed Python installation (PEP 668). Installing packages globally with pip can conflict with packages managed by the operating system.

### Resolution

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies inside it:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run tests:

```bash
python -m pytest -v
```

### Prevention

- Use a virtual environment for project dependencies.
- Add `venv/` to `.gitignore`.
- Do not use `sudo pip` or disable the system's externally-managed protection as a workaround.

If `venv` creation fails because the venv module is missing, install the OS package that provides it for your Ubuntu release, then retry.

---

## 2. Kubernetes Pods cannot pull the Docker image

### Symptom

The Service exists, but application Pods fail to start and show image-pull errors such as `ErrImagePull` or `ImagePullBackOff`.

### Cause

A Kubernetes Service does not create Pods. The Deployment creates Pods, and the Pods' container runtime must be able to pull the image specified in the Deployment.

The initial image reference was incorrect/not available to the cluster. The image had been built locally, but the MicroK8s cluster could not automatically use the local Docker image.

### Diagnosis

```bash
kubectl get pods
kubectl describe pod <POD_NAME>
kubectl describe deployment flask-app
```

Look at the Pod Events section for the exact image name and registry error.

### Resolution

Tag the local image with the Docker Hub namespace and repository:

```bash
docker tag flask-k8s-demo:1.0.0 drexterdill/flask-k8s-demo:1.0.0
```

Push it:

```bash
docker push drexterdill/flask-k8s-demo:1.0.0
```

Update the Deployment's image reference so it matches the pushed image exactly:

```yaml
image: drexterdill/flask-k8s-demo:1.0.0
```

Apply the manifest or update the Deployment:

```bash
kubectl apply -f kubernetes/deployment.yaml
```

Alternatively, update an existing Deployment with the full image reference:

```bash
kubectl set image deployment/flask-app \
  flask-app=drexterdill/flask-k8s-demo:1.0.0
```

Then wait for the rollout:

```bash
kubectl rollout status deployment/flask-app --timeout=120s
```

### Important clarification

The earlier command:

```bash
kubectl set image deployment/flask-app flask-app=flask-k8s-demo
```

was insufficient if `flask-k8s-demo` was only a local image name. It did not identify the Docker Hub namespace and version tag. The image reference used by Kubernetes must identify an image that the cluster can pull, for example `drexterdill/flask-k8s-demo:1.0.0`.

---

## 3. The wrong Kubernetes context is active

### Symptom

`kubectl` commands appear to work, but resources are missing, updates affect an unexpected cluster, or the expected application does not appear.

### Cause

The active kubeconfig context was not the intended MicroK8s context. A machine can have multiple Kubernetes contexts (for example, Docker Desktop and MicroK8s).

### Diagnosis

```bash
kubectl config get-contexts
kubectl config current-context
kubectl cluster-info
kubectl get nodes
```

The current context is marked with an asterisk in the `get-contexts` output.

### Resolution

Select the intended context only after confirming its name:

```bash
kubectl config use-context <MICROK8S_CONTEXT_NAME>
```

Verify again:

```bash
kubectl config current-context
kubectl get nodes
```

Also verify the context from the Jenkins agent's execution environment. Jenkins may run with a different `HOME`, kubeconfig, or service environment from your interactive shell.

### Prevention

Make the target cluster explicit in your deployment process and verify the context before applying changes. Do not assume that the context selected in one terminal is automatically selected for every user or service.

---

## 4. Jenkins WSL2 agent cannot connect to the Windows controller

### Symptom

The Jenkins agent remains offline or cannot reach the controller at `localhost:8080`.

### Cause

The Jenkins controller runs on Windows, while the agent runs inside Ubuntu on WSL2. `localhost` inside WSL2 refers to the Linux environment; it is not always the correct address for reaching a Windows service. Windows Firewall can also block inbound traffic.

### Diagnosis

On Windows, verify Jenkins is listening and accessible:

```text
http://localhost:8080
```

Inside WSL2, inspect the network route:

```bash
ip route
```

Test the Windows-side WSL gateway (the lab used `172.18.32.1` at one point):

```bash
curl -I http://172.18.32.1:8080/login
```

### Resolution

Use the current Windows-side WSL gateway address in the agent connection URL. If required, create a narrowly scoped Windows Firewall rule for TCP port `8080`, limited to the current WSL2 subnet.

Example PowerShell rule (re-check the subnet first; this is a historical lab value):

```powershell
New-NetFirewallRule `
  -DisplayName "Jenkins 8080 from WSL2" `
  -Direction Inbound `
  -Action Allow `
  -Protocol TCP `
  -LocalPort 8080 `
  -RemoteAddress 172.18.32.0/20 `
  -Profile Public
```

The two URLs serve different paths:

- `http://localhost:8080` — Windows loopback access.
- `http://172.18.32.1:8080` — Windows-side WSL2 gateway access used by the WSL2 agent in this lab.

A firewall rule does not override a service that is bound only to loopback. Confirm Jenkins is listening on an interface reachable from WSL2 and restrict exposure to trusted networks.

### Prevention

- Re-check the WSL2 gateway and subnet after network changes.
- Keep the firewall rule restricted to the required source range.
- Avoid exposing Jenkins port `8080` broadly.
- Use the agent launch command generated by the Jenkins node configuration.

---

## 5. Jenkins agent does not stay running

### Symptom

The agent disconnects when the terminal closes or after the WSL2 session changes.

### Cause

Launching `java -jar agent.jar ...` interactively ties the agent process to that terminal/session.

### Resolution

Run the agent under systemd in WSL2. The lab service is:

```text
/etc/systemd/system/jenkins-agent.service
```

The agent work directory is:

```text
/home/samachilles/jenkins-agent
```

Manage it with:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now jenkins-agent
sudo systemctl status jenkins-agent
```

Inspect logs:

```bash
sudo journalctl -u jenkins-agent -f
```

Restart after configuration changes:

```bash
sudo systemctl restart jenkins-agent
```

### Important

The service can only connect while WSL2 is running and the Windows Jenkins controller is reachable. systemd does not make the Windows controller or WSL2 environment permanently available.

---

## 6. Jenkins pipeline cannot run Docker or kubectl

### Symptom

A command works in the interactive Ubuntu terminal but fails in a Jenkins build with a command-not-found, permission, Docker socket, or kubeconfig error.

### Possible causes

- Jenkins is running the job on the wrong agent.
- The Jenkins node label does not match the label requested by the pipeline.
- The service user has a different `PATH` or `HOME`.
- The agent user lacks Docker socket permissions.
- The agent user cannot read the kubeconfig or access the MicroK8s cluster.
- The active Kubernetes context differs from the one used interactively.

### Diagnosis

Run diagnostic commands as a pipeline step:

```bash
whoami
pwd
echo "$PATH"
java -version
docker version
kubectl config current-context
kubectl get nodes
```

### Resolution

- Confirm the job is assigned to `wsl2-agent` (or the exact configured label).
- Install required tools for the agent user and make their paths available to the service.
- Grant only the permissions needed for Docker and Kubernetes operations.
- Ensure the agent uses the intended kubeconfig and context.
- Restart the agent service after changing its service environment.

Docker group membership can grant powerful host-level privileges. Treat access to the Docker socket as privileged and do not grant it casually.

---

## 7. Deployment update does not complete

### Symptom

`kubectl set image` returns, but the application does not become ready or the rollout times out.

### Cause

A Deployment must already exist, the container name must match a container in its Pod template, and the image must be available. The Pods must also pass their readiness checks and be schedulable.

### Diagnosis

```bash
kubectl get deployment flask-app
kubectl get pods -o wide
kubectl describe deployment flask-app
kubectl describe pod <POD_NAME>
kubectl get events --sort-by=.metadata.creationTimestamp
```

### Resolution

Create/apply the Deployment and Service before relying on a pipeline step that updates an existing Deployment:

```bash
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml
```

Then update the image using the actual Deployment name, container name, and published image:

```bash
kubectl set image deployment/flask-app \
  flask-app=drexterdill/flask-k8s-demo:1.0.0

kubectl rollout status deployment/flask-app --timeout=120s
```

The two commands must be separate shell commands (for example, on separate lines or joined with `&&`). If the Deployment or container names differ, use the names in the manifest.

---

## 8. Service exists but the application is unreachable

### Symptom

`kubectl get services` shows the Service, but requests do not reach the Flask application.

### Checks

A Service selects Pods by labels. Confirm the Service type, selector, port, targetPort, and NodePort, and selector matches the labels on the Deployment's Pod template:

```bash
kubectl describe service flask-service
kubectl get pods --show-labels
kubectl get endpoints flask-service
```

If the Service has no endpoints, investigate selector/label mismatches and whether the Pods are ready.

Confirm the container listens on `0.0.0.0:5000`, not only `127.0.0.1`, and that the Service `targetPort` matches the container's listening port.

The project uses a NodePort Service to expose the application externally on port 30080:

Traffic follows this path: NodeIP:30080 → Service:80 → Flask Pod:5000

```bash
curl http://127.0.0.1:30080/health
```

Alternatively, use the Kubernetes node IP:

```bash
kubectl get nodes -o wide
curl http://NODE_IP:30080/health
```

Test with port forwarding:

```bash
kubectl port-forward service/flask-service 8080:80
```

Then, in another terminal:

```bash
curl http://127.0.0.1:8080/health
```

Port forwarding uses the Service port (80), which forwards traffic to the container's targetPort (5000).

8080:80 — local port 8080 forwarded to Service port 80.
80:5000 — Service port 80 forwards to container port 5000.
30080 — NodePort for accessing the application through the Kubernetes node.

---

## 9. Safe rollback

If a Deployment update causes a failure, inspect rollout history:

```bash
kubectl rollout history deployment/flask-app
```

Roll back to the previous revision if appropriate:

```bash
kubectl rollout undo deployment/flask-app
kubectl rollout status deployment/flask-app --timeout=120s
```

Confirm the application and Pods are healthy after rollback.

## General troubleshooting checklist

- [ ] Is the Jenkins controller running on Windows?
- [ ] Is the WSL2 agent online in Jenkins?
- [ ] Is the pipeline running on the intended agent?
- [ ] Can the agent access GitHub?
- [ ] Do Python tests pass?
- [ ] Does the Docker image build successfully?
- [ ] Was the exact image tag pushed to Docker Hub?
- [ ] Is the intended MicroK8s context active for the agent?
- [ ] Do the Deployment and Service exist?
- [ ] Do the Deployment selector and Service selector match Pod labels?
- [ ] Does the rollout complete?
- [ ] Does `/health` return the expected healthy response?