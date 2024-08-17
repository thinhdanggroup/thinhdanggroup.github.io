---
author:
    name: "Thinh Dang"
    avatar: "/assets/images/avatar.png"
    bio: "Experienced Fintech Software Engineer Driving High-Performance Solutions"
    location: "Viet Nam"
    email: "thinhdang206@gmail.com"
    links:
        -   label: "Linkedin"
            icon: "fab fa-fw fa-linkedin"
            url: "https://www.linkedin.com/in/thinh-dang/"
toc: true
toc_sticky: true
header:
    overlay_image: /assets/images/guide-hpa-datadog/banner.jpeg
    overlay_filter: 0.5
    teaser: /assets/images/guide-hpa-datadog/banner.jpeg
title: "Setting Up Autoscaling with HPA and DataDog Metrics for a Python App in Kubernetes"
tags:
    - Auto Scaling

---

This blog post provides a comprehensive guide on setting up Horizontal Pod Autoscaling (HPA) in a Kubernetes cluster using DataDog metrics for a Python application. It begins with an introduction to the importance of autoscaling and monitoring, followed by a list of prerequisites such as a basic understanding of Kubernetes, an existing Kubernetes cluster, and a DataDog account. The guide then walks you through the steps to deploy your Python application in Kubernetes, including writing a Dockerfile and creating a Kubernetes Deployment YAML file. Next, it covers installing and configuring the DataDog agent to collect metrics from your Python app. The guide then delves into setting up HPA using these metrics, providing detailed examples and configurations. Finally, it discusses how to monitor and test the setup using DataDog’s dashboard to ensure everything is working correctly. The conclusion summarizes the key points and offers best practices for managing Kubernetes workloads effectively with HPA and DataDog metrics.

## Introduction

In this blog post, we will guide you through the process of setting up Horizontal Pod Autoscaling (HPA) in a Kubernetes cluster using DataDog metrics for a Python application. Autoscaling ensures that your application can handle varying loads efficiently by automatically adjusting the number of pods. By the end of this guide, you'll have a thorough understanding of how to configure HPA and monitor your application using DataDog metrics.

## Prerequisites

Before diving into the setup, there are a few prerequisites that you need to have in place. This section will cover the necessary tools and configurations, including a basic understanding of Kubernetes, an existing Kubernetes cluster, `kubectl` command-line tool, DataDog account, and a Python application ready for deployment. Ensuring these prerequisites are met will make the setup process smoother and more efficient.

### Basic Understanding of Kubernetes

First and foremost, a basic understanding of Kubernetes is essential. Kubernetes, often abbreviated as K8s, is an open-source platform designed to automate deploying, scaling, and operating application containers. Familiarity with concepts such as pods, deployments, services, and namespaces will be beneficial as we proceed through this guide.

### Existing Kubernetes Cluster

You need to have a running Kubernetes cluster. This could be a local setup using tools like Minikube or a managed Kubernetes service from cloud providers such as Google Kubernetes Engine (GKE), Amazon Elastic Kubernetes Service (EKS), or Azure Kubernetes Service (AKS). Ensure that your cluster is properly configured and accessible.

### `kubectl` Command-Line Tool

The `kubectl` command-line tool is essential for interacting with your Kubernetes cluster. If you haven't installed it yet, you can follow the [official installation guide](https://kubernetes.io/docs/tasks/tools/install-kubectl/) to set it up. Once installed, verify that `kubectl` can communicate with your cluster using the following command:

```sh
kubectl cluster-info
```

This command should return information about your cluster, confirming that `kubectl` is correctly configured.

### DataDog Account

