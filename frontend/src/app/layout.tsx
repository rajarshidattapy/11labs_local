import "~/styles/globals.css";

import { ClerkProvider } from "@clerk/nextjs";
import { type Metadata } from "next";
import { Inter } from "next/font/google";
import { Toaster } from "react-hot-toast";

export const metadata: Metadata = {
  title: "11labs",
  description: "Local Elevenlabs clone for text-to-speech and speech-to-text",
  icons: [{ rel: "icon", url: "/favicon.ico" }],
};

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
});

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <ClerkProvider
      signInUrl="/app/sign-in"
      signUpUrl="/app/sign-up"
      signInFallbackRedirectUrl="/app/speech-synthesis/text-to-speech"
      signUpFallbackRedirectUrl="/app/speech-synthesis/text-to-speech"
    >
      <html lang="en" className={`${inter.className}`}>
        <body>
          <Toaster />
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
