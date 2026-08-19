## Deployment Instructions

## ECR

Use ECR as the private registry for the image built from this GitHub branch. One image is enough for both Compose services: app and nginx use the same image but different commands.
AWS’s flow is: create repository → authenticate Docker → build/tag → push. AWS ECR push documentation

1. Create the ECR repository

Run locally or in AWS CloudShell:

```
export AWS_REGION=eu-west-1
export ECR_REPOSITORY=label-studio-rbac

aws ecr create-repository \
  --repository-name "$ECR_REPOSITORY" \
  --image-scanning-configuration scanOnPush=true
```

Get the registry URL:

```
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity \
  --query Account --output text)

export ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
```

2. Build and push manually
   From the cloned repository and desired branch:

```
git checkout feat/rbac
git pull --ff-only origin feat/rbac

export IMAGE_TAG=$(git rev-parse HEAD)

aws ecr get-login-password --region "$AWS_REGION" | \
  docker login \
  --username AWS \
  --password-stdin "$ECR_REGISTRY"

docker build \
  --platform linux/amd64 \
  -t "$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" \
  .

docker push "$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG"
```

The image will look like:

```
123456789012.dkr.ecr.eu-west-1.amazonaws.com/label-studio-rbac:582150633...
```

Use the commit SHA as the tag instead of only latest, so every deployment is tied to exact source code.

3. Modify docker-compose.yml
   In both the nginx and app services, replace:

```
build: .
image: heartexlabs/label-studio:latest
```

with:

```
image: ${LABEL_STUDIO_IMAGE}:${LABEL_STUDIO_IMAGE_TAG}
```

The relevant parts become:

```
services:
  nginx:
    image: ${LABEL_STUDIO_IMAGE}:${LABEL_STUDIO_IMAGE_TAG}
    restart: unless-stopped
    ports:
      - "8080:8085"
      - "8081:8086"
    depends_on:
      - app
    # remaining nginx configuration...

  app:
    image: ${LABEL_STUDIO_IMAGE}:${LABEL_STUDIO_IMAGE_TAG}
    restart: unless-stopped
    expose:
      - "8000"
    depends_on:
      - db
    # remaining app configuration...
```

Create .env beside the Compose file on EC2:

```
LABEL_STUDIO_IMAGE=123456789012.dkr.ecr.eu-west-1.amazonaws.com/label-studio-rbac
LABEL_STUDIO_IMAGE_TAG=582150633
LABEL_STUDIO_HOST=http://YOUR_EC2_PUBLIC_IP:8080
POSTGRES_DATA_DIR=/opt/label-studio/postgres-data
```

4. Pull and run the ECR image on EC2
   Attach an IAM role to the EC2 instance with ECR pull permissions, then:

```
aws ecr get-login-password --region eu-west-1 | \
  docker login \
  --username AWS \
  --password-stdin 123456789012.dkr.ecr.eu-west-1.amazonaws.com

cd /opt/label-studio/label-studio

docker compose pull
docker compose up -d --force-recreate
docker compose ps
```

The EC2 role needs at least:

```
ecr:GetAuthorizationToken
ecr:BatchGetImage
ecr:GetDownloadUrlForLayer
ecr:BatchCheckLayerAvailability
```
