# LLM AI Scheduler — FAQ & Guide

## What is the LLM AI Scheduler?

The LLM AI Scheduler is a demo service that suggests appointment slots. You can describe your availability in plain English, and it uses AI to parse your text and recommend the best times.

## How do I describe my availability?

You can use free text like: "Dr. Smith is available Monday through Friday, 9am to 5pm Eastern. Patient prefers mornings. Looking between Feb 3 and Feb 10, 2025."

Include: provider hours, timezone, preferred days or times, date range, and any existing appointments to avoid.

## What timezone formats are supported?

Use IANA timezone names, for example: America/New_York, America/Los_Angeles, Europe/London, UTC. The scheduler handles timezone conversion automatically.

## What are slot length and buffer?

- **Slot length** (default 30 minutes): How long each appointment lasts.
- **Buffer** (default 10 minutes): Gap required between appointments. If you have a meeting at 10:00–10:30, the next slot cannot start before 10:40.

## Do I need an API key?

Yes. Set OPENAI_API_KEY in your environment. The service uses OpenAI (or compatible) models to parse free text and generate slot explanations.

## Can I use structured JSON instead of free text?

Yes. Switch to the "Structured JSON" tab and paste a JSON object with provider_id, timezone, business_hours, date_range, existing_appointments, and optional preferred_days and preferred_times.

## How many slots does it return?

The scheduler returns the top 5 available slots that fit your constraints. Each slot includes an AI-generated explanation of why it was chosen.
