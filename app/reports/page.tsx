"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChevronDown, User, Settings, LogOut } from "lucide-react";

const symptomData = {
  "2025-07-20": [
    {
      time: "10:03 AM",
      text: "Today I feel lethargic and uncomfortable. I'm really tired and find it difficult to move.",
    },
    {
      time: "12:35 PM",
      text: "I feel better now, but not by a lot. I went on a short walk.",
    },
  ],
  "2025-07-19": [
    {
      time: "9:15 AM",
      text: "Woke up feeling refreshed after a good night's sleep.",
    },
    {
      time: "2:20 PM",
      text: "Had some mild headaches during lunch, but they subsided.",
    },
    {
      time: "6:45 PM",
      text: "Energy levels dropped significantly in the evening.",
    },
  ],
  "2025-07-18": [
    { time: "8:30 AM", text: "Started the day with some joint stiffness." },
    { time: "11:00 AM", text: "Stiffness improved after morning stretches." },
    { time: "4:15 PM", text: "Feeling quite energetic and productive." },
  ],
};

export default function HomePage() {
  const [selectedDate, setSelectedDate] = useState("2025-07-20");

  return (
    <div className="min-h-screen p-6 bg-[#fff3e2]">
      {/* Navigation Bar */}
      <nav className="fixed top-0 left-0 right-0 bg-white/90 backdrop-blur-sm border-b border-gray-200 z-50">
        <div className="flex justify-between items-center px-6 py-2">
          <div className="flex items-center">
            <img
              src="/clara_logo.png"
              alt="CLARA Logo"
              className="h-12 w-auto"
            />
            <h1
              className="font-agbalumo text-4xl text-gray-800 ml-3"
              style={{
                color: "#F5CC98",
              }}
            >
              CLARA
            </h1>
          </div>

          {/* Navigation Items */}
          <div className="flex items-center space-x-8">
            <Link
              href="/"
              className="text-gray-700 hover:text-[#F099C1] font-medium transition-colors"
            >
              Home
            </Link>

            <DropdownMenu>
              <DropdownMenuTrigger className="flex items-center text-gray-700 hover:text-[#F099C1] font-medium transition-colors">
                Transcripts
                <ChevronDown className="ml-1 h-4 w-4" />
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem>Logs</DropdownMenuItem>
                <DropdownMenuItem>Reports</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            <Link
              href="/contacts"
              className="text-gray-700 hover:text-[#F099C1] font-medium transition-colors"
            >
              My People
            </Link>

            <DropdownMenu>
              <DropdownMenuTrigger className="flex items-center justify-center w-10 h-10 rounded-full bg-gray-200 hover:bg-gray-300 transition-colors">
                <User className="h-5 w-5 text-gray-600" />
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem className="flex items-center">
                  <Settings className="mr-2 h-4 w-4" />
                  Manage
                </DropdownMenuItem>
                <DropdownMenuItem
                  className="flex items-center"
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = "rgb(254 226 226)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = "";
                  }}
                >
                  <LogOut className="mr-2 h-4 w-4" />
                  Log Out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </nav>

      {/* Main Content with top padding for nav */}
      <div className="pt-24">
        {/* Title */}
        <h2 className="text-2xl font-bold text-gray-600 mb-4">
          Generate Report:
        </h2>

        {/* Date Selector */}
        <div className="flex justify-between mb-8 items-center">
          <div className="flex items-center space-x-8">
            <div className="flex items-center">
              <span className="text-lg font-semibold text-gray-700 mr-4">
                From:
              </span>
              <Select value={selectedDate} onValueChange={setSelectedDate}>
                <SelectTrigger className="w-48 h-12 bg-[#F099C1] hover:bg-[#EA83B3] border-none rounded-2xl text-lg font-semibold text-white py-2 px-6 transition-colors flex items-center justify-between">
                  <SelectValue />
                  <div className="w-px h-8 bg-white/50 mx-3"></div>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="2025-07-20">2025-07-20 </SelectItem>
                  <SelectItem value="2025-07-19">2025-07-19</SelectItem>
                  <SelectItem value="2025-07-18">2025-07-18</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center">
              <span className="text-lg font-semibold text-gray-700 mr-4">
                To:
              </span>
              <Select value={selectedDate} onValueChange={setSelectedDate}>
                <SelectTrigger className="w-48 h-12 bg-[#F099C1] hover:bg-[#EA83B3] border-none rounded-2xl text-lg font-semibold text-white py-2 px-6 transition-colors flex items-center justify-between">
                  <SelectValue />
                  <div className="w-px h-8 bg-white/50 mx-3"></div>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="2025-07-20">2025-07-20 </SelectItem>
                  <SelectItem value="2025-07-19">2025-07-19</SelectItem>
                  <SelectItem value="2025-07-18">2025-07-18</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <button className="bg-[#F099C1] hover:bg-[#EA83B3] text-white font-semibold py-3 px-8 rounded-2xl transition-colors">
            Generate
          </button>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 gap-8">
          {/* Symptom Logs */}
          <div>
            <Card className="bg-white/80 backdrop-blur-sm border-none rounded-2xl shadow-lg">
              <CardContent>
                <div className="h-64 flex items-center justify-center text-gray-500">
                  <p>Report will be generated here</p>
                </div>
              </CardContent>
            </Card>

            {/* Export Buttons */}
            <div className="flex justify-end mt-6 space-x-4">
              <button className="bg-[#F099C1] hover:bg-[#EA83B3] text-white font-semibold py-3 px-8 rounded-2xl transition-colors">
                Export to PDF
              </button>
              <button className="bg-[#F099C1] hover:bg-[#EA83B3] text-white font-semibold py-3 px-8 rounded-2xl transition-colors">
                Export to PNG
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
