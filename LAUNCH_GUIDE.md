# FindGolf AI Agent — Launch Guide

This guide walks you through launching the Enthusiast AI platform locally and setting up a FindGolf product agent you can chat with.

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Docker Compose) installed and running
- An OpenAI API key (unrestricted)
- Git (to clone / pull the repo)

---

## Step 1 — Configure Environment

1. Copy the sample env file:
   ```
   cp server/sample.env server/.env
   ```

2. Open `server/.env` and fill in the two required values:

   ```
   ECL_DJANGO_SECRET_KEY=any-long-random-string-you-choose
   OPENAI_API_KEY=sk-proj-your-real-openai-key-here
   ```

   Everything else can stay as-is for local development.

---

## Step 2 — Start the Application

Run all services (database, backend API, background worker, and frontend):

```bash
docker compose -f docker-compose.development.yml up -d --build
```

> The first build takes a few minutes. Subsequent starts are much faster.

Wait ~30 seconds, then verify everything is running:

```bash
docker compose -f docker-compose.development.yml ps
```

You should see 5 services with status **Up**: `postgres`, `redis`, `api`, `worker`, `frontend`.

---

## Step 3 — Open the App

Go to: **http://localhost:10001**

Log in with:
- **Email:** `admin@example.com`
- **Password:** `anas@1234`

> These credentials are set in `server/.env` (`ECL_ADMIN_EMAIL` / `ECL_ADMIN_PASSWORD`).

---

## Step 4 — Create the FindGolf Data Set

1. Click **Data Sets** in the left sidebar
2. Click **New Data Set** (top right)
3. Fill in:
   - **Name:** `FindGolf`
   - Leave all other settings as defaults (OpenAI / gpt-4o / text-embedding-3-large)
4. Click **Save**

---

## Step 5 — Add the FindGolf Product Source

1. Click on the **FindGolf** data set you just created
2. Click the **Sources** tab
3. Click **Add source** → select **Product source** from the dropdown
4. In the modal, select **Custom Product Source** from the plugin list
5. Click **Save**

You should now see "Custom Product Source" listed under sources.

---

## Step 6 — Sync the Products

1. Still on the Sources tab, find the **Custom Product Source** row
2. Click the **sync icon** (circular arrows) on the right side of that row
3. Wait ~15–30 seconds for the sync to complete

To verify the sync worked:
- Click the **Products** tab — you should see ~89 FindGolf products listed.

---

## Step 7 — Create a FindGolf Agent

1. Click the **Agents** tab within the FindGolf data set
2. Click **New Agent**
3. Fill in:
   - **Name:** `FindGolf Assistant` (or any name you like)
   - **Description / System prompt:** something like:
     > You are a helpful golf product assistant. Answer questions about FindGolf products based on the product catalog.
4. Click **Save**

---

## Step 8 — Chat with the Agent

1. Click on the **FindGolf Assistant** agent
2. Click **New Conversation**
3. Ask questions about golf products, for example:
   - *"What golf bags do you have?"*
   - *"Show me products under $50"*
   - *"What's the best golf ball for beginners?"*
   - *"Tell me about the BallBoon"*

The agent answers using only FindGolf product data — it will not mix in data from other data sets.

---

## Stopping the Application

```bash
docker compose -f docker-compose.development.yml down
```

To also remove stored data (full reset):

```bash
docker compose -f docker-compose.development.yml down -v
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Services not starting | Run `docker compose -f docker-compose.development.yml logs api` to check errors |
| Sync shows no products | Check worker logs: `docker compose -f docker-compose.development.yml logs worker` |
| OpenAI errors in chat | Verify `OPENAI_API_KEY` in `server/.env` is valid and unrestricted |
| Frontend shows blank / errors | Check `docker compose -f docker-compose.development.yml logs frontend` |
| Port already in use | Make sure nothing else is running on ports 10000, 10001, or 5433 |
