/**
 * Grand Theft Attention — heartbeat.
 *
 * The collector's clock. Once an hour, at five past, this asks GitHub to run
 * the `collect` workflow. It does nothing else and stores nothing.
 *
 * Why it exists
 * -------------
 * The collector used to rely on GitHub's own schedule, "0 * * * *". That
 * scheduler is best-effort, and from 13 September 2026 it started the job
 * only every four to six hours — five or six readings a day instead of
 * twenty-four, for two weeks, with every run reporting success, because the
 * runs that did happen worked perfectly. The hour-of-week baseline stalled, and
 * one published prediction ("four consecutive hourly readings") became
 * impossible to pass for a reason unrelated to the launch.
 *
 * Cloudflare's cron triggers are the dependable clock here. GitHub's schedule
 * stays in collect.yml as a fallback at :37; when this heartbeat has already
 * produced a reading in the hour, the fallback sees it and stands down, so the
 * two never double-count.
 *
 * Kept as its own Worker, separate from worker.js, on purpose: this one holds
 * a GitHub token and the other one takes the public's answers. A mistake here
 * must not be able to take signups down, and the other way round.
 *
 * Setup (Cloudflare dashboard)
 * ----------------------------
 *   Secret:        GITHUB_TOKEN  — fine-grained token, this repository only,
 *                                  permission "Actions: Read and write".
 *   Cron trigger:  5 * * * *
 *
 * There is deliberately no way to trigger a run by visiting the Worker's URL.
 * A public URL that starts workflow runs is a URL anyone can use to spend the
 * project's Actions minutes and API quotas.
 */

const REPO = "kalminDR/gta-blackout";
const WORKFLOW = "collect.yml";
const BRANCH = "main";

async function dispatch(env) {
  if (!env.GITHUB_TOKEN) {
    // Say so loudly in the Worker's logs rather than failing quietly: a
    // heartbeat with no token is a clock that is not ticking.
    console.error("heartbeat: GITHUB_TOKEN is not set; no run requested");
    return;
  }
  const res = await fetch(
    `https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches`,
    {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${env.GITHUB_TOKEN}`,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "gta-blackout-heartbeat",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ ref: BRANCH }),
    },
  );
  // GitHub answers 204 with no body when the run is accepted.
  if (res.status === 204) {
    console.log("heartbeat: collect run requested");
    return;
  }
  // 401: the token is wrong or expired. 403: it lacks Actions write. 404: the
  // token cannot see this repository. The body says which.
  const body = (await res.text()).slice(0, 300);
  console.error(`heartbeat: GitHub answered ${res.status}: ${body}`);
}

export default {
  async scheduled(controller, env, ctx) {
    ctx.waitUntil(dispatch(env));
  },

  async fetch() {
    return new Response(
      "heartbeat: requests a collect run at five past each hour. " +
      "Nothing here can be triggered by visiting it.\n",
      { status: 200, headers: { "Content-Type": "text/plain" } },
    );
  },
};
