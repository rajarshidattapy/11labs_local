import { auth } from "@clerk/nextjs/server";
import { PageLayout } from "~/components/client/page-layout";
import { getHistoryItems } from "~/lib/history";
import { getOrCreateUser } from "~/server/db";
import { TextToSpeechEditor } from "../../../../components/client/speech-synthesis/text-to-speech-editor";

export default async function TextToSpeechPage() {
  const { userId } = await auth();

  let credits = 0;

  if (userId) {
    const user = await getOrCreateUser(userId);
    credits = user.credits;
  }

  const service = "styletts2";

  const historyItems = await getHistoryItems(service);

  return (
    <PageLayout
      title={"Text to Speech"}
      service={service}
      showSidebar={true}
      historyItems={historyItems}
    >
      <TextToSpeechEditor service="styletts2" credits={credits} />
    </PageLayout>
  );
}
