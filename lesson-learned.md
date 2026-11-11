# Lessons Learned

## Project

**CI/CD Pipeline Using Jenkins — Deploy a Docker Image to Kubernetes**

This project helped me understand how the individual tools in a DevOps workflow connect. I moved beyond running Docker containers and Kubernetes resources manually and worked toward automating the delivery process with Jenkins.

## 1. Python environments should be isolated

### What happened

When I tried to install the application's Python dependencies, I encountered the `externally-managed-environment` error.

### What I learned

Some Linux distributions protect their system Python installation from changes made by `pip`. This is intended to prevent conflicts with packages managed by the operating system.

The correct approach for this project was to create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Takeaway

Use a project-level virtual environment to isolate Python dependencies. Do not modify the OS-managed Python environment or bypass its protection just to install application packages.

---

## 2. A locally built Docker image is not automatically available to Kubernetes

### What happened

The Kubernetes Service was created, but the Flask Pods could not download the container image. The Pods entered an image-pull failure state.

I initially tried changing the Deployment image:

```bash
kubectl set image deployment/flask-app flask-app=flask-k8s-demo
```

That did not solve the issue because the image reference was not the published registry image.

### What I learned

Building an image locally and making it available to a Kubernetes cluster are separate operations. The cluster's container runtime needs access to the image. In this setup, I used Docker Hub as the registry.

I tagged and pushed the image:

```bash
docker tag flask-k8s-demo:1.0.0 drexterdill/flask-k8s-demo:1.0.0
docker push drexterdill/flask-k8s-demo:1.0.0
```

The Deployment then needed to reference the same fully qualified image:

```text
drexterdill/flask-k8s-demo:1.0.0
```

### Takeaway

A container registry is the hand-off point between the image build process and a cluster that needs to pull and run that image. The image name, repository, and tag must match exactly.

---

## 3. Kubernetes context matters

### What happened

I realized that I was using the wrong Kubernetes context. My environment had a MicroK8s context, and I needed to make sure `kubectl` was targeting the intended cluster.

### What I learned

`kubectl` can manage multiple clusters through contexts. A successful command does not prove that it was executed against the correct cluster.

I now check the active context before making changes:

```bash
kubectl config get-contexts
kubectl config current-context
kubectl get nodes
```

### Takeaway

Always verify the target cluster before applying manifests or updating a Deployment. The Jenkins agent must also use the intended context; its environment may differ from my interactive terminal.

---

## 4. The Jenkins controller and agent can run on different environments

### What happened

I ran the Jenkins controller on Windows and configured a Jenkins agent inside my Ubuntu WSL2 environment. I installed Java in WSL2 and connected the agent to the Windows controller.

The WSL2 environment could not reliably reach the controller using the same `localhost` address used in the Windows browser. I investigated the WSL2 network gateway and Windows Firewall.

### What I learned

The Jenkins controller coordinates the work, while the agent executes the pipeline steps. They do not have to run on the same operating system or machine.

In this project:

- Windows hosted the Jenkins controller.
- Ubuntu on WSL2 hosted the `wsl2-agent`.
- The agent executed Linux commands and accessed Docker and MicroK8s.
- The controller and agent communicated over the network.

I used the Windows-side WSL2 gateway address for the agent connection in this lab:

```text
http://172.18.32.1:8080/
```

The Windows loopback URL:

```text
http://localhost:8080
```

was used to access Jenkins from Windows itself.

### Takeaway

Understand where each process runs and which network address is reachable from that environment. `localhost` is relative to the machine or network namespace making the request.

---

## 5. Windows Firewall rules need to be scoped

### What happened

I needed to allow the WSL2 agent to reach the Jenkins controller on TCP port `8080`. I configured a Windows Firewall inbound rule limited to the WSL2 subnet observed at the time.

### What I learned

A firewall rule should allow only the traffic required for the task. Opening Jenkins broadly would unnecessarily increase exposure.

The lab rule used this example subnet:

```text
172.18.32.0/20
```

WSL2 network ranges can change, so the subnet must be checked again if connectivity stops working.

