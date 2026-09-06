#!/usr/bin/env python3
"""Six dated, falsifiable statements, written down before the event.

Why they exist
--------------
Anyone can explain a Thursday afterwards. The only version of this project
that is worth a journalist's time is one where the claims were fixed in
advance, in public, and afterwards visibly passed or failed. So these are
published before 19 November 2026 and are never edited afterwards. If one is
wrong it stays wrong on the page, marked failed.

Being publicly wrong about two of six is more credible than being right about
all six. It is also the version that can be written about twice.

How each threshold was chosen
-----------------------------
Every number below came out of the data in this repository, and each one was
checked against the years we already hold to make sure it does not fire on an
ordinary autumn. That check is not a formality. Two of the six were rewritten
because the first version would have been satisfied with no game involved:

  * The subway rule inherited from the working notes compared 19 November to
    the whole October-December window. Two Thursdays in that window are
    Christmas Eve and New Year's Eve, which run 25-60% below normal, so no
    ordinary day could ever be "the lowest" and the window mean was dragged
    down by holidays. Rewritten against November Thursdays alone, which the
    record shows are extraordinarily uniform.

  * The electricity rule first read "at least one of the eight grids moves by
    two standard deviations". That happens on 24.4% of ordinary autumn
    weekdays -- one Thursday in four, by chance, with nothing happening. It
    now takes three of the eight, which happens on 1.4%.

This is the same failure the Russian PlayStation Store nearly caused: a
prediction that was already true before the event. Every threshold here has
been run against the backfill to see how often it fires on an ordinary day,
and that rate is published beside it.

What is deliberately missing
----------------------------
There is no prediction for claim 04, "you could not buy a console". The eBay
collector only began authenticating on 6 September 2026 and has four daily
medians behind it. A threshold drawn from four readings would be a number we
made up, and this project does not do that. Claim 04 keeps its witnesses and
gets no verdict.

Self-reports are also absent, for the same reason -- the endpoint has not
returned a single response yet -- and because a prediction about our own
self-selected sample is the one a sceptical reader should discount first.
"""

RELEASE_DAY = "2026-11-19"

# The day these six were fixed. A constant, never a call to the clock: if this
# moved with every run, "written down in advance" would be a claim the file
# quietly re-earned every hour, which is the opposite of the point. Changing
# it means the predictions changed, and that is exactly what must never happen
# without saying so.
PUBLISHED_AT = "2026-09-06"

