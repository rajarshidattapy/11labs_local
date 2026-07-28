import { db } from "~/server/db";
import { inngest } from "./client";
import { env } from "~/env";

// Preset voice names picked in the UI don't carry actual audio - TTS/api.py needs a
// real reference clip to clone. Map each preset to a pre-uploaded reference S3 key.
const VOICE_PROMPT_S3_KEYS: Record<string, string> = {
  andreas: "voice-prompts/andreas.wav",
  woman: "voice-prompts/woman.wav",
};

export const aiGenerationFunction = inngest.createFunction(
  {
    id: "genrate-audio-clip",
    retries: 2,
    throttle: {
      limit: 3,
      period: "1m",
      key: "event.data.userId",
    },
  },
  { event: "generate.request" },
  async ({ event, step }) => {
    const { audioClipId } = event.data;

    const audioClip = await step.run("get-clip", async () => {
      return await db.generatedAudioClip.findUniqueOrThrow({
        where: { id: audioClipId },
        select: {
          id: true,
          text: true,
          voice: true,
          userId: true,
          service: true,
          originalVoiceS3Key: true,
        },
      });
    });

    const result = await step.run("call-api", async () => {
      let response: Response | null = null;

      if (audioClip.service === "styletts2") {
        const promptAudioS3Key = audioClip.voice
          ? VOICE_PROMPT_S3_KEYS[audioClip.voice]
          : undefined;

        if (!promptAudioS3Key) {
          await db.generatedAudioClip.update({
            where: { id: audioClip.id },
            data: { failed: true },
          });
          throw new Error(
            `No reference audio configured for voice "${audioClip.voice}"`,
          );
        }

        response = await fetch(env.TTS_API_ROUTE + "/generate", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: env.BACKEND_API_KEY ?? "",
          },
          body: JSON.stringify({
            text: audioClip.text,
            prompt_audio_s3_key: promptAudioS3Key,
          }),
        });
      } else if (audioClip.service === "seedvc") {
        await db.generatedAudioClip.update({
          where: { id: audioClip.id },
          data: { failed: true },
        });
        throw new Error(
          "Speech-to-speech is not available: seed-vc has no backend service",
        );
      } else if (audioClip.service === "make-an-audio") {
        response = await fetch(env.SOUND_GENERATOR_API_ROUTE + "/generate", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: env.BACKEND_API_KEY ?? "",
          },
          body: JSON.stringify({
            prompt: audioClip.text,
          }),
        });
      }

      if (!response) {
        throw new Error("API error: no response");
      }

      if (!response.ok) {
        await db.generatedAudioClip.update({
          where: { id: audioClip.id },
          data: {
            failed: true,
          },
        });

        throw new Error("API error: " + response.statusText);
      }

      return response.json() as Promise<{ audio_url: string; s3_key: string }>;
    });

    const history = await step.run("save-to-history", async () => {
      return await db.generatedAudioClip.update({
        where: { id: audioClip.id },
        data: {
          s3Key: result.s3_key,
        },
      });
    });

    const deductCredits = await step.run("deduct-credits", async () => {
      return await db.user.update({
        where: { id: audioClip.userId },
        data: {
          credits: {
            decrement: 50,
          },
        },
      });
    });

    return { success: true };
  },
);