### Takeaway

Use the narrowest practical source range and port. A firewall rule does not replace checking the service's listening interface or verifying the route from WSL2.

---

## 6. Running the Jenkins agent as a systemd service improves reliability

### What happened

After connecting the agent manually, I wanted it to run in the background rather than depend on an open terminal. I configured a systemd service in Ubuntu WSL2.

The service is:

```text
/etc/systemd/system/jenkins-agent.service
```

The working directory is:

```text
/home/samachilles/jenkins-agent
```

I enabled and started it with:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now jenkins-agent
sudo systemctl status jenkins-agent
```

### What I learned

A systemd service can manage a long-running process, start it automatically when the systemd environment starts, and make it easier to inspect logs and restart it.

### Takeaway

Use a service manager for persistent agents rather than relying on a manually launched terminal process. However, WSL2 still needs to be running, and the Windows Jenkins controller must be reachable.

---

## 7. Kubernetes Deployments must exist before an image update can target them

### What happened

I learned that an image-update command such as `kubectl set image` targets an existing Deployment and a container inside that Deployment. It cannot update a Deployment that has not yet been created.

I therefore created the Deployment and Service before relying on the CI/CD pipeline to update the image.

### What I learned

The Deployment manages the desired number of Pods and their container configuration. The Service provides stable networking to matching Pods. These resources have different responsibilities.

I used commands such as:

```bash
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml
```

Then an image update and rollout check:

```bash
kubectl set image deployment/flask-app \
  flask-app=drexterdill/flask-k8s-demo:1.0.0

kubectl rollout status deployment/flask-app --timeout=120s
```

### Takeaway

Understand the resource lifecycle. Create the workload before updating it, and verify that the Deployment name and container name match the manifest.

---

## 8. A successful `kubectl apply` does not mean the application is healthy

### What happened

I saw that Kubernetes resources could exist even while the application Pods were unable to start.

### What I learned

Kubernetes accepting a manifest only confirms that the API server accepted the resource configuration. It does not guarantee that the image can be pulled, the container can start, or the application is responding.

Useful checks include:

```bash
kubectl get deployments
kubectl get pods -o wide
kubectl get services
kubectl describe pod <POD_NAME>
kubectl rollout status deployment/flask-app --timeout=120s
```

I can also test the application health endpoint:

```bash
curl http://127.0.0.1:8080/health
```

when the service is port-forwarded.

### Takeaway

Verify the full application lifecycle: resource creation, image pull, Pod readiness, rollout completion, and application-level health.

---

## 9. CI/CD depends on the complete delivery chain

### What happened

Several individual parts appeared to work, but the end-to-end pipeline could not succeed until the image name, registry, Kubernetes context, agent connectivity, and existing Deployment were all correct.

### What I learned

A CI/CD pipeline is not just a sequence of shell commands. Each stage depends on outputs and permissions from the previous stage:

1. Jenkins must retrieve the right source code.
2. Tests must run successfully.
3. Docker must build the expected image.
4. The image must be tagged and pushed to a registry.
5. Kubernetes must target the correct cluster.
6. The Deployment must reference a pullable image.
7. The rollout must complete and the application must be healthy.

### Takeaway

Troubleshoot the chain one stage at a time. Verify each hand-off instead of assuming that success in one tool means the next tool has everything it needs.

---

## Improvements for a future iteration

- Use immutable image tags based on the Git commit SHA or Jenkins build number.
- Add a clear test report and fail the pipeline when tests fail.
- Use least-privilege Kubernetes RBAC for the Jenkins deployment identity.
- Add an automated post-deployment health check.
- Consider a rollback strategy when deployment verification fails.

## Final reflection

This project strengthened my understanding of how CI/CD connects source control, build automation, container registries, and Kubernetes deployments. The most important lesson was learning to verify the boundaries between systems: the agent's network access, the Docker image registry, the active Kubernetes context, and the state of the Deployment.

It also reinforced that troubleshooting is part of engineering. Each issue helped me understand not only which command to run, but why the system behaved that way.
