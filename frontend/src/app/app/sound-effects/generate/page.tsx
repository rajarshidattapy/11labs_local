import { auth } from "@clerk/nextjs/server";
import { PageLayout } from "~/components/client/page-layout";
import { SoundEffectsGenerator } from "~/components/client/sound-effects/sound-effects-generator";
import { getOrCreateUser } from "~/server/db";

export default async function SoundEffectsGeneratePage() {
  const { userId } = await auth();

  let credits = 0;

  if (userId) {
    const user = await getOrCreateUser(userId);
    credits = user.credits;
  }

  const soundEffectsTabs = [
    {
      name: "Generate",
      path: "/app/sound-effects/generate",
    },
    {
      name: "History",
      path: "/app/sound-effects/history",
    },
  ];

  return (
    <PageLayout
      title={"Sound Effects"}
      showSidebar={false}
      tabs={soundEffectsTabs}
      service="make-an-audio"
    >
      <SoundEffectsGenerator credits={credits} />
    </PageLayout>
  );
}
