import { PrismaClient } from "@prisma/client";

import { env } from "~/env";

const createPrismaClient = () =>
  new PrismaClient({
    log:
      env.NODE_ENV === "development" ? ["query", "error", "warn"] : ["error"],
  });

const globalForPrisma = globalThis as unknown as {
  prisma: ReturnType<typeof createPrismaClient> | undefined;
};

export const db = globalForPrisma.prisma ?? createPrismaClient();

if (env.NODE_ENV !== "production") globalForPrisma.prisma = db;

// Clerk owns signup/session state; mirror the user into our own table on
// first sight so credits/generatedAudioClips have a row to attach to.
export async function getOrCreateUser(userId: string) {
  return db.user.upsert({
    where: { id: userId },
    update: {},
    create: { id: userId },
  });
}
