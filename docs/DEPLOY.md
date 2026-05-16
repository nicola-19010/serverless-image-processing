# Deploying your Lambda to AWS

This guide assumes you've completed `SETUP.md` and tested your Lambda locally.

---

## Step 1 — Start the Learner Lab

1. Open AWS Academy in your browser.
2. Go to the **AWS Academy Learner Lab** course.
3. Click **Launch AWS Academy Learner Lab**.
4. Press **Start Lab**. Wait until the status dot turns **green** (1–2 min).
5. Click the **AWS** link at the top. The AWS Console opens.

**Important:** when you finish working, press **End Lab** in the Vocareum window. Your work persists; the timer stops.

---

## Step 2 — Create the Lambda function

In the AWS Console:

1. Top search bar → type **Lambda** → click the service.
2. Click **Create function**.
3. Choose **Author from scratch**.
4. **Function name:** use one of these exactly (case-sensitive matters for the grader script):
   - `resize-fn` (Nico)
   - `grayscale-fn` (Prajwal)
   - `edge-fn` (Mathias)
5. **Runtime:** Python 3.11
6. **Architecture:** x86_64
7. Leave the rest at defaults. Click **Create function**.

---

## Step 3 — Paste your code

1. In the function page, scroll down to **Code source**.
2. Open the file `lambdas\<your-operation>\lambda_function.py` from the repo.
3. Copy the entire content. Paste it over what's in the editor.
4. Press **Deploy** (top right of the code editor). Wait for "Successfully deployed".

---

## Step 4 — Add the Pillow Layer

Lambda's base Python 3.11 image doesn't include Pillow. Instead of zipping it ourselves, we use a public layer maintained by the Klayers project.

1. In your function page, scroll down to **Layers**.
2. Click **Add a layer**.
3. Choose **Specify an ARN**.
4. Paste:

```
arn:aws:lambda:us-east-1:770693421928:layer:Klayers-p311-Pillow:7
```

5. Click **Verify**, then **Add**.

> If the ARN above doesn't work, look up the latest version here: https://api.klayers.cloud/api/v2/p3.11/layers/latest/us-east-1/json — find the `Pillow` entry and copy its `arn` field.

---

## Step 5 — Increase memory and timeout

The default 128 MB and 3 sec are too low for image processing.

1. Click the **Configuration** tab → **General configuration** → **Edit**.
2. **Memory:** 512 MB
3. **Timeout:** 30 sec
4. **Save**.

---

## Step 6 — Test from the console

1. Click the **Test** tab.
2. Event name: `test-medium-image`.
3. **Event JSON:** paste the contents of `lambdas\<your-operation>\test_event.json`.
4. Click **Save**.
5. Click **Test**. After a few seconds you should see "Execution result: succeeded" with a `statusCode: 200` and a `body` containing the processed image as base64.

If it fails, check CloudWatch Logs (link in the result panel) and read the error.

---

## Step 7 — Add the API Gateway trigger

1. In your function page, click **Add trigger**.
2. **Source:** API Gateway.
3. **Intent:** Create a new API.
4. **API type:** **HTTP API** (not REST — HTTP API is cheaper and faster).
5. **Security:** Open (we won't use auth for the load tests).
6. Click **Add**.
7. AWS creates the API and shows you a **public URL** at the top of the trigger panel, something like `https://abc123xyz.execute-api.us-east-1.amazonaws.com/default/<your-fn-name>`.
8. **Copy this URL** — you need it for Postman and Locust.

---

## Step 8 — Send the URL to the team

In the group chat, share your URL using this format:

```
RESIZE_URL = https://abc123.execute-api.us-east-1.amazonaws.com/default/resize-fn
GRAYSCALE_URL = https://def456.execute-api.us-east-1.amazonaws.com/default/grayscale-fn
EDGE_URL = https://ghi789.execute-api.us-east-1.amazonaws.com/default/edge-fn
```

---

## Step 9 — Verify CloudWatch is logging

1. After running a few test invocations, go to the **Monitor** tab in your Lambda function.
2. You should see graphs for **Invocations**, **Duration**, **Error rate**, **Throttles**, **Concurrent executions**.
3. Click **View logs in CloudWatch** to see per-invocation logs. Each invocation shows REPORT lines with Duration, Billed Duration, Memory Used, and (for cold starts) Init Duration.

If you see no metrics, run a few more test invocations and refresh.

---

## Common issues

**"No module named 'PIL'"** → the Pillow Layer wasn't attached, or the ARN is wrong. Re-check Step 4.

**Timeout errors on large images** → bump memory to 1024 MB and timeout to 60 sec.

**Permission denied / IAM errors** → the Learner Lab provides a default execution role. Don't try to create a new one (IAM creation is blocked). Use the auto-generated role.

**API Gateway URL returns "Forbidden"** → make sure the integration is deployed. In the API Gateway console, click your API → check that there's a deployed stage.

---

## Next step

Once your URL works, go to `TESTING.md` to run Postman + Locust against it.
