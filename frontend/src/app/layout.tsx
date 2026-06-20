import type { Metadata } from "next";
import { Cinzel, Cinzel_Decorative, IM_Fell_English, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const cinzel = Cinzel({
  subsets: ["latin"],
  weight: ["400", "600", "700"],
  variable: "--font-cinzel",
  display: "swap",
});

const cinzelDecorative = Cinzel_Decorative({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-cinzel-decorative",
  display: "swap",
});

const imFellEnglish = IM_Fell_English({
  subsets: ["latin"],
  weight: ["400"],
  variable: "--font-im-fell",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400"],
  variable: "--font-jetbrains",
  display: "swap",
});

export const metadata: Metadata = {
  title: "CodeTribunal - Where Every Line of Code Faces Justice",
  description: "Multi-agent adversarial code review system",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${cinzel.variable} ${cinzelDecorative.variable} ${imFellEnglish.variable} ${jetbrainsMono.variable} bg-[#080808] text-[#f0f0f0] antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
