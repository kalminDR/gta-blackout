#!/usr/bin/env python3
"""Tests for the ENTSO-E parser, run without touching the network.

The API cannot be reached from the build environment, so the parser is
exercised against fixtures shaped like the documents it will actually meet:
hourly and quarter-hourly resolutions, the namespaced form, a multi-period
document, and the error that arrives dressed as a success.
"""

import sys
from datetime import datetime, timezone

sys.path.insert(0, "/home/claude/repo")
from collect import _entsoe_points  # noqa: E402

NS = "urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0"

HOURLY = f"""<?xml version="1.0" encoding="UTF-8"?>
<GL_MarketDocument xmlns="{NS}">
  <mRID>abc123</mRID>
  <TimeSeries>
    <mRID>1</mRID>
    <Period>
      <timeInterval>
        <start>2026-09-05T16:00Z</start>
        <end>2026-09-05T19:00Z</end>
      </timeInterval>
      <resolution>PT60M</resolution>
      <Point><position>1</position><quantity>42150</quantity></Point>
      <Point><position>2</position><quantity>43900</quantity></Point>
      <Point><position>3</position><quantity>45120</quantity></Point>
    </Period>
  </TimeSeries>
</GL_MarketDocument>"""

QUARTER = f"""<?xml version="1.0" encoding="UTF-8"?>
<GL_MarketDocument xmlns="{NS}">
  <TimeSeries>
    <Period>
      <timeInterval>
        <start>2026-09-05T18:00Z</start>
        <end>2026-09-05T19:00Z</end>
      </timeInterval>
      <resolution>PT15M</resolution>
      <Point><position>1</position><quantity>5100</quantity></Point>
      <Point><position>2</position><quantity>5180</quantity></Point>
      <Point><position>3</position><quantity>5240</quantity></Point>
      <Point><position>4</position><quantity>5205</quantity></Point>
    </Period>
  </TimeSeries>
</GL_MarketDocument>"""

TWO_PERIODS = f"""<?xml version="1.0" encoding="UTF-8"?>
<GL_MarketDocument xmlns="{NS}">
  <TimeSeries>
    <Period>
      <timeInterval><start>2026-09-05T10:00Z</start><end>2026-09-05T12:00Z</end></timeInterval>
      <resolution>PT60M</resolution>
      <Point><position>1</position><quantity>100</quantity></Point>
      <Point><position>2</position><quantity>200</quantity></Point>
    </Period>
  </TimeSeries>
  <TimeSeries>
    <Period>
      <timeInterval><start>2026-09-05T12:00Z</start><end>2026-09-05T14:00Z</end></timeInterval>
      <resolution>PT60M</resolution>
      <Point><position>1</position><quantity>300</quantity></Point>
      <Point><position>2</position><quantity>400</quantity></Point>
    </Period>
  </TimeSeries>
</GL_MarketDocument>"""

NO_DATA = """<?xml version="1.0" encoding="UTF-8"?>
<Acknowledgement_MarketDocument
    xmlns="urn:iec62325.351:tc57wg16:451-1:acknowledgementdocument:8:0">
  <mRID>x</mRID>
  <Reason>
    <code>999</code>
    <text>No matching data found for Data item Actual Total Load.</text>
  </Reason>
</Acknowledgement_MarketDocument>"""

NO_NAMESPACE = """<?xml version="1.0"?>
<GL_MarketDocument>
  <TimeSeries><Period>
    <timeInterval><start>2026-09-05T18:00Z</start><end>2026-09-05T19:00Z</end></timeInterval>
    <resolution>PT60M</resolution>
    <Point><position>1</position><quantity>777</quantity></Point>
  </Period></TimeSeries>
</GL_MarketDocument>"""


def check(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + (f"  [{detail}]" if detail else ""))
    return bool(cond)


def run():
    ok = []

    pts, reason = _entsoe_points(HOURLY)
    ok.append(check("hourly: three points parsed", len(pts) == 3, f"got {len(pts)}"))
    ok.append(check("hourly: no error reason", reason is None))
    ok.append(check("hourly: first timestamp is the interval start",
                    pts[0][0] == datetime(2026, 9, 5, 16, 0, tzinfo=timezone.utc), str(pts[0][0])))
    ok.append(check("hourly: position 3 lands two hours later",
                    pts[2][0] == datetime(2026, 9, 5, 18, 0, tzinfo=timezone.utc), str(pts[2][0])))
    ok.append(check("hourly: newest value is last", pts[-1][1] == 45120.0, str(pts[-1][1])))

    pts, _ = _entsoe_points(QUARTER)
    ok.append(check("quarter-hourly: four points", len(pts) == 4, f"got {len(pts)}"))
    ok.append(check("quarter-hourly: position 4 is 45 minutes in",
                    pts[3][0] == datetime(2026, 9, 5, 18, 45, tzinfo=timezone.utc), str(pts[3][0])))

    pts, _ = _entsoe_points(TWO_PERIODS)
    ok.append(check("two periods: all four points collected", len(pts) == 4, f"got {len(pts)}"))
    ok.append(check("two periods: sorted, newest last", pts[-1][1] == 400.0, str(pts[-1][1])))
    ok.append(check("two periods: timestamps strictly increasing",
                    all(a[0] < b[0] for a, b in zip(pts, pts[1:]))))

    pts, reason = _entsoe_points(NO_DATA)
    ok.append(check("no data: returns no points", pts == []))
    ok.append(check("no data: reason carries the code", reason and "999" in reason, str(reason)))
    ok.append(check("no data: reason carries the text",
                    reason and "No matching data" in reason, str(reason)))

    pts, _ = _entsoe_points(NO_NAMESPACE)
    ok.append(check("unnamespaced document still parses",
                    len(pts) == 1 and pts[0][1] == 777.0, str(pts)))

    print()
    print(f"{sum(ok)}/{len(ok)} checks passed")
    return all(ok)


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
