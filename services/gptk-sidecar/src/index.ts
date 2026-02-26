import cors from "cors";
import express from "express";

type CookieItem = {
  name: string;
  value: string;
  domain?: string;
  path?: string;
  secure?: boolean;
};

type GptkSession = {
  account?: string;
  fSid: string;
  bl: string;
  path: string;
  at: string;
  rapt?: string;
};

const app = express();
app.use(cors());
app.use(express.json({ limit: "2mb" }));

const PORT = Number(process.env.PORT || 8787);

function cookieHeader(cookieJar: CookieItem[]): string {
  return cookieJar.map((c) => `${c.name}=${c.value}`).join("; ");
}

function extractValue(html: string, key: string): string | undefined {
  const escaped = key.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const regex = new RegExp(`"${escaped}":"([^\"]+)"`);
  const match = html.match(regex);
  if (!match) {
    return undefined;
  }
  return match[1]
    .replace(/\\u003d/g, "=")
    .replace(/\\u0026/g, "&")
    .replace(/\\\//g, "/");
}

function parseWrbPayload(body: string): unknown {
  const jsonLine = body
    .split("\n")
    .map((line) => line.trim())
    .find((line) => line.includes("wrb.fr"));

  if (!jsonLine) {
    throw new Error("No wrb.fr envelope found");
  }

  const parsed = JSON.parse(jsonLine);
  const payload = parsed?.[0]?.[2];
  if (!payload) {
    throw new Error("Missing payload in wrb.fr envelope");
  }

  return JSON.parse(payload);
}

app.get("/health", (_req, res) => {
  res.json({ status: "ok" });
});

app.post("/api/session/bootstrap", async (req, res) => {
  try {
    const cookieJar = (req.body.cookieJar || []) as CookieItem[];
    const sourcePath = (req.body.sourcePath || "/") as string;

    if (!Array.isArray(cookieJar) || cookieJar.length === 0) {
      return res.status(400).json({ error: "cookieJar is required" });
    }

    const response = await fetch(`https://photos.google.com${sourcePath}`, {
      headers: {
        Cookie: cookieHeader(cookieJar),
      },
      redirect: "follow",
    });

    if (!response.ok) {
      return res.status(response.status).json({ error: `Bootstrap failed: ${response.status}` });
    }

    const html = await response.text();

    const session: GptkSession = {
      account: extractValue(html, "oPEP7c"),
      fSid: extractValue(html, "FdrFJe") || "",
      bl: extractValue(html, "cfb2h") || "",
      path: extractValue(html, "eptZe") || "/_/PhotosUi/",
      at: extractValue(html, "SNlM0e") || "",
      rapt: extractValue(html, "Dbw5Ud"),
    };

    if (!session.fSid || !session.bl || !session.at) {
      return res.status(422).json({
        error: "Unable to extract required session fields (fSid/bl/at). Refresh cookies and retry.",
      });
    }

    return res.json({ session });
  } catch (error) {
    return res.status(500).json({ error: (error as Error).message });
  }
});

app.post("/api/rpc/execute", async (req, res) => {
  try {
    const cookieJar = (req.body.cookieJar || []) as CookieItem[];
    const session = (req.body.session || {}) as GptkSession;
    const rpcid = req.body.rpcid as string;
    const requestData = req.body.requestData;
    const sourcePath = (req.body.sourcePath || "/") as string;

    if (!Array.isArray(cookieJar) || cookieJar.length === 0) {
      return res.status(400).json({ error: "cookieJar is required" });
    }
    if (!session.fSid || !session.bl || !session.at || !session.path) {
      return res.status(400).json({ error: "session fSid/bl/path/at is required" });
    }
    if (!rpcid) {
      return res.status(400).json({ error: "rpcid is required" });
    }

    const wrappedData = [[[rpcid, JSON.stringify(requestData), null, "generic"]]];
    const body = `f.req=${encodeURIComponent(JSON.stringify(wrappedData))}&at=${encodeURIComponent(session.at)}&`;

    const params = new URLSearchParams({
      rpcids: rpcid,
      "source-path": sourcePath,
      "f.sid": session.fSid,
      bl: session.bl,
      pageId: "none",
      rt: "c",
    });
    if (session.rapt) {
      params.set("rapt", session.rapt);
    }

    const url = `https://photos.google.com${session.path}data/batchexecute?${params.toString()}`;

    const response = await fetch(url, {
      method: "POST",
      headers: {
        "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
        Cookie: cookieHeader(cookieJar),
      },
      body,
      redirect: "follow",
    });

    if (response.status === 401 || response.status === 403) {
      return res.status(401).json({ error: "Unauthorized session" });
    }

    if (!response.ok) {
      const text = await response.text();
      return res.status(response.status).json({ error: `RPC request failed`, details: text.slice(0, 3000) });
    }

    const text = await response.text();
    const data = parseWrbPayload(text);

    return res.json({
      data,
      session,
    });
  } catch (error) {
    return res.status(500).json({ error: (error as Error).message });
  }
});

app.listen(PORT, () => {
  console.log(`[gptk-sidecar] listening on http://localhost:${PORT}`);
});