To monitor your application's performance, you will need a DataDog account. If you don't already have one, you can sign up for a free trial on the [DataDog website](https://www.datadoghq.com/). Once you have an account, you will need to obtain a DataDog API key. This key will be used to authenticate the DataDog agent that you will deploy in your Kubernetes cluster.

### Python Application Ready for Deployment

Ensure that you have a Python application ready for deployment. This application should be containerized using Docker. If you haven't containerized your application yet, here is a basic example of a `Dockerfile` for a Python application:

```Dockerfile
## Use the official Python image from the Docker Hub
FROM python:3.8-slim

## Set the working directory in the container
WORKDIR /app

## Copy the requirements file into the container
COPY requirements.txt .

## Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

## Copy the rest of the application code into the container
COPY . .

## Command to run the application
CMD ["python", "app.py"]
```

Build the Docker image using the following command:

```sh
docker build -t my-python-app .
```

Push the Docker image to a container registry such as Docker Hub or a private registry that your Kubernetes cluster can access.

### Cluster Authentication and Permissions

Proper authentication mechanisms and permissions are crucial for securely interacting with your Kubernetes cluster. Configure roles and permissions using Kubernetes Role-Based Access Control (RBAC). Define roles and role bindings to ensure that users and services have the appropriate access levels. For example, you can create a role and role binding for deploying your Python application as follows:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: default
  name: deploy-role
rules:
- apiGroups: ["", "apps", "extensions"]
  resources: ["deployments", "pods", "services"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: deploy-role-binding
  namespace: default
subjects:
- kind: User
  name: "your-username"
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: deploy-role
  apiGroup: rbac.authorization.k8s.io
```

Apply these configurations using `kubectl`:

```sh
kubectl apply -f role.yaml
kubectl apply -f rolebinding.yaml
```

### Network Configuration

Proper network configuration is crucial for exposing your application to external traffic. Set up an Ingress controller if you need to manage external access to your services. For example, you can deploy the NGINX Ingress controller using the following command:

```sh
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/cloud/deploy.yaml
```

Ensure that your services are properly configured to use the Ingress controller.

### Resource Limits and Requests

Defining resource requests and limits for your containers helps manage resource allocation and ensures that your application operates efficiently within the cluster. Here is an example of how to specify resource requests and limits in your Kubernetes deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-python-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-python-app
  template:
    metadata:
      labels:
        app: my-python-app
    spec:
      containers:
      - name: my-python-app
        image: my-python-app:latest
        resources:
          requests:
            memory: "64Mi"
            cpu: "250m"
          limits:
            memory: "128Mi"
            cpu: "500m"
```

### DataDog Agent Deployment

Deploying the DataDog agent in your Kubernetes cluster is essential for collecting metrics and monitoring your application's performance. You can deploy the DataDog agent using the official DataDog Helm chart. First, add the DataDog Helm repository:

```sh
helm repo add datadog https://helm.datadoghq.com
helm repo update
```

Then, install the DataDog agent using the following command:

```sh
helm install datadog-agent --set datadog.apiKey=<YOUR_DATADOG_API_KEY> --set datadog.site='datadoghq.com' datadog/datadog
```

Replace `<YOUR_DATADOG_API_KEY>` with your actual DataDog API key.

### Security Best Practices

Adhering to security best practices is crucial for protecting your application and Kubernetes cluster. Use Kubernetes secrets to store sensitive information such as API keys and credentials. Here is an example of how to create a secret for your DataDog API key:

```sh
kubectl create secret generic datadog-api-key --from-literal=api-key=<YOUR_DATADOG_API_KEY>
```

Configure network policies to restrict traffic between pods and ensure that your Docker image is secure by scanning it for vulnerabilities.

By ensuring these prerequisites are met, you'll be well-prepared to proceed with setting up autoscaling with HPA and DataDog metrics for your Python application in a Kubernetes cluster.


## Setting Up Your Python Application in Kubernetes

In this section, we will walk you through the steps to deploy your Python application in a Kubernetes cluster. This includes writing a Dockerfile for your Python app, creating a Kubernetes Deployment YAML file, and applying the deployment to your cluster. We provide sample code and configurations to help you get started quickly.

### Writing a Dockerfile for Your Python App

A Dockerfile is a text document that contains all the commands a user could call on the command line to assemble an image. Here’s an example Dockerfile for a Python application:

```Dockerfile
## Use the official Python base image
FROM python:3.9-slim

## Set the working directory
WORKDIR /app

## Copy the requirements file into the container
COPY requirements.txt .

## Install the required dependencies
RUN pip install --no-cache-dir -r requirements.txt

## Copy the rest of the application code into the container
COPY . .

## Specify the command to run on container start
CMD ["python", "app.py"]
```

This Dockerfile uses the official Python 3.9 slim image, sets the working directory to `/app`, copies the requirements file and installs the dependencies, and finally copies the application code and specifies the command to run the application.

### Creating a Kubernetes Deployment YAML File

A Kubernetes Deployment is a resource object in Kubernetes that provides declarative updates to applications. Here’s an example YAML file for deploying a Python application:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-python-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-python-app
  template:
    metadata:
      labels:
        app: my-python-app
    spec:
      containers:
      - name: my-python-app
        image: my-python-app:latest
        ports:
        - containerPort: 5000
        resources:
          requests:
            memory: "64Mi"
            cpu: "250m"
          limits:
            memory: "128Mi"
            cpu: "500m"
```

This YAML file defines a Deployment named `my-python-app` with 3 replicas. Each Pod will run a container from the `my-python-app:latest` image, exposing port 5000. Resource requests and limits are also specified to manage resource allocation.

### Applying the Deployment to Your Cluster

To apply the Deployment to your Kubernetes cluster, use the `kubectl apply` command:

```sh
kubectl apply -f deployment.yaml
```

This command will create the Deployment and start the specified number of Pods running your Python application.

### Exposing the Deployment with a Service

To make your application accessible from outside the cluster, you need to create a Kubernetes Service. Here’s an example YAML file for a Service:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-python-app-service
spec:
  selector:
    app: my-python-app
  ports:
    - protocol: TCP
      port: 80
      targetPort: 5000
  type: LoadBalancer
```

This Service will expose your application on port 80 and forward traffic to port 5000 on the Pods. To apply the Service, use the `kubectl apply` command:

```sh
kubectl apply -f service.yaml
```

Once the Service is created, it will automatically provision a load balancer (if your cloud provider supports it) and expose your application to the internet.

By following these steps, you’ve successfully deployed your Python application in a Kubernetes cluster. Next, we will cover how to set up autoscaling with Horizontal Pod Autoscaler (HPA) and monitor your application using DataDog metrics.


## Installing and Configuring DataDog

Here, we will cover how to install and configure the DataDog agent in your Kubernetes cluster. This involves creating a DataDog API key, setting up the DataDog Helm chart, and configuring the agent to collect metrics from your Python application. This section will ensure that DataDog is correctly integrated with your Kubernetes cluster for monitoring and metrics collection.

### Step 1: Creating a DataDog API Key

First, you need to create a DataDog API key. This key will be used by the DataDog agent to send metrics to your DataDog account.

1. Log in to your DataDog account.
2. Navigate to **Integrations > APIs**.
3. Click on **Create API Key**.
4. Name your API key and click **Create API Key**.
5. Copy the API key. You will need it for the next steps.

### Step 2: Setting Up the DataDog Helm Chart

Helm is a package manager for Kubernetes that simplifies the deployment of applications and services. We will use Helm to install the DataDog agent.

1. **Add the DataDog Helm repository:**

    ```sh
    helm repo add datadog https://helm.datadoghq.com
    helm repo update
    ```

2. **Create a Kubernetes secret for the DataDog API key:**

    ```sh
    kubectl create secret generic datadog-secret --from-literal api-key=<YOUR_DATADOG_API_KEY>
    ```

3. **Install the DataDog agent using Helm:**

    ```sh
    helm install datadog-agent --set datadog.apiKeyExistingSecret=datadog-secret datadog/datadog
    ```

This command installs the DataDog agent in your Kubernetes cluster using the API key stored in the Kubernetes secret.

### Step 3: Configuring the DataDog Agent

To collect metrics from your Python application, you need to configure the DataDog agent. This involves setting up the `datadog.yaml` configuration file.

1. **Edit the `datadog.yaml` file:**

    ```yaml
    apiVersion: v1
    kind: ConfigMap
    metadata:
      name: datadog-config
      namespace: default
    data:
      datadog.yaml: |-
        api_key: ${DD_API_KEY}
        logs_enabled: true
        logs_config:
          container_collect_all: true
        tags:
          - env:production
        collect_events: true
        kubelet:
          tls_verify: false
    ```

2. **Apply the ConfigMap to your Kubernetes cluster:**

    ```sh
    kubectl apply -f datadog-config.yaml
    ```

This ConfigMap enables log collection and sets up basic configurations for the DataDog agent. You can customize it further based on your requirements.

### Step 4: Verifying the Installation

To verify that the DataDog agent is correctly installed and collecting metrics, follow these steps:

1. **Check the DataDog agent Pods:**

    ```sh
    kubectl get pods -l app=datadog
    ```

2. **Check the logs of a DataDog agent Pod:**

    ```sh
    kubectl logs <DATADOG_AGENT_POD_NAME>
    ```

If the agent is correctly installed, you should see logs indicating that it is collecting metrics and sending them to DataDog.

### Step 5: Custom Metrics Collection

To collect custom metrics from your Python application, you can use the `datadog` Python library. Here’s an example of how to send custom metrics:

1. **Install the `datadog` library:**

    ```sh
    pip install datadog
    ```

2. **Send custom metrics from your Python application:**

    ```python
    from datadog import initialize, statsd

    options = {
        'api_key': 'YOUR_DATADOG_API_KEY',
        'app_key': 'YOUR_DATADOG_APP_KEY'
    }

    initialize(**options)

    # Send a custom metric
    statsd.increment('my_python_app.custom_metric')
    ```

By following these steps, you’ve successfully installed and configured the DataDog agent in your Kubernetes cluster, and you’re now collecting metrics from your Python application.


## Configuring Horizontal Pod Autoscaler (HPA)

In this section, we will delve into setting up the Horizontal Pod Autoscaler (HPA) using the metrics collected by DataDog. We will explain how to create an HPA YAML file, configure it to use custom metrics from DataDog, and apply it to your Kubernetes cluster. Detailed examples and explanations will help you understand how HPA works and how to customize it for your application’s needs.

### Step 6: Creating the HPA YAML File

The Horizontal Pod Autoscaler (HPA) automatically scales the number of pods in a deployment or replica set based on observed CPU utilization or other custom metrics. To use custom metrics from DataDog, you need to configure the HPA to reference these metrics.

1. **Create the HPA YAML file:**

    ```yaml
    apiVersion: autoscaling/v2beta2
    kind: HorizontalPodAutoscaler
    metadata:
      name: my-python-app-hpa
      namespace: default
    spec:
      scaleTargetRef:
        apiVersion: apps/v1
        kind: Deployment
        name: my-python-app
      minReplicas: 2
      maxReplicas: 10
      metrics:
      - type: Pods
        pods:
          metric:
            name: datadog.metric.name
          target:
            type: AverageValue
            averageValue: 100m
    ```

    In this YAML file:
    - `scaleTargetRef` specifies the target deployment for scaling.
    - `minReplicas` and `maxReplicas` define the minimum and maximum number of replicas.
    - The `metrics` section specifies the custom metric from DataDog that will be used to scale the deployment.

### Step 7: Applying the HPA Configuration

Once you have created the HPA YAML file, the next step is to apply it to your Kubernetes cluster.

1. **Apply the HPA configuration:**

    ```sh
    kubectl apply -f my-python-app-hpa.yaml
    ```

    This command will create the HPA resource in your Kubernetes cluster, which will start monitoring the specified custom metric and adjust the number of pods accordingly.

### Step 8: Configuring RBAC for Custom Metrics

To allow the HPA to access custom metrics from DataDog, you need to configure the necessary RBAC (Role-Based Access Control) settings. This involves creating a Role and RoleBinding that grants the required permissions.

1. **Create the RBAC configuration:**

    ```yaml
    apiVersion: rbac.authorization.k8s.io/v1
    kind: Role
    metadata:
      name: hpa-metrics-role
      namespace: default
    rules:
    - apiGroups: ["custom.metrics.k8s.io"]
      resources: ["*"]
      verbs: ["get", "list"]
    ---
    apiVersion: rbac.authorization.k8s.io/v1
    kind: RoleBinding
    metadata:
      name: hpa-metrics-binding
      namespace: default
    subjects:
    - kind: ServiceAccount
      name: default
      namespace: default
    roleRef:
      kind: Role
      name: hpa-metrics-role
      apiGroup: rbac.authorization.k8s.io
    ```

2. **Apply the RBAC configuration:**

    ```sh
    kubectl apply -f hpa-rbac.yaml
    ```

    This configuration ensures that the HPA can access the custom metrics provided by DataDog.

### Step 9: Verifying HPA Configuration

To verify that the HPA is correctly configured and working as expected, follow these steps:

1. **Check the HPA status:**

    ```sh
    kubectl get hpa my-python-app-hpa
    ```

2. **Describe the HPA for detailed information:**

    ```sh
    kubectl describe hpa my-python-app-hpa
    ```

    This command provides detailed information about the HPA, including the current number of replicas, target metrics, and scaling events.

By following these steps, you have successfully set up the Horizontal Pod Autoscaler (HPA) to use custom metrics from DataDog. This configuration allows your Kubernetes cluster to dynamically scale your Python application based on real-time metrics, ensuring optimal performance and resource utilization.


## Monitoring and Testing the Setup

After setting up HPA and DataDog, it's crucial to monitor and test the configuration to ensure everything is working as expected. This section will guide you on how to use DataDog’s dashboard to monitor your application’s performance and autoscaling behavior. We will also discuss how to simulate load on your application to test the autoscaling functionality and ensure that your setup is robust and reliable.

### Step 10: Monitoring with DataDog Dashboard

DataDog provides a comprehensive dashboard that allows you to visualize and monitor your application's performance and the behavior of your HPA configuration. Follow these steps to set up and use the DataDog dashboard:

1. **Create a DataDog Dashboard:**

    - Navigate to the DataDog dashboard and click on the "New Dashboard" button.
    - Name your dashboard appropriately (e.g., "Python App Monitoring").

2. **Add Widgets for Key Metrics:**

    - Add widgets to monitor key metrics such as CPU usage, memory usage, and custom metrics from your Python application.
    - For example, to monitor CPU usage, add a "Timeseries" widget and select the CPU metric (e.g., `system.cpu.user`).

3. **Configure Autoscaling Metrics:**

    - Add widgets to monitor the metrics used for autoscaling. This includes the custom metric specified in your HPA configuration (e.g., `datadog.metric.name`).
    - Ensure that the widgets are set to display real-time data to observe the autoscaling behavior.

4. **Set Up Alerts:**

    - Configure alerts for critical metrics to receive notifications when certain thresholds are exceeded.
    - For example, set an alert for CPU usage exceeding 80% to proactively manage resource utilization.


### Step 11: Simulating Load to Test Autoscaling

To ensure that your HPA configuration and DataDog integration are working correctly, you need to simulate load on your application and observe the autoscaling behavior. Here's how you can do it:

1. **Install Load Testing Tool:**

    - Use a load testing tool like Locust to generate traffic and simulate user behavior.
    - Install Locust using pip:

    ```sh
    pip install locust
    ```

2. **Create a Locustfile:**

    - Create a `locustfile.py` that defines the behavior of your simulated users. Here is an example:

    ```python
    from locust import HttpUser, TaskSet, task, between

    class UserBehavior(TaskSet):
        @task(1)
        def index(self):
            self.client.get("/")

        @task(2)
        def predict(self):
            self.client.post("/predict", json={"data": "sample data"})

    class WebsiteUser(HttpUser):
        tasks = [UserBehavior]
        wait_time = between(1, 5)
    ```

3. **Run Locust:**

    - Start Locust to begin the load test:

    ```sh
    locust -f locustfile.py --host=http://your-python-app-url
    ```

    - Access the Locust web interface (by default at `http://localhost:8089`) to start the test and specify the number of users and spawn rate.

4. **Monitor Autoscaling Behavior:**

    - While the load test is running, monitor the DataDog dashboard to observe the metrics and the behavior of the HPA.
    - Check if the number of replicas increases as the load increases and decreases when the load is reduced.

5. **Verify Scaling Events:**

    - Use the following command to check the scaling events and ensure that the HPA is scaling the pods as expected:

    ```sh
    kubectl describe hpa my-python-app-hpa
    ```

    - Look for events indicating that the HPA has scaled the number of pods up or down based on the custom metric.

By following these steps, you can effectively monitor and test your HPA and DataDog setup. This ensures that your Python application can handle varying loads and maintain optimal performance through dynamic scaling.


## Conclusion

In this blog post, we have taken a comprehensive journey through setting up autoscaling with Horizontal Pod Autoscaler (HPA) and integrating DataDog metrics for a Python application running in a Kubernetes cluster. Let's recap the key points covered:

1. **Understanding HPA and Metrics**: We started by exploring the fundamental concepts of HPA, including its role in dynamically adjusting the number of pod replicas based on observed metrics such as CPU usage. We also delved into the various metrics that HPA can leverage, including custom application metrics and external metrics.

2. **Setting Up HPA**: We provided a step-by-step guide on configuring HPA for a Python application. This included creating the necessary Kubernetes resources, such as Deployment and Service objects, and defining the HPA configuration using a YAML file.

3. **Integrating DataDog**: We walked through the process of integrating DataDog with your Kubernetes cluster. This covered installing the DataDog agent, configuring it to collect metrics, and setting up the DataDog API and Helm chart. We also discussed the importance of managing DataDog secrets securely within Kubernetes.

4. **Creating Custom Metrics**: We demonstrated how to create custom metrics for your Python application and configure HPA to use these metrics for scaling decisions. This included writing and exposing custom metrics using the Prometheus client library for Python.

5. **Monitoring and Visualization**: We set up a DataDog dashboard to visualize key metrics and monitor the autoscaling behavior of your application. This included adding widgets for CPU usage, memory usage, and custom metrics, as well as configuring alerts for critical metrics.

6. **Simulating Load**: To test the HPA configuration and DataDog integration, we used a load testing tool (Locust) to simulate traffic and observe the autoscaling behavior. We monitored the DataDog dashboard and verified the scaling events using Kubernetes commands.

### Best Practices and Tips

To ensure effective management of your Kubernetes workloads with HPA and DataDog metrics, consider the following best practices:

- **Use Multiple Metrics**: Configure HPA to use multiple metrics for more accurate scaling decisions. This can include a combination of CPU usage, memory usage, and custom application metrics.

- **Secure Your Configuration**: Implement security best practices for integrating DataDog with Kubernetes. This includes securing API keys, managing Role-Based Access Control (RBAC) policies, and ensuring secure communication between services.

- **Optimize Performance**: Tune the performance of HPA and DataDog monitoring to minimize overhead and ensure efficient data collection. Optimize polling intervals and reduce monitoring overhead where possible.

- **Regularly Update Configurations**: Regularly review and update your HPA and DataDog configurations to adapt to changing workloads and application requirements. This ensures that your autoscaling and monitoring setup remains effective over time.

By following these best practices and leveraging the capabilities of HPA and DataDog, you can maintain the performance and reliability of your Python applications running in Kubernetes. Autoscaling and monitoring are crucial for handling varying loads and ensuring that your applications can scale dynamically to meet user demands.

