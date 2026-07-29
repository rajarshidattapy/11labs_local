import { NextRequest } from "next/server";

const services = {
  styletts2: {
    voices: ["andreas", "woman"],
  },
  "seed-vc": {
    voices: ["andreas", "woman", "trump"],
  },
  "make-an-audio": {
    voices: [],
  },
};

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ slug: string[] }> },
) {
  const { slug } = await params;
  const [service, endpoint] = slug;

  if (!services[service as keyof typeof services]) {
    return Response.json({ error: "Service not found" }, { status: 404 });
  }

  if (endpoint === "voices") {
    return Response.json({
      voices: services[service as keyof typeof services].voices,
    });
  }

  if (endpoint === "health") {
    return Response.json({
      status: "healthy",
      model: "loaded",
    });
  }

  return Response.json({ error: "Not found" }, { status: 404 });
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ slug: string[] }> },
) {
  const { slug } = await params;
  const [service] = slug;

  if (!services[service as keyof typeof services]) {
    return Response.json({ error: "Service not found" }, { status: 404 });
  }

  await new Promise((resolve) => setTimeout(resolve, 2000));

  return Response.json({
    audio_url: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
  });
}
