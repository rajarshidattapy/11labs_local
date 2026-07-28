import { auth } from "@clerk/nextjs/server";
import { PageLayout } from "~/components/client/page-layout";
import { TextToSpeechEditor } from "~/components/client/speech-synthesis/text-to-speech-editor";
import { VoiceChanger } from "~/components/client/speech-synthesis/voice-changer";
import { getHistoryItems } from "~/lib/history";
import { getOrCreateUser } from "~/server/db";

export default async function SpeechToSpeechPage() {
  const { userId } = await auth();

  let credits = 0;

  if (userId) {
    const user = await getOrCreateUser(userId);
    credits = user.credits;
  }

  const service = "seedvc";

  const historyItems = await getHistoryItems(service);

  return (
    <PageLayout
      title={"Voice Changer"}
      service={service}
      showSidebar={true}
      historyItems={historyItems}
    >
      <VoiceChanger credits={credits} service={service} />
    </PageLayout>
  );
}
