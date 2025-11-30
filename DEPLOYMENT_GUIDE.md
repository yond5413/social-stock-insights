# Deployment Guide: Connecting Vercel Frontend to Render Backend

This guide explains how to connect your Vercel deployment (Frontend) with your Render deployment (Backend).

## 1. Backend Configuration (Render)

You need to tell the backend to accept requests from your Vercel frontend.

1.  Go to your **Render Dashboard**.
2.  Select your **Web Service** (the FastAPI backend).
3.  Go to **Environment**.
4.  Add a new Environment Variable:
    *   **Key**: `ALLOWED_ORIGINS`
    *   **Value**: Your Vercel deployment URL (e.g., `https://social-stock-insights.vercel.app`).
        *   *Note: If you have multiple domains (e.g., a custom domain and a vercel.app domain), you can separate them with commas: `https://social-stock-insights.vercel.app,https://your-custom-domain.com`*
5.  **Save Changes**. Render will automatically redeploy your service.

## 2. Frontend Configuration (Vercel)

You need to tell the frontend where to find the backend API.

1.  Go to your **Vercel Dashboard**.
2.  Select your **Project** (social-stocks-insights).
3.  Go to **Settings** > **Environment Variables**.
4.  Add a new Environment Variable:
    *   **Key**: `NEXT_PUBLIC_API_BASE_URL`
    *   **Value**: `https://social-stock-insights.onrender.com`
        *   *Note: Do not include a trailing slash.*
5.  **Save**.
6.  **Redeploy** your frontend for the changes to take effect. You can do this by going to **Deployments**, clicking the three dots on the latest deployment, and selecting **Redeploy**.

## 3. Verification

Once both services are redeployed:

1.  Open your Vercel app in the browser.
2.  Open the Developer Tools (F12) and go to the **Network** tab.
3.  Refresh the page.
4.  You should see requests going to `https://social-stock-insights.onrender.com/...`.
5.  If you see CORS errors in the console, double-check that the `ALLOWED_ORIGINS` in Render exactly matches the URL you are visiting (including `https://` and no trailing slash).

## Troubleshooting

*   **CORS Errors**: Ensure `ALLOWED_ORIGINS` in Render matches your Vercel URL exactly.
*   **Connection Refused**: Ensure the Render service is active and healthy (check the `/health` endpoint).
*   **Mixed Content**: Ensure both are using HTTPS.
