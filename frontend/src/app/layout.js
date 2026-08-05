import "./globals.css";
import { Toaster } from "@/components/ui/sonner";

export const metadata = {
  title: "SmartFINN — Mortgage Compliance Engine",
  description: "Automated mortgage compliance and OCR extraction system",
};

export default function RootLayout({ children }) {
  return (
    <html
      lang="en"
      className="h-full antialiased"
    >
      <body className="min-h-full flex flex-col">
        {children}
        <Toaster richColors />
      </body>
    </html>
  );
}
