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
        {/* Date Selector */}
        <div className="flex justify-start mb-8">
          <Select value={selectedDate} onValueChange={setSelectedDate}>
            <SelectTrigger className="w-64 h-16 bg-[#F099C1] hover:bg-[#EA83B3] border-none rounded-2xl text-2xl font-semibold text-white py-3 px-8 transition-colors flex items-center justify-between">
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

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Symptom Logs */}
          <div className="lg:col-span-2">
            <Card className="bg-white/80 backdrop-blur-sm border-none rounded-2xl shadow-lg">
              <CardHeader>
                <CardTitle className="text-gray-700 text-lg">
                  Symptom Logs
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="min-w-full text-left border-separate border-spacing-y-2 border border-[#F099C1] rounded-xl table-fixed">
                    <colgroup>
                      <col style={{ width: "120px" }} />
                      <col />
                    </colgroup>
                    <thead>
                      <tr>
                        <th className="px-4 py-2 text-gray-600 font-semibold border-b border-[#F099C1] w-32">
                          Time
                        </th>
                        <th className="px-4 py-2 text-gray-600 font-semibold border-b border-[#F099C1]">
                          Log
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {symptomData[
                        selectedDate as keyof typeof symptomData
                      ]?.map((entry, index) => (
                        <tr
                          key={index}
                          className="bg-white/70 rounded-xl border-b border-[#F099C1]"
                        >
                          <td className="px-4 py-2 align-top font-semibold text-gray-800 whitespace-nowrap border-r border-[#F099C1] w-32">
                            {entry.time}
                          </td>
                          <td className="px-4 py-2 text-gray-800">
                            {entry.text}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Health Metrics Cards */}
          <div className="space-y-6">
            <Card className="bg-white/80 backdrop-blur-sm border-none rounded-2xl shadow-lg">
              <CardHeader>
                <CardTitle className="text-gray-700 text-lg">
                  Heart Rate
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-24 flex items-center justify-center text-gray-500">
                  <p>No data available</p>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-white/80 backdrop-blur-sm border-none rounded-2xl shadow-lg">
              <CardHeader>
                <CardTitle className="text-gray-700 text-lg">
                  Sleep Duration
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-24 flex items-center justify-center text-gray-500">
                  <p>No data available</p>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-white/80 backdrop-blur-sm border-none rounded-2xl shadow-lg">
              <CardHeader>
                <CardTitle className="text-gray-700 text-lg">
                  Energy Expended
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-24 flex items-center justify-center text-gray-500">
                  <p>No data available</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
