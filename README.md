# truproxy_databricks

## Setup & Deployment

Follow these steps to deploy the TruProxy app on Databricks.

### 1. Create a Git folder in Databricks
In the Databricks workspace, navigate to your user folder and create a new **Git folder**. This will host the source code synced from GitHub.

### 2. Pull the `truproxy_databricks` repo
Connect the Git folder to this repository (`truproxy_databricks`) and pull the latest `main` branch so the workspace has the full source code.

### 3. Create a Databricks App with minimal settings
In the Databricks workspace, go to **Apps → Create app** and choose the minimal/blank template. Give the app a name and skip any optional integrations for now.

### 4. Point the app to the Git folder as source code
During app configuration, set the **source code path** to the Git folder created in step 1. This makes the app deploy directly from the synced repo.

### 5. Deploy the Databricks App
Trigger the deployment from the app page. Databricks will build and start the app using the source code from the Git folder.

### 6. Open the Databricks App
Once the deployment status is `Running`, open the app URL provided in the Databricks UI.

### 7. Insert your PAT token
On first launch, the app opens to the **Settings** view. Paste a valid Databricks **Personal Access Token (PAT)** and save.

---

App is ready for use.
