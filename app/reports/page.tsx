"use client";

import type { FC } from "react";
import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { format } from "date-fns";
import { Calendar } from "@/components/ui/calendar";
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "@/components/ui/popover";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import { Card, CardContent } from "@/components/ui/card";
import {
  ChevronDown,
  User,
  Settings,
  LogOut,
  CalendarIcon,
  Loader2,
} from "lucide-react";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:5000";

// pull this out so TSX stays happy
interface DateFieldProps {
  label: string;
  date?: Date;
  onChange: (d: Date | undefined) => void;
}

const DateField: FC<DateFieldProps> = ({ label, date, onChange }) => {
  return (
    <div className="flex items-center">
      <span className="text-lg font-semibold text-gray-700 mr-4">
        {label}
      </span>
      <Popover>
        <PopoverTrigger asChild>
          <button className="w-64 h-12 bg-[#F099C1] hover:bg-[#EA83B3] rounded-2xl text-lg font-semibold text-white px-6 flex items-center justify-between">
            {date ? format(date, "PPP") : <span>Select date</span>}
            <CalendarIcon className="ml-2 h-5 w-5" />
          </button>
        </PopoverTrigger>
        <PopoverContent className="p-0" align="start">
          <Calendar
            mode="single"
            selected={date}
            onSelect={onChange}
            initialFocus
          />
        </PopoverContent>
      </Popover>
    </div>
  );
};

export default function ReportPage() {
  const [fromDate, setFromDate] = useState<Date>();
  const [toDate, setToDate] = useState<Date>();
  const [stepsImg, setStepsImg] = useState<string | null>(null);
  const [sleepImg, setSleepImg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const iso = (d: Date) => format(d, "yyyy-MM-dd");

  async function handleGenerate() {
    if (!fromDate || !toDate) {
      setErrorMsg("Please pick both start and end dates.");
      return;
    }
    setLoading(true);
    setErrorMsg(null);

    const start = iso(fromDate);
    const end = iso(toDate);

    try {
      const res = await fetch(
        `${BACKEND_URL}/api/report?start=${start}&end=${end}`,
        { credentials: "include" }
      );
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(txt || "Failed to fetch report");
      }
      await res.json();

      // filenames must match what your Flask writes
      const stepsFilename = `steps_${start}_${end}.png`;
      const sleepFilename = `sleep_${start}_${end}.png`;

      setStepsImg(`/reports/${stepsFilename}`);
      setSleepImg(`/reports/${sleepFilename}`);
    } catch (err: any) {
      setErrorMsg(err.message || "Unknown error");
      setStepsImg(null);
      setSleepImg(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen p-6 bg-[#fff3e2]">
      {/* ── Nav bar ─────────────────────────────────────────────── */}
      <nav className="fixed top-0 left-0 right-0 bg-white/90 backdrop-blur-sm border-b border-gray-200 z-50">
        <div className="flex justify-between items-center px-6 py-2">
          <div className="flex items-center">
            <Image
              src="/clara_logo.png"
              alt="CLARA Logo"
              width={48}
              height={48}
            />
            <h1
              className="font-agbalumo text-4xl ml-3"
              style={{ color: "#F5CC98" }}
            >
              CLARA
            </h1>
          </div>
          <div className="flex items-center space-x-8">
            <Link
              href="/"
              className="text-gray-700 hover:text-[#F099C1] font-medium"
            >
              Home
            </Link>
            <DropdownMenu>
              <DropdownMenuTrigger className="flex items-center text-gray-700 hover:text-[#F099C1] font-medium">
                Transcripts
                <ChevronDown className="ml-1 h-4 w-4" />
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <Link href="/logs">
                  <DropdownMenuItem>Logs</DropdownMenuItem>
                </Link>
                <Link href="/reports">
                  <DropdownMenuItem>Reports</DropdownMenuItem>
                </Link>
              </DropdownMenuContent>
            </DropdownMenu>
            <Link
              href="/contacts"
              className="text-gray-700 hover:text-[#F099C1] font-medium"
            >
              My People
            </Link>
            <DropdownMenu>
              <DropdownMenuTrigger className="flex items-center justify-center w-10 h-10 rounded-full bg-gray-200 hover:bg-gray-300">
                <User className="h-5 w-5 text-gray-600" />
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem className="flex items-center">
                  <Settings className="mr-2 h-4 w-4" />
                  Manage
                </DropdownMenuItem>
                <DropdownMenuItem className="flex items-center hover:bg-red-100">
                  <LogOut className="mr-2 h-4 w-4" />
                  Log Out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </nav>

      {/* ── Main ────────────────────────────────────────────────── */}
      <div className="pt-24">
        <h2 className="text-2xl font-bold text-gray-600 mb-4">
          Generate Report:
        </h2>

        <div className="flex justify-between items-center mb-8">
          <div className="flex items-center space-x-8">
            <DateField label="From:" date={fromDate} onChange={setFromDate} />
            <DateField label="To:" date={toDate} onChange={setToDate} />
          </div>
          <button
            onClick={handleGenerate}
            className="bg-[#F099C1] hover:bg-[#EA83B3] text-white font-semibold py-3 px-8 rounded-2xl"
            disabled={loading}
          >
            {loading ? <Loader2 className="animate-spin h-5 w-5" /> : "Generate"}
          </button>
        </div>

        <Card className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg">
          <CardContent className="p-6">
            {errorMsg && (
              <p className="text-red-600 font-medium mb-4">{errorMsg}</p>
            )}
            {!stepsImg && !sleepImg && !loading && !errorMsg && (
              <p className="text-center text-gray-500 h-64 flex items-center justify-center">
                Report will appear here
              </p>
            )}
            {/* eslint-disable @next/next/no-img-element */}
            {(stepsImg || sleepImg) && (
              <div className="grid md:grid-cols-2 gap-6">
                {stepsImg && (
                  <img
                    src={stepsImg}
                    alt="Steps graph"
                    width={800}
                    height={400}
                    className="rounded-lg border shadow"
                  />
                )}
                {sleepImg && (
                  <img
                    src={sleepImg}
                    alt="Sleep graph"
                    width={800}
                    height={400}
                    className="rounded-lg border shadow"
                  />
                )}
              </div>
            )}
            {/* eslint-enable @next/next/no-img-element */}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
