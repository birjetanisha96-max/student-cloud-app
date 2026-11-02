# Student Information System — Amazon EKS GitOps Project

A small Flask web application demonstrating an end-to-end cloud-native deployment workflow using EC2, Docker, Amazon ECR, Amazon EKS, GitHub Actions OIDC, and Argo CD.

## Features

- Add student records (name and course)
- View student records
- Delete student records
- Health-check endpoint at `/health`
- Responsive browser interface
- Automated unit tests

## Architecture

Developer → GitHub → GitHub Actions → Docker image → Amazon ECR → updated Kubernetes manifest in Git → Argo CD → Amazon EKS → LoadBalancer Service

## Repository layout

```text
.
├── app.py
├── requirements.txt
├── test_app.py
├── Dockerfile
├── .dockerignore
├── .gitignore
├── k8s/
│   └── deployment.yaml
├── argocd/
│   └── application.yaml
└── .github/workflows/
    └── ci-cd.yml
```

## 1. Run locally

Requires Python 3.12+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest -v
python -m flask --app app run --host 0.0.0.0 --port 5000
```

Open `http://localhost:5000`.

## 2. Build and test Docker image

```bash
docker build -t student-app:local .
docker run --rm -p 5000:5000 student-app:local
```

In another terminal:

```bash
curl http://localhost:5000/health
```

## 3. AWS prerequisites

Use an AWS region consistently (example: `ap-south-1`). The AWS identity used to create infrastructure needs appropriately scoped permissions. Prefer an EC2 instance profile over long-lived AWS access keys.

Set variables in your EC2 shell:

```bash
export AWS_REGION=ap-south-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ECR_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/student-app"
```

Create the private ECR repository:

```bash
aws ecr create-repository --repository-name student-app --region "$AWS_REGION"
```

If it already exists, continue. Login, build, tag and push a bootstrap image:

```bash
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
docker build -t student-app:bootstrap .
docker tag student-app:bootstrap "${ECR_REPO}:bootstrap"
docker push "${ECR_REPO}:bootstrap"
```

## 4. Prepare Kubernetes manifest

Replace the placeholders in `k8s/deployment.yaml`:

- `ACCOUNT_ID` with your 12-digit AWS account ID
- `AWS_REGION` with your region, e.g. `ap-south-1`

Then deploy:

```bash
kubectl apply -f k8s/
kubectl rollout status deployment/student-app
kubectl get pods
kubectl get svc student-app-service
```

The worker-node IAM role (or Fargate pod execution role, as applicable) must be allowed to pull the private ECR image. The `LoadBalancer` Service provisions cloud networking resources and can incur charges.

## 5. GitHub Actions OIDC configuration

Create the GitHub OIDC identity provider in IAM if it does not exist:

- Provider URL: `https://token.actions.githubusercontent.com`
- Audience: `sts.amazonaws.com`

Create an IAM role trusted by that provider. Restrict its trust policy to your exact repository and branch:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
        "token.actions.githubusercontent.com:sub": "repo:YOUR_GITHUB_USERNAME/student-cloud-app:ref:refs/heads/main"
      }
    }
  }]
}
```

Attach an IAM permissions policy allowing:
- `ecr:GetAuthorizationToken` on `*`
- `ecr:BatchCheckLayerAvailability`
- `ecr:InitiateLayerUpload`
- `ecr:UploadLayerPart`
- `ecr:CompleteLayerUpload`
- `ecr:PutImage`

Scope repository-specific actions to `arn:aws:ecr:REGION:ACCOUNT_ID:repository/student-app`.

Add these **GitHub Actions repository variables** (Settings → Secrets and variables → Actions → Variables):

| Name | Value |
|---|---|
| `AWS_REGION` | Your AWS region |
| `AWS_ACCOUNT_ID` | Your 12-digit AWS account ID |
| `AWS_ROLE_ARN` | ARN of the GitHub Actions IAM role |

Do not store long-lived AWS access keys in GitHub.

In GitHub Settings → Actions → General → Workflow permissions, allow read and write permissions so the workflow can commit the updated deployment manifest. Branch protection must also permit this bot commit.

## 6. GitOps with Argo CD

Install Argo CD into the cluster if it is not already installed:

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl get pods -n argocd
```

Edit `argocd/application.yaml` and replace `YOUR_GITHUB_USERNAME` with your GitHub username. For a public GitHub repository, apply it:

```bash
kubectl apply -f argocd/application.yaml
kubectl get applications -n argocd
```

For a private repository, configure repository credentials in Argo CD before creating the Application.

Access the UI locally with port forwarding:

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Use a secure SSH tunnel from your laptop to the EC2 host if needed, then browse to `https://localhost:8080`. Retrieve the initial password:

```bash
kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath="{.data.password}" | base64 -d; echo
```

Login as `admin`, then change the initial password.

## 7. Demonstrate automated deployment

Change a visible heading in `app.py`, then:

```bash
git add app.py
git commit -m "Update application heading"
git push origin main
```

GitHub Actions runs tests, builds and pushes an image tagged with the source commit SHA, then commits the new image URI into `k8s/deployment.yaml`. Argo CD detects the Git change and synchronizes EKS.

Verify:

```bash
kubectl rollout status deployment/student-app
kubectl get pods
kubectl get deployment student-app -o jsonpath='{.spec.template.spec.containers[0].image}'; echo
kubectl get svc student-app-service
```

Open the external hostname shown by the Service.

## Important limitations and production notes

- This teaching application stores records in process memory. Data is lost when a Pod restarts and replicas do not share data. Use a database (such as RDS or DynamoDB) for persistent production data.
- A public `LoadBalancer` Service creates billable AWS resources. Restrict access or use an approved ingress/load-balancer design for production.
- The EKS worker-node role needs ECR pull access. GitHub's OIDC role is for publishing images and does not automatically grant EKS nodes image-pull permission.
- Pin GitHub Actions to reviewed commit SHAs for production supply-chain security.
- Use least-privilege IAM, secure Argo CD credentials, and TLS for production.

## Cleanup

After your instructor verifies the assignment, remove resources you created and no longer need. Deleting an EKS cluster does not always remove every separately provisioned resource. Check EC2, EKS, ECR, Load Balancers, NAT Gateways, EBS volumes, and the AWS billing console. Do not delete college/shared resources without permission.
