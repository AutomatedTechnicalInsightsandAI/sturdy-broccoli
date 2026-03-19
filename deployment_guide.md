# Deploying sturdy-broccoli to Google Cloud Run

This guide walks you through deploying the sturdy-broccoli Streamlit application
to Google Cloud Run using Docker and Cloud Build.

## Prerequisites

- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed and authenticated
- A GCP project with billing enabled
- The following APIs enabled on your project:
  - Cloud Run API
  - Cloud Build API
  - Artifact Registry API
  - Secret Manager API

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com
```

## 1. Set project variables

```bash
export PROJECT_ID=your-gcp-project-id
export REGION=us-central1
export SERVICE_NAME=sturdy-broccoli
export REPO=sturdy-broccoli
```

## 2. Create an Artifact Registry repository

```bash
gcloud artifacts repositories create $REPO \
  --repository-format=docker \
  --location=$REGION \
  --description="sturdy-broccoli Docker images"
```

## 3. Store the OpenAI API key in Secret Manager

Never commit your API key to source control. Store it as a secret instead:

```bash
echo -n "sk-YOUR_OPENAI_API_KEY" | \
  gcloud secrets create OPENAI_API_KEY \
    --data-file=- \
    --replication-policy=automatic
```

If the secret already exists, add a new version:

```bash
echo -n "sk-YOUR_OPENAI_API_KEY" | \
  gcloud secrets versions add OPENAI_API_KEY --data-file=-
```

## 4. Grant Cloud Build access to the secret

```bash
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

gcloud secrets add-iam-policy-binding OPENAI_API_KEY \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding OPENAI_API_KEY \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## 5. Deploy manually with Cloud Build

From the repository root:

```bash
gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions=_REGION=$REGION,_SERVICE_NAME=$SERVICE_NAME,\
_IMAGE=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/app:manual \
  .
```

### Alternative: deploy using the service definition in app.yaml

First replace `IMAGE_URL` in `app.yaml` with your actual image reference, then run:

```bash
gcloud run services replace app.yaml --region=$REGION
```

This is useful for declarative, version-controlled service configuration.

## 6. Set up automated CI/CD with a Cloud Build trigger

Connect your GitHub repository to Cloud Build and create a push trigger:

```bash
# Create a trigger that fires on every push to the main branch
gcloud builds triggers create github \
  --repo-name=sturdy-broccoli \
  --repo-owner=AutomatedTechnicalInsightsandAI \
  --branch-pattern=^main$ \
  --build-config=cloudbuild.yaml \
  --name=sturdy-broccoli-main \
  --substitutions=_REGION=$REGION,_SERVICE_NAME=$SERVICE_NAME,\
_IMAGE=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/app:\$SHORT_SHA
```

You can also create the trigger through the
[Cloud Build console](https://console.cloud.google.com/cloud-build/triggers).

## 7. Retrieve the deployed URL

After deployment completes, get the service URL:

```bash
gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --format='value(status.url)'
```

Open the printed URL in your browser to access the Streamlit app.

## 8. Local development with Docker

Build and run the container locally to verify it before deploying:

```bash
# Build
docker build -t sturdy-broccoli:local .

# Run (pass your API key as an environment variable)
docker run -p 8080:8080 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  sturdy-broccoli:local
```

Then open [http://localhost:8080](http://localhost:8080) in your browser.

## Environment variables reference

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | For live generation | OpenAI API key. Set via Secret Manager on Cloud Run. |
| `STREAMLIT_SERVER_HEADLESS` | Set by Dockerfile | Disables the browser-open behaviour. |
| `STREAMLIT_BROWSER_GATHER_USAGE_STATS` | Set by Dockerfile | Opts out of Streamlit telemetry. |

## Cost considerations

- Cloud Run is billed per request and per second of CPU/memory usage.
- `min-instances=0` means the service scales to zero when idle (cold-start on first request).
- Increase `min-instances` to 1 if you need instant response times and are willing to pay for idle capacity.

## Troubleshooting

**Container fails to start**
Check Cloud Run logs:
```bash
gcloud run services logs read $SERVICE_NAME --region=$REGION
```

**`OPENAI_API_KEY` not available at runtime**
Confirm the secret is mounted correctly:
```bash
gcloud run services describe $SERVICE_NAME --region=$REGION \
  --format='yaml(spec.template.spec.containers[0].env)'
```

**Port mismatch**
Cloud Run always injects `$PORT=8080`. The `Dockerfile` and `cloudbuild.yaml` both
pass `--server.port=8080` to Streamlit, so this should not be an issue.
