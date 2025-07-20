import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function Unsuccessful() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#fff3e2] p-8">
      <div className="bg-white/95 backdrop-blur-sm shadow-2xl rounded-2xl p-10 max-w-md text-center space-y-6 border-4 border-[#F099C1]">
        <h2 className="text-3xl font-agbalumo" style={{ color: "#F5CC98" }}>
          Oops!
        </h2>
        <p className="text-gray-800">
          We couldn&apos;t get the required Google Fit permissions. Please try signing
          in again and make sure you grant all fitness access.
        </p>
        <Link href="/">
          <Button className="bg-[#F099C1] hover:bg-[#EA83B3] text-white py-2 px-6 rounded-2xl">
            Return to Home
          </Button>
        </Link>
      </div>
    </div>
  );
}

