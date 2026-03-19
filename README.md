# Streamlit CMS Usage Instructions

## Streamlit GUI Overview
The Streamlit GUI provides an interface for users to interact with the CMS. It features various components that allow for easy navigation and content management. You'll find:
- A sidebar for selecting different content types.
- A main area that displays the content and allows for editing.

## Step-by-Step Workflow
1. **Log into the Streamlit CMS:** Use your credentials to access the dashboard.
2. **Select Content Type:** From the sidebar, choose the type of content you want to create or edit.
3. **Create/Edit Content:** Fill in the necessary fields and use the provided tools to format your content.
4. **Save Changes:** Once you're done, make sure to save your changes using the save button. You can also preview the content before publishing.

## Deployment Instructions
To deploy the Streamlit application to Cloud Run:
1. **Install Google Cloud SDK** if you haven't already.
2. **Dockerize your Streamlit app:** Create a Dockerfile that specifies the environment and dependencies.
3. **Build your container:** Run the command:  `gcloud builds submit --tag gcr.io/YOUR_PROJECT/YOUR_IMAGE`
4. **Deploy to Cloud Run:** Use the command: `gcloud run deploy --image gcr.io/YOUR_PROJECT/YOUR_IMAGE --platform managed`

## WordPress Publishing
Integrating with WordPress allows you to publish content directly from Streamlit CMS. To set up integration:
1. **Install the WordPress API plugin** on your WordPress site.
2. **Configure API settings** to connect to your Streamlit CMS.
3. **Publish Content:** Use the publish button in the Streamlit GUI to send content to your WordPress site directly.