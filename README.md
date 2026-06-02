# TruProxy Cost Monitor

Real-time Databricks resource cost monitoring — clusters, pipelines, SQL warehouses, and Apps.

## Requirements

- A Databricks workspace (Premium tier or above)
- Your user account must have **Can View** access on the resources you want to monitor
- No local software installation required

## Installation (~5 minutes)

### Step 1 — Add this repository as a Git Folder

1. In your Databricks workspace, click **Workspace** in the left sidebar.
2. Navigate to your user folder (e.g. `/Users/you@company.com`).
3. Click the **⋮** (kebab) menu → **Add** → **Git folder**.
4. Paste the repository URL: `https://github.com/trupositive-ai/truproxy_databricks`
5. Leave the branch as `main` and click **Create Git folder**.

### Step 2 — Create a new Databricks App

1. In the left sidebar, click **Compute** → **Apps**.
2. Click **Create app**.
3. Choose the **Custom** template (blank).
4. Give the app any name, e.g. `TruProxy`.

### Step 3 — Configure and deploy

1. In the app's **Source code** field, set the path to the Git folder from Step 1
   (e.g. `/Users/you@company.com/truproxy_databricks`).
2. Click **Deploy**. The first deploy takes ~2 minutes as dependencies install.
3. Wait until the status shows **Running**.

> **Note:** If your workspace is not in `EU_WEST`, edit `app.yaml` to set `TRUPROXY_REGION`
> to match your region before deploying (e.g. `US_EAST`, `US_WEST`, `AP_SOUTHEAST`).

### Step 4 — Configure your PAT token

1. Click the app URL to open TruProxy.
2. The app opens to **Settings** automatically.
3. Follow the on-screen instructions to generate a Databricks Personal Access Token.
4. Paste the token and click **Save**.

The app starts monitoring immediately after saving the token.

## Updating

When a new version is released:
1. In your Databricks workspace, open the Git Folder for this repo.
2. Click **Pull** to fetch the latest changes from `main`.
3. Go to **Compute → Apps**, find TruProxy, and click **Redeploy**.

## Troubleshooting

**The app shows "Fetch error" after saving the token**
- Verify the token starts with `dapi`. Copy it again from Databricks — tokens are shown only once.
- Check that the token has not expired: Databricks workspace → user avatar → **Settings** → **Developer** → **Access tokens**.
- Confirm your account has at least **Can View** on clusters, pipelines, and SQL warehouses.

**All costs show as zero / no data appears**
- The default region is `EU_WEST`. If your workspace is in a different region, update `TRUPROXY_REGION` in `app.yaml`, pull, and redeploy.

**The deployment stays in "Deploying" or fails immediately**
- In the App's event log, check for pip install errors — this usually means a dependency conflict.
- Open an issue and paste the deployment log.

**The app shows a red error mentioning `bin/truproxy-core`**
- The binary was not pulled correctly. Open the Git Folder in your workspace, click **Pull**, and redeploy.

## Reporting Issues

Found a bug or have feedback? [Open an issue](https://github.com/trupositive-ai/truproxy_databricks/issues) using the **Bug Report** template.

Please include:
- Your app version (shown in the sidebar footer, e.g. `v0.1.0-beta`)
- The error message or a screenshot
- Your workspace region
