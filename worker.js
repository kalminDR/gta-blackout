/**
 * Grand Theft Attention — collection endpoint.
 *
 *   POST /report   a reader says what they plan to do on 19 November
 *   GET  /counts   the running tally
 *   POST /signup   an email address for the two planned emails
 *
 * Three decisions worth keeping, each of which replaced a worse one:
 *
 * 1. Abuse is handled by Cloudflare Turnstile at the edge, not by storing
 *    a hash of the visitor's address. An earlier version hashed the IP to
 *    stop repeat votes, which quietly contradicted the claim that nothing
 *    personal is stored: a salted IP hash is still derived from an
 *    identifier, and we would have held the salt. Turnstile needs us to
 *    store nothing at all.
 *
 * 2. /counts reads four rows from an aggregate table. It never counts the
 *    reports table. From 1 September 2026 Cloudflare enforces the D1 free
 *    row limits as hard errors, so a full scan per page view would take
 *    the site down on exactly the day it mattered.
 *
 * 3. /counts is cached at the edge for a minute, and the site normally
 *    reads an hourly snapshot committed by the collector rather than
 *    calling here at all. The Workers free plan allows 100,000 requests a
 *    day; a single press mention could spend that on page views alone.
 */

const ANSWERS = {
  day_off:        "Taking the day off",
  sick:           "Calling in sick",
  in_not_working: "Going in, not expecting to get much done",
  working:        "Working normally",
};

const INDUSTRIES = [
  "technology", "finance", "healthcare", "education", "government",
  "retail", "manufacturing", "media", "logistics", "hospitality",
  "construction", "professional_services", "student", "other",
];

const ALLOWED_ORIGINS = [
  "https://grandtheftattention.com",
  "https://www.grandtheftattention.com",
  "https://attentionheist.com",
  "https://kalmindr.github.io",
  "http://localhost:8000",
  "http://127.0.0.1:8000",
];

const NOTE = "Self-selected count of people who chose to answer. " +
             "Not a representative survey.";

function cors(origin) {
  const allow = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
  return {
    "Access-Control-Allow-Origin": allow,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
  };
}

function json(body, status, origin, cacheSeconds) {
  const headers = { "Content-Type": "application/json", ...cors(origin) };
  if (cacheSeconds) headers["Cache-Control"] = `public, max-age=${cacheSeconds}`;
  return new Response(JSON.stringify(body), { status: status || 200, headers });
}

async function readJson(request) {
  try {
    const body = await request.json();
    return (body && typeof body === "object") ? body : {};
  } catch {
    return {};
  }
}

/** Cloudflare Turnstile. Verification happens at the edge; we store nothing. */
async function passesTurnstile(token, secret, request) {
  if (!token) return false;
  const form = new FormData();
  form.append("secret", secret);
  form.append("response", token);
  // Turnstile wants the address to bind the token to the challenge. It is
  // sent to Cloudflare for that check and never written to our database.
  const ip = request.headers.get("CF-Connecting-IP");
  if (ip) form.append("remoteip", ip);

  const res = await fetch(
    "https://challenges.cloudflare.com/turnstile/v0/siteverify",
    { method: "POST", body: form }
  );
  const out = await res.json();
  return out.success === true;
}

// ------------------------------------------------------------------ counts

async function tally(env) {
  // Four rows by primary key. Never a scan of the reports table.
  const { results } = await env.DB
    .prepare("SELECT answer, n FROM tallies").all();

  const answers = {};
  Object.keys(ANSWERS).forEach((k) => { answers[k] = 0; });
  let total = 0;
  for (const row of results || []) {
    if (Object.prototype.hasOwnProperty.call(answers, row.answer)) {
      answers[row.answer] = row.n;
      total += row.n;
    }
  }

  // Shares matter as much as counts: "31% say they will work normally" is
  // an observation, whereas a raw number of absentees is just a headline.
  const share = {};
  Object.keys(answers).forEach((k) => {
    share[k] = total ? Math.round((answers[k] / total) * 1000) / 10 : null;
  });

  return { total, answers, share, labels: ANSWERS, note: NOTE };
}

// ------------------------------------------------------------------ report

async function handleReport(request, env, origin) {
  if (!env.TURNSTILE_SECRET) {
    // Fail closed. An unprotected endpoint would let one person invent the
    // result, and this is the only data we gather ourselves.
    return json({ error: "not accepting responses yet" }, 503, origin);
  }

  const body = await readJson(request);

  const answer = String(body.answer || "");
  if (!Object.prototype.hasOwnProperty.call(ANSWERS, answer)) {
    return json({ error: "unknown answer" }, 400, origin);
  }

  if (!await passesTurnstile(body.token, env.TURNSTILE_SECRET, request)) {
    return json({ error: "could not verify that you are a person" }, 403, origin);
  }

  // Two letters or nothing; anything else is dropped rather than stored.
  let country = String(body.country || "").trim().toUpperCase();
  if (!/^[A-Z]{2}$/.test(country)) country = null;

  let industry = String(body.industry || "").trim().toLowerCase();
  if (INDUSTRIES.indexOf(industry) === -1) industry = null;

  await env.DB.batch([
    env.DB.prepare(
      "INSERT INTO reports (answer, country, industry, submitted_at) VALUES (?, ?, ?, ?)"
    ).bind(answer, country, industry, new Date().toISOString()),
    env.DB.prepare("UPDATE tallies SET n = n + 1 WHERE answer = ?").bind(answer),
  ]);

  // Returned fresh so the person who just answered sees their own response
  // land. Everyone else reads the hourly snapshot from the static site.
  return json({ ok: true, counts: await tally(env) }, 200, origin);
}

// ------------------------------------------------------------------ signup

async function handleSignup(request, env, origin) {
  if (!env.TURNSTILE_SECRET) {
    return json({ error: "not accepting signups yet" }, 503, origin);
  }

  const body = await readJson(request);
  const email = String(body.email || "").trim().toLowerCase();

  if (email.length > 254 || !/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(email)) {
    return json({ error: "that does not look like an email address" }, 400, origin);
  }
  if (!await passesTurnstile(body.token, env.TURNSTILE_SECRET, request)) {
    return json({ error: "could not verify that you are a person" }, 403, origin);
  }

  await env.DB.prepare(
    "INSERT INTO subscribers (email, submitted_at) VALUES (?, ?) " +
    "ON CONFLICT(email) DO NOTHING"
  ).bind(email, new Date().toISOString()).run();

  return json({ ok: true }, 200, origin);
}

// ------------------------------------------------------------------- router

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const { pathname } = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors(origin) });
    }

    try {
      if (pathname === "/counts" && request.method === "GET") {
        // A minute of edge caching turns a burst of page views into one
        // origin hit, which is the difference between surviving a press
        // mention and spending the daily quota before lunch.
        return json(await tally(env), 200, origin, 60);
      }
      if (pathname === "/report" && request.method === "POST") {
        return handleReport(request, env, origin);
      }
      if (pathname === "/signup" && request.method === "POST") {
        return handleSignup(request, env, origin);
      }
      return json({ error: "not found" }, 404, origin);
    } catch (err) {
      console.error(err);
      return json({ error: "something went wrong" }, 500, origin);
    }
  },
};