# Each prediction carries: the sentence, the claim it serves, the exact rule
# in machine-checkable words, where its threshold came from, and how often the
# rule fires on an ordinary day. That last field is the one that matters --
# a prediction whose base rate is high is not a prediction.
PREDICTIONS = [
    {
        "id": "subway",
        "claim": "work",
        "says": "Fewer New Yorkers will travel on launch day than on any "
                "other November Thursday",
        "rule": "New York subway ridership on Thursday 19 November 2026 is "
                "lower than on 5 and 12 November 2026, and at least 3% below "
                "the mean of those three Thursdays. Thanksgiving, 26 November, "
                "is excluded.",
        "threshold_from":
            "November Thursdays excluding Thanksgiving are the most uniform "
            "days in the whole record: standard deviation 0.68% in 2023, "
            "0.99% in 2024, 0.45% in 2025, and no November Thursday in three "
            "years fell more than 1.12% below its month's mean. Three per cent "
            "is between three and six standard deviations of ordinary "
            "variation.",
        "base_rate":
            "Never. The third Thursday of November came in at -0.18%, -0.73% "
            "and +0.18% against its own month in 2023, 2024 and 2025.",
        "caveat":
            "12 November is preload day. If the preload itself keeps people "
            "at home, the comparison days are depressed and this test becomes "
            "harder to pass, not easier.",
    },
    {
        "id": "traffic",
        "claim": "work",
        "says": "The evening commute will be lighter in most of our cities "
                "than on any other Thursday this autumn",
        "rule": "In at least four of the six cities, the evening peak road "
                "delay on 19 November 2026 is the lowest recorded on any "
                "Thursday between 1 October and 17 December 2026.",
        "threshold_from":
            "A rank test, which needs no history: it asks only that this "
            "Thursday beat the other Thursdays we are already measuring. "
            "The traffic collector was rebuilt on 6 September and has three "
            "days behind it, so a magnitude threshold would have to be "
            "invented. This one does not.",
        "base_rate":
            "About 1 in 1,135. With eleven Thursdays in the window, one city "
            "is lowest by chance one time in eleven; four of six cities at "
            "once is 0.09%, assuming the cities move independently when "
            "nothing is happening.",
        "caveat":
            "Six cities are not fully independent -- weather systems and "
            "school holidays cross borders -- so the true chance is somewhat "
            "higher than 1 in 1,135.",
    },
    {
        "id": "power",
        "claim": "home",
        "says": "At least three European countries will spend the evening at "
                "home in a way their national grid can see",
        "rule": "On 19 November 2026, at least three of the eight grids show "
                "an evening ratio -- the evening peak over the same day's "
                "16:00 reading -- at least two standard deviations from that "
                "country's own autumn normal for a weekday.",
        "threshold_from":
            "Measured on 213 ordinary autumn weekdays in the backfill. One "
            "grid clearing two standard deviations happens on 24.4% of them, "
            "which is no prediction at all. Two happens on 4.7%. Three "
            "happens on 1.4%.",
        "base_rate":
            "1.4% of ordinary autumn weekdays -- about one Thursday in "
            "seventy.",
        "caveat":
            "This is the boldest of the six and the one most likely to fail. "
            "Football has never once moved a national grid on this measure: "
            "the two World Cup readings this project treated as evidence for "
            "years turned out to be a Sunday scored against weekdays. We are "
            "predicting an effect that has never been observed. Each grid also "
            "differs enormously in what it could see at all -- Germany can "
            "distinguish a 4.8% change in its evening, Hungary nothing under "
            "13.0%.",
    },
    {
        "id": "steam",
        "claim": "quiet",
        "says": "Every other game will empty out at the same moment",
        "rule": "During the launch evening, the seven tracked games other than "
                "Grand Theft Auto V record their lowest combined player count, "
                "for that hour of that weekday, of any Thursday between "
                "1 October and 17 December 2026.",
        "threshold_from":
            "A rank test on the same-hour, same-weekday comparison. Raw "
            "player counts are useless for this: the basket swings threefold "
            "across an ordinary day, so any threshold not tied to the hour "
            "measures the time of day and nothing else.",
        "base_rate":
            "About 1 in 11, the number of Thursdays in the window.",
        "caveat":
            "Steam player counts rise through the autumn into winter, so an "
            "October Thursday starts with an advantage. That makes a November "
            "low harder to achieve, not easier.",
    },
    {
        "id": "twitch",
        "claim": "quiet",
        "says": "More people will watch this than watched the biggest "
                "scheduled event on the platform, and for longer",
        "rule": "Between 19 and 20 November 2026, the global Twitch top-100 "
                "viewer total holds at or above twice its same-hour, "
                "same-weekday median for at least four consecutive hourly "
                "readings.",
        "threshold_from":
            "ZEVENT, one of the largest scheduled events on Twitch, landed in "
            "the first week of collection: 540,000 concurrent viewers on a "
            "single channel, lifting the global top-100 total to 2.12 times "
            "the running median at its peak. It held twice the median for two "
            "consecutive hours and never longer.",
        "base_rate":
            "Not once in 105 readings did anything but ZEVENT come near, and "
            "ZEVENT itself managed two hours, not four.",
        "caveat":
            "ZEVENT's multiple was measured against a running median over four "
            "days, because that is all the history there was. The prediction "
            "is stated against the same-hour, same-weekday median, which will "
            "exist by November. The two are not exactly comparable, and "
            "ZEVENT will be rescored on the better baseline when it exists.",
    },
    {
        "id": "servers",
        "claim": "servers",
        "says": "Sony's own status page will admit to a problem",
        "rule": "PlayStation Network reports at least one service incident "
                "outside Russia between 19 and 20 November 2026.",
        "threshold_from":
            "Sony has listed the Russian PlayStation Store as degraded "
            "continuously since 2022, which is why Russia is excluded: "
            "counting it would have made this prediction true in advance, by "
            "a war. With Russia removed the count has been zero in every "
            "reading taken.",
        "base_rate":
            "Zero incidents in 101 readings so far. That record is only four "
            "days long and will be months long by November; the rate will be "
            "republished then rather than quietly left as it is.",
        "caveat":
            "Xbox is not part of this one. Its status page has already shown "
            "two incidents in the same 101 readings, so a prediction that "
            "included it would be far easier to satisfy.",
    },
]

# The commitment that travels with them. It is the point of the exercise.
COMMITMENT = (
    "We expect to be wrong about at least one of these. When we are, it stays "
    "on this page marked failed, with the reading that failed it. We will not "
    "quietly edit them."
)


def as_published():
    """The six, in the shape the page renders and the order it shows them."""
    return {"published_at": PUBLISHED_AT,
            "release_day": RELEASE_DAY,
            "commitment": COMMITMENT,
            "predictions": PREDICTIONS}
