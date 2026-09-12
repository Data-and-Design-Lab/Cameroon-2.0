import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Claim Fraud & Rejection Review",
  description:
    "openIMIS claim triage — LightGBM risk scoring with TreeSHAP explanations for each decision.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      </head>
      <body>{children}</body>
    </html>
  );
}
