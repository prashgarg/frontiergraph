# Public Beta Launch Plan

This repo now includes the assets for a two-surface launch:

- `www`: a static public site from [site/index.html](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/site/index.html)
- `app`: the Streamlit ranker packaged for Cloud Run with a mounted read-only economics database

## Recommended Stage 1

Use this exact split:

- `frontiergraph.com` on Cloudflare Pages
- the app on Google Cloud Run at its default `run.app` URL first
- a Google Cloud Storage bucket mounted read-only into Cloud Run for `app_causalclaims.db`

This is the fastest low-ops public beta. It avoids adding a load balancer before you know the product shape.

## Why This Structure

- The landing page and the tool should evolve independently.
- Cloudflare Pages is cheap and simple for a static site.
- Cloud Run scales the app only when users are active.
- The economics SQLite database is currently about `2.3G`, so it is better mounted from Cloud Storage than baked into the image.
- The app is read-only, so SQLite is acceptable for the first public beta.

## Most Automated Workflow

The most automated sane workflow is:

1. Put this repo in GitHub.
2. Connect `site/` to Cloudflare Pages using Git integration.
3. Connect the same repo to Google Cloud Build.
4. Create a Cloud Build trigger on pushes to `main`.
5. Let Cloud Build build the image from [cloudbuild.yaml](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/cloudbuild.yaml) and redeploy Cloud Run automatically.

After that, one push to `main` updates:

- the public site on Cloudflare Pages
- the app on Cloud Run

Only the domain purchase and the first cloud connections are manual.

## Repo Assets Added

- [Dockerfile](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/Dockerfile)
- [cloudbuild.yaml](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/cloudbuild.yaml)
- [.dockerignore](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/.dockerignore)
- [.gcloudignore](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/.gcloudignore)
- [scripts/deploy_cloud_run.sh](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/scripts/deploy_cloud_run.sh)
- [scripts/upload_ranker_db_to_gcs.sh](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/scripts/upload_ranker_db_to_gcs.sh)
- [deploy/public_beta.env.example](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/deploy/public_beta.env.example)
- [site/index.html](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/site/index.html)
- [site/styles.css](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/site/styles.css)
- [site/config.js](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/site/config.js)

## Setup Steps

### 1. Create the Google Cloud project

Enable billing, then enable the required services:

- Cloud Run
- Cloud Build
- Artifact Registry
- Cloud Storage

### 2. Create a storage bucket for the economics DB

The easiest pattern is one bucket with one main object:

- bucket: `gs://your-ranker-data-bucket`
- object: `app_causalclaims.db`

Upload the current database:

```bash
scripts/upload_ranker_db_to_gcs.sh
```

Or explicitly:

```bash
scripts/upload_ranker_db_to_gcs.sh data/processed/app_causalclaims.db your-ranker-data-bucket app_causalclaims.db
```

### 3. Fill in the deployment env file

Copy [deploy/public_beta.env.example](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/deploy/public_beta.env.example) to `deploy/public_beta.env` and set:

- `PROJECT_ID`
- `REGION`
- `SERVICE_NAME`
- `DATA_BUCKET`

The default sizing in the template is a sane starting point for beta:

- `CPU=2`
- `MEMORY=4Gi`
- `CONCURRENCY=4`
- `MIN_INSTANCES=0`

### 4. Deploy the app

You now have two choices.

#### Option A: one-time manual deploy

```bash
scripts/deploy_cloud_run.sh
```

This is useful for a first smoke test.

#### Option B: continuous deployment from GitHub

```bash
# Create a Cloud Build trigger that points at this repo and uses cloudbuild.yaml.
```

Cloud Build officially supports repository event triggers for GitHub pushes and pull requests. The trigger should:

- watch the `main` branch
- use [cloudbuild.yaml](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/cloudbuild.yaml)
- set trigger substitutions for at least:
  - `_REGION`
  - `_SERVICE_NAME`
  - `_DATA_BUCKET`

What the automated pipeline does:

- enables required Google APIs
- creates the Artifact Registry repository if missing
- builds the app image with Cloud Build
- deploys the Cloud Run service
- mounts the Cloud Storage bucket read-only when `DATA_BUCKET` is set
- prints the final `run.app` service URL

If you leave `DATA_BUCKET` blank, the deploy uses the tiny packaged demo DB instead. That is only for smoke tests, not for the public economics beta.

### 5. Publish the landing page

The static site lives in [site](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/site).

Before publishing it:

- edit [site/config.js](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/site/config.js)
- replace the placeholder app URL with your deployed Cloud Run `run.app` URL
- replace the docs and method URLs as needed

Then deploy to Cloudflare Pages by either:

- Git integration if this repo is in GitHub or GitLab
- Direct Upload with drag-and-drop only if you explicitly want a non-automated site deploy

For the most automated workflow, use Git integration.

## Domain Strategy

### Cheapest beta

- map `frontiergraph.com` to Cloudflare Pages
- redirect `www.frontiergraph.com` to `frontiergraph.com`
- keep the app at its Cloud Run `run.app` URL
- link to the app from the landing page

This is the cheapest and fastest path.

### Branded app URL later

When you want `app.yourdomain.com`, do one of these:

- put a Google external Application Load Balancer in front of Cloud Run
- put Firebase Hosting in front of Cloud Run

Cloud Run's direct domain mapping is currently documented by Google as limited-availability preview, so it is not the best long-term production choice.

## Cost Bands

Practical ranges for this architecture:

- `www` on Cloudflare Pages: effectively free at low volume
- domain: usually low double-digits per year
- Cloud Run beta app: often low single digits to low tens per month if `min instances = 0`
- Cloud Storage bucket for the SQLite file: low cost relative to compute

Reasonable first budget:

- `~$10-$25/month` plus domain for a real but low-traffic public beta

## What Changes Later

You should move off the mounted SQLite design when you need:

- user accounts
- saved shortlists
- comments or feedback
- concurrent write traffic
- richer cross-session analytics

That is the point to add PostgreSQL on Cloud SQL and probably move from Streamlit toward a custom frontend plus API.

## What I Still Need From You

To take this live with you, I need:

- the domain you want to use
- a Google Cloud project with billing enabled
- permission to deploy from this machine
- if you want `www` immediately, access to the Cloudflare account or a Pages project

Once you have that, I can do the actual deployment steps rather than just preparing the repo.
