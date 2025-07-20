"use client";

import type { FC } from "react";
import { useState, useEffect } from "react";
import Link from "next/link";
import { format } from "date-fns";
import { Calendar } from "@/components/ui/calendar";
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "@/components/ui/popover";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ChevronDown,
  User,
  Settings,
  LogOut,
  CalendarIcon,
  Moon,
  Footprints,
  Heart,
} from "lucide-react";

const symptomData = {
  "2025-07-19": [
    {
      time: "8:15 AM",
      text: "Woke up with slight dizziness. Took blood pressure medication as scheduled. BP reading: 135/85.",
    },
    {
      time: "10:30 AM",
      text: "Feeling better after breakfast. Completed morning exercises. Joint mobility good today.",
    },
    {
      time: "2:45 PM",
      text: "Mild headache developed. Took acetaminophen. Remembered to drink more water.",
    },
    {
      time: "6:20 PM",
      text: "Headache resolved. Evening walk completed - 15 minutes around the block. Feeling tired but content.",
    },
  ],
  "2025-07-18": [
    {
      time: "7:45 AM",
      text: "Good night's sleep. Morning blood sugar: 6.2 mmol/L. Took diabetes medication.",
    },
    {
      time: "11:00 AM",
      text: "Slight chest discomfort while gardening. Sat down and rested. Discomfort subsided after 10 minutes.",
    },
    {
      time: "3:30 PM",
      text: "Followed up with Dr. Johnson about chest discomfort. She advised to monitor and call if it worsens.",
    },
    {
      time: "7:00 PM",
      text: "Evening medication taken. No further chest discomfort. Watched TV and relaxed.",
    },
  ],
  "2025-07-17": [
    {
      time: "8:30 AM",
      text: "Woke up feeling congested. Sinus pressure noticeable. Took allergy medication.",
    },
    {
      time: "12:15 PM",
      text: "Congestion improved. Lunch with neighbor Mary. Good social interaction.",
    },
    {
      time: "4:45 PM",
      text: "Mild back pain from sitting too long. Did some gentle stretches. Pain reduced.",
    },
    {
      time: "8:30 PM",
      text: "Evening routine completed. Blood pressure: 128/82. Ready for bed.",
    },
  ],
  "2025-07-16": [
    {
      time: "7:20 AM",
      text: "Restless night. Woke up with anxiety about upcoming doctor's appointment.",
    },
    {
      time: "10:00 AM",
      text: "Called daughter Sarah to discuss appointment concerns. Feeling more reassured.",
    },
    {
      time: "2:00 PM",
      text: "Doctor's appointment went well. Blood work results good. Medication adjusted slightly.",
    },
    {
      time: "6:15 PM",
      text: "Celebrated good news with a small treat. Evening walk - 20 minutes. Feeling positive.",
    },
  ],
  "2025-07-15": [
    {
      time: "8:00 AM",
      text: "Good morning energy. Blood sugar: 5.8 mmol/L. Breakfast and medication taken.",
    },
    {
      time: "11:30 AM",
      text: "Mild shortness of breath while climbing stairs. Rested and recovered quickly.",
    },
    {
      time: "3:00 PM",
      text: "Afternoon nap - 30 minutes. Woke up refreshed. No breathing issues since morning.",
    },
    {
      time: "7:30 PM",
      text: "Evening routine. Blood pressure: 132/88. Watched favorite show before bed.",
    },
  ],
  "2025-07-14": [
    {
      time: "7:45 AM",
      text: "Woke up with slight nausea. Took anti-nausea medication. Feeling better after 30 minutes.",
    },
    {
      time: "12:00 PM",
      text: "Appetite returned. Light lunch. Called pharmacy to refill prescription.",
    },
    {
      time: "4:30 PM",
      text: "Pharmacy delivered medication. Organized pill box for the week.",
    },
    {
      time: "8:00 PM",
      text: "Evening medication taken. Blood sugar: 6.5 mmol/L. Ready for sleep.",
    },
  ],
  "2025-07-13": [
    {
      time: "8:15 AM",
      text: "Good night's sleep. Morning routine completed. Blood pressure: 125/80.",
    },
    {
      time: "11:00 AM",
      text: "Mild joint stiffness in knees. Applied heating pad. Stiffness improved.",
    },
    {
      time: "2:30 PM",
      text: "Afternoon walk with neighbor. 25 minutes. Joints feeling more mobile.",
    },
    {
      time: "6:45 PM",
      text: "Evening medication. Blood sugar: 5.9 mmol/L. Relaxing evening planned.",
    },
  ],
  "2025-07-12": [
    {
      time: "7:30 AM",
      text: "Woke up with headache. Took pain medication. Feeling better after breakfast.",
    },
    {
      time: "10:30 AM",
      text: "Headache resolved. Morning exercises completed. Energy levels good.",
    },
    {
      time: "3:15 PM",
      text: "Mild fatigue in afternoon. Took short nap. Woke up refreshed.",
    },
    {
      time: "7:00 PM",
      text: "Evening routine. Blood pressure: 130/85. Watched news and relaxed.",
    },
  ],
  "2025-07-11": [
    {
      time: "8:00 AM",
      text: "Good morning. Blood sugar: 6.1 mmol/L. All medications taken on schedule.",
    },
    {
      time: "12:30 PM",
      text: "Lunch with friends at community center. Good social interaction. Feeling happy.",
    },
    {
      time: "4:00 PM",
      text: "Mild back pain from sitting. Did gentle stretches. Pain improved.",
    },
    {
      time: "8:15 PM",
      text: "Evening medication. Blood pressure: 127/83. Reading before bed.",
    },
  ],
  "2025-07-10": [
    {
      time: "7:45 AM",
      text: "Restless night. Woke up feeling anxious. Took anxiety medication as prescribed.",
    },
    {
      time: "10:00 AM",
      text: "Feeling calmer. Called therapist for support. Scheduled follow-up appointment.",
    },
    {
      time: "2:30 PM",
      text: "Afternoon walk in park. 30 minutes. Fresh air helped mood significantly.",
    },
    {
      time: "6:30 PM",
      text: "Evening routine. Blood sugar: 6.3 mmol/L. Feeling more positive.",
    },
  ],
  "2025-07-09": [
    {
      time: "8:15 AM",
      text: "Good night's sleep. Morning blood pressure: 128/82. All medications taken.",
    },
    {
      time: "11:30 AM",
      text: "Mild chest tightness while doing housework. Rested and symptoms resolved.",
    },
    {
      time: "3:45 PM",
      text: "Called cardiologist about chest tightness. Advised to monitor and report if it recurs.",
    },
    {
      time: "7:00 PM",
      text: "Evening walk - 15 minutes. No further chest symptoms. Blood pressure: 126/80.",
    },
  ],
  "2025-07-08": [
    {
      time: "7:30 AM",
      text: "Woke up with slight dizziness. Took blood pressure medication. Feeling better after 30 minutes.",
    },
    {
      time: "10:15 AM",
      text: "Morning exercises completed. Joint mobility good. Energy levels normal.",
    },
    {
      time: "2:00 PM",
      text: "Afternoon appointment with nutritionist. Discussed diabetes management. Good advice received.",
    },
    {
      time: "6:45 PM",
      text: "Evening medication. Blood sugar: 5.7 mmol/L. Relaxing evening.",
    },
  ],
  "2025-07-07": [
    {
      time: "8:00 AM",
      text: "Good morning. Blood pressure: 125/78. All medications taken on schedule.",
    },
    {
      time: "12:00 PM",
      text: "Lunch with family. Good social interaction. Appetite normal.",
    },
    {
      time: "4:30 PM",
      text: "Mild headache developed. Took acetaminophen. Headache resolved within hour.",
    },
    {
      time: "7:30 PM",
      text: "Evening routine. Blood sugar: 6.0 mmol/L. Watched favorite show.",
    },
  ],
  "2025-07-06": [
    {
      time: "7:45 AM",
      text: "Woke up feeling congested. Sinus pressure. Took allergy medication.",
    },
    {
      time: "11:00 AM",
      text: "Congestion improved. Morning walk completed. 20 minutes. Feeling better.",
    },
    {
      time: "3:15 PM",
      text: "Afternoon nap. Woke up refreshed. No congestion remaining.",
    },
    {
      time: "8:00 PM",
      text: "Evening medication. Blood pressure: 129/84. Ready for bed.",
    },
  ],
  "2025-07-05": [
    {
      time: "8:15 AM",
      text: "Good night's sleep. Blood sugar: 5.9 mmol/L. Morning routine completed.",
    },
    {
      time: "12:30 PM",
      text: "Mild shortness of breath while walking. Rested and recovered. Called doctor.",
    },
    {
      time: "4:00 PM",
      text: "Doctor advised to monitor breathing. No further episodes. Feeling reassured.",
    },
    {
      time: "7:15 PM",
      text: "Evening walk - 10 minutes. No breathing issues. Blood pressure: 127/81.",
    },
  ],
  "2025-07-04": [
    {
      time: "7:30 AM",
      text: "Woke up with slight nausea. Took anti-nausea medication. Feeling better after breakfast.",
    },
    {
      time: "10:30 AM",
      text: "Morning exercises. Joint stiffness minimal. Energy levels good.",
    },
    {
      time: "2:45 PM",
      text: "Afternoon social call with neighbor. Good conversation. Mood improved.",
    },
    {
      time: "6:30 PM",
      text: "Evening medication. Blood sugar: 6.2 mmol/L. Relaxing evening.",
    },
  ],
  "2025-07-03": [
    {
      time: "8:00 AM",
      text: "Good morning. Blood pressure: 124/79. All medications taken on schedule.",
    },
    {
      time: "11:15 AM",
      text: "Mild back pain from gardening. Applied heating pad. Pain improved.",
    },
    {
      time: "3:30 PM",
      text: "Afternoon walk. 25 minutes. Back feeling better. Good exercise.",
    },
    {
      time: "7:45 PM",
      text: "Evening routine. Blood sugar: 5.8 mmol/L. Reading before bed.",
    },
  ],
  "2025-07-02": [
    {
      time: "7:45 AM",
      text: "Restless night. Woke up with anxiety. Took anxiety medication as needed.",
    },
    {
      time: "10:00 AM",
      text: "Feeling calmer. Called daughter for support. Good conversation.",
    },
    {
      time: "2:15 PM",
      text: "Afternoon appointment with therapist. Helpful session. Mood improved.",
    },
    {
      time: "6:45 PM",
      text: "Evening medication. Blood pressure: 131/86. Feeling more positive.",
    },
  ],
  "2025-07-01": [
    {
      time: "8:15 AM",
      text: "Good morning. Blood sugar: 6.0 mmol/L. Morning routine completed.",
    },
    {
      time: "12:00 PM",
      text: "Lunch with friends. Good social interaction. Appetite normal.",
    },
    {
      time: "4:30 PM",
      text: "Mild headache developed. Took pain medication. Headache resolved.",
    },
    {
      time: "7:30 PM",
      text: "Evening walk - 15 minutes. Blood pressure: 126/82. Relaxing evening.",
    },
  ],
  "2025-06-30": [
    {
      time: "7:30 AM",
      text: "Woke up with slight dizziness. Took blood pressure medication. Feeling better.",
    },
    {
      time: "10:30 AM",
      text: "Morning exercises. Joint mobility good. Energy levels normal.",
    },
    {
      time: "3:00 PM",
      text: "Afternoon nap. Woke up refreshed. No dizziness remaining.",
    },
    {
      time: "8:00 PM",
      text: "Evening medication. Blood sugar: 5.9 mmol/L. Ready for bed.",
    },
  ],
  "2025-06-29": [
    {
      time: "8:00 AM",
      text: "Good night's sleep. Blood pressure: 125/80. All medications taken.",
    },
    {
      time: "11:30 AM",
      text: "Mild chest discomfort while walking. Rested and symptoms resolved.",
    },
    {
      time: "4:15 PM",
      text: "Called cardiologist. Advised to monitor. No further episodes.",
    },
    {
      time: "7:00 PM",
      text: "Evening routine. Blood pressure: 128/83. Feeling reassured.",
    },
  ],
  "2025-06-28": [
    {
      time: "7:45 AM",
      text: "Woke up feeling congested. Sinus pressure. Took allergy medication.",
    },
    {
      time: "10:15 AM",
      text: "Congestion improved. Morning walk - 20 minutes. Feeling better.",
    },
    {
      time: "2:30 PM",
      text: "Afternoon social call. Good conversation. Mood improved.",
    },
    {
      time: "6:45 PM",
      text: "Evening medication. Blood sugar: 6.1 mmol/L. No congestion remaining.",
    },
  ],
  "2025-06-27": [
    {
      time: "8:15 AM",
      text: "Good morning. Blood sugar: 5.8 mmol/L. Morning routine completed.",
    },
    {
      time: "12:00 PM",
      text: "Lunch with family. Good social interaction. Appetite normal.",
    },
    {
      time: "4:30 PM",
      text: "Mild back pain from sitting. Did stretches. Pain improved.",
    },
    {
      time: "7:30 PM",
      text: "Evening walk - 15 minutes. Blood pressure: 127/81. Relaxing evening.",
    },
  ],
  "2025-06-26": [
    {
      time: "7:30 AM",
      text: "Restless night. Woke up with anxiety. Took anxiety medication.",
    },
    {
      time: "10:00 AM",
      text: "Feeling calmer. Called therapist for support. Scheduled appointment.",
    },
    {
      time: "3:15 PM",
      text: "Afternoon walk in park. 30 minutes. Fresh air helped mood.",
    },
    {
      time: "6:30 PM",
      text: "Evening medication. Blood pressure: 130/85. Feeling more positive.",
    },
  ],
  "2025-06-25": [
    {
      time: "8:00 AM",
      text: "Good night's sleep. Blood pressure: 124/78. All medications taken.",
    },
    {
      time: "11:30 AM",
      text: "Mild shortness of breath while climbing stairs. Rested and recovered.",
    },
    {
      time: "4:00 PM",
      text: "Afternoon nap. Woke up refreshed. No breathing issues since morning.",
    },
    {
      time: "7:45 PM",
      text: "Evening routine. Blood sugar: 6.0 mmol/L. Watched favorite show.",
    },
  ],
  "2025-06-24": [
    {
      time: "7:45 AM",
      text: "Woke up with slight nausea. Took anti-nausea medication. Feeling better.",
    },
    {
      time: "10:30 AM",
      text: "Appetite returned. Light lunch. Called pharmacy for refill.",
    },
    {
      time: "3:30 PM",
      text: "Pharmacy delivered medication. Organized pill box for week.",
    },
    {
      time: "8:00 PM",
      text: "Evening medication. Blood sugar: 6.4 mmol/L. Ready for sleep.",
    },
  ],
  "2025-06-23": [
    {
      time: "8:15 AM",
      text: "Good morning. Blood sugar: 5.9 mmol/L. Morning routine completed.",
    },
    {
      time: "12:30 PM",
      text: "Lunch with friends. Good social interaction. Feeling happy.",
    },
    {
      time: "4:15 PM",
      text: "Mild joint stiffness in knees. Applied heating pad. Improved.",
    },
    {
      time: "7:00 PM",
      text: "Evening walk - 20 minutes. Blood pressure: 126/80. Relaxing evening.",
    },
  ],
  "2025-06-22": [
    {
      time: "7:30 AM",
      text: "Woke up with headache. Took pain medication. Feeling better after breakfast.",
    },
    {
      time: "10:15 AM",
      text: "Headache resolved. Morning exercises completed. Energy levels good.",
    },
    {
      time: "3:00 PM",
      text: "Mild fatigue in afternoon. Short nap. Woke up refreshed.",
    },
    {
      time: "6:45 PM",
      text: "Evening routine. Blood pressure: 129/84. Watched news and relaxed.",
    },
  ],
  "2025-06-21": [
    {
      time: "8:00 AM",
      text: "Good morning. Blood pressure: 125/79. All medications taken on schedule.",
    },
    {
      time: "11:30 AM",
      text: "Morning walk completed. 25 minutes. Joints feeling mobile.",
    },
    {
      time: "2:45 PM",
      text: "Afternoon social call with neighbor. Good conversation. Mood improved.",
    },
    {
      time: "7:15 PM",
      text: "Evening medication. Blood sugar: 5.7 mmol/L. Reading before bed.",
    },
  ],
  "2025-06-20": [
    {
      time: "7:45 AM",
      text: "Woke up feeling refreshed. Blood sugar: 6.0 mmol/L. Morning routine completed.",
    },
    {
      time: "12:00 PM",
      text: "Lunch with family. Good social interaction. Appetite normal.",
    },
    {
      time: "4:30 PM",
      text: "Mild back pain from sitting. Did gentle stretches. Pain reduced.",
    },
    {
      time: "8:00 PM",
      text: "Evening walk - 15 minutes. Blood pressure: 127/82. Ready for bed.",
    },
  ],
};

// Interface for ring data from API
interface RingData {
  date: string;
  sleep: {
    current: number;
    goal: number;
    percentage: number;
  };
  steps: {
    current: number;
    goal: number;
    percentage: number;
  };
  energy?: {
    current: number;
    goal: number;
    percentage: number;
  };
}

// Interface for heart rate data from API
interface HeartRateData {
  date: string;
  data_points: Array<{
    time: string;
    timestamp: number;
    value: number;
  }>;
  summary: {
    average: number;
    min: number;
    max: number;
    count: number;
  };
  graph: string; // base64 encoded PNG
}

// Ring component for Apple Watch-style progress
interface RingProps {
  current: number;
  goal: number;
  color: string;
  size?: number;
  strokeWidth?: number;
}

const Ring: FC<RingProps> = ({
  current,
  goal,
  color,
  size = 80,
  strokeWidth = 8,
}) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.min(current / goal, 1);
  const strokeDasharray = circumference;
  const strokeDashoffset = circumference - progress * circumference;

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="#e5e7eb"
          strokeWidth={strokeWidth}
          fill="none"
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={strokeDasharray}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-sm font-semibold text-gray-800">
          {Math.round((current / goal) * 100)}%
        </span>
      </div>
    </div>
  );
};

// DateField component for calendar picker
interface DateFieldProps {
  date?: Date;
  onChange: (d: Date | undefined) => void;
}

const DateField: FC<DateFieldProps> = ({ date, onChange }) => {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button className="w-64 h-12 bg-[#F099C1] hover:bg-[#EA83B3] border-none rounded-2xl text-lg font-semibold text-white px-6 transition-colors flex items-center justify-between">
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
  );
};

export default function HomePage() {
  const [selectedDate, setSelectedDate] = useState<Date>(
    new Date("2025-07-20")
  );
  const [ringData, setRingData] = useState<RingData | null>(null);
  const [heartRateData, setHeartRateData] = useState<HeartRateData | null>(
    null
  );
  const [loading, setLoading] = useState(false);
  const [heartRateLoading, setHeartRateLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [heartRateError, setHeartRateError] = useState<string | null>(null);

  // Fetch ring data from API when date changes
  useEffect(() => {
    const fetchRingData = async () => {
      setLoading(true);
      setError(null);

      try {
        const dateStr = format(selectedDate, "yyyy-MM-dd");
        const response = await fetch(
          `http://127.0.0.1:5000/api/rings?date=${dateStr}`,
          {
            credentials: "include",
          }
        );

        if (!response.ok) {
          if (response.status === 401) {
            setError("Please authenticate with Google Fit first");
          } else {
            setError(`Failed to fetch data: ${response.status}`);
          }
          return;
        }

        const data = await response.json();
        console.log("Ring data received:", data); // Debug log
        setRingData(data);
      } catch (err) {
        setError("Failed to connect to server");
        console.error("Error fetching ring data:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchRingData();
  }, [selectedDate]);

  // Fetch heart rate data from API when date changes
  useEffect(() => {
    const fetchHeartRateData = async () => {
      setHeartRateLoading(true);
      setHeartRateError(null);

      try {
        const dateStr = format(selectedDate, "yyyy-MM-dd");
        const response = await fetch(
          `http://127.0.0.1:5000/api/heart-rate?date=${dateStr}`,
          {
            credentials: "include",
          }
        );

        if (!response.ok) {
          if (response.status === 401) {
            setHeartRateError("Please authenticate with Google Fit first");
          } else {
            setHeartRateError(
              `Failed to fetch heart rate data: ${response.status}`
            );
          }
          return;
        }

        const data = await response.json();
        console.log("Heart rate data received:", data); // Debug log
        setHeartRateData(data);
      } catch (err) {
        setHeartRateError("Failed to connect to server");
        console.error("Error fetching heart rate data:", err);
      } finally {
        setHeartRateLoading(false);
      }
    };

    fetchHeartRateData();
  }, [selectedDate]);

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
                  className="flex items-center transition-colors"
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = "#fef2f2";
                    e.currentTarget.style.color = "#dc2626";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = "";
                    e.currentTarget.style.color = "";
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
          Generate Logs:
        </h2>

        {/* Date Selector */}
        <div className="flex justify-start mb-8">
          <div className="flex items-center">
            <span className="text-lg font-semibold text-gray-700 mr-4">
              Choose date:
            </span>
            <DateField
              date={selectedDate}
              onChange={(d) => d && setSelectedDate(d)}
            />
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Side - Symptom Logs and Heart Rate */}
          <div className="lg:col-span-2 space-y-6">
            {/* Symptom Logs */}
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
                        format(
                          selectedDate,
                          "yyyy-MM-dd"
                        ) as keyof typeof symptomData
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

            {/* Heart Rate */}
            <Card className="bg-white/80 backdrop-blur-sm border-none rounded-2xl shadow-lg">
              <CardHeader>
                <CardTitle className="text-gray-700 text-lg flex items-center">
                  <Heart className="mr-2 h-5 w-5 text-red-500" />
                  Heart Rate
                </CardTitle>
              </CardHeader>
              <CardContent>
                {heartRateLoading ? (
                  <div className="flex flex-col items-center space-y-3">
                    <div className="w-20 h-20 border-4 border-gray-200 border-t-red-500 rounded-full animate-spin"></div>
                    <p className="text-sm text-gray-600">Loading...</p>
                  </div>
                ) : heartRateError ? (
                  <div className="flex flex-col items-center space-y-3">
                    <div className="w-20 h-20 border-4 border-gray-200 rounded-full flex items-center justify-center">
                      <span className="text-gray-400 text-2xl">?</span>
                    </div>
                    <p className="text-sm text-red-600 text-center">
                      {heartRateError}
                    </p>
                  </div>
                ) : heartRateData ? (
                  <div className="flex gap-4">
                    {/* Left Side - Stats */}
                    <div className="w-48 flex flex-col justify-center space-y-3">
                      {/* Summary Stats */}
                      <div className="space-y-2">
                        <div className="bg-red-50 rounded-lg p-3 text-center">
                          <p className="text-xs text-gray-600">Average</p>
                          <p className="text-xl font-bold text-red-600">
                            {heartRateData.summary.average} BPM
                          </p>
                        </div>
                        <div className="bg-red-50 rounded-lg p-3 text-center">
                          <p className="text-xs text-gray-600">Min</p>
                          <p className="text-xl font-bold text-red-600">
                            {heartRateData.summary.min.toFixed(1)} BPM
                          </p>
                        </div>
                        <div className="bg-red-50 rounded-lg p-3 text-center">
                          <p className="text-xs text-gray-600">Max</p>
                          <p className="text-xl font-bold text-red-600">
                            {heartRateData.summary.max.toFixed(1)} BPM
                          </p>
                        </div>
                      </div>

                      {/* Data Points Count */}
                      <div className="text-center">
                        <p className="text-xs text-gray-600">
                          {heartRateData.summary.count} measurements today
                        </p>
                      </div>
                    </div>

                    {/* Right Side - Graph */}
                    {heartRateData.graph && (
                      <div className="flex-1">
                        <img
                          src={`data:image/png;base64,${heartRateData.graph}`}
                          alt="Heart Rate Fluctuations"
                          className="w-full h-auto rounded-lg border border-gray-200"
                        />
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex flex-col items-center space-y-3">
                    <div className="w-20 h-20 border-4 border-gray-200 rounded-full flex items-center justify-center">
                      <span className="text-gray-400 text-2xl">?</span>
                    </div>
                    <p className="text-sm text-gray-600">No data available</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Right Side - Health Metrics Cards */}
          <div className="space-y-6">
            <Card className="bg-white/80 backdrop-blur-sm border-none rounded-2xl shadow-lg">
              <CardHeader>
                <CardTitle className="text-gray-700 text-lg flex items-center">
                  <Moon className="mr-2 h-5 w-5 text-blue-500" />
                  Sleep Duration
                </CardTitle>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="flex flex-col items-center space-y-3">
                    <div className="w-20 h-20 border-4 border-gray-200 border-t-blue-500 rounded-full animate-spin"></div>
                    <p className="text-sm text-gray-600">Loading...</p>
                  </div>
                ) : error ? (
                  <div className="flex flex-col items-center space-y-3">
                    <div className="w-20 h-20 border-4 border-gray-200 rounded-full flex items-center justify-center">
                      <span className="text-gray-400 text-2xl">?</span>
                    </div>
                    <p className="text-sm text-red-600 text-center">{error}</p>
                  </div>
                ) : ringData ? (
                  <div className="flex flex-col items-center space-y-3">
                    <Ring
                      current={ringData.sleep.current}
                      goal={ringData.sleep.goal}
                      color="#3b82f6"
                      size={100}
                      strokeWidth={10}
                    />
                    <div className="text-center">
                      <p className="text-lg font-semibold text-gray-800">
                        {ringData.sleep.current}h
                      </p>
                      <p className="text-sm text-gray-600">
                        Goal: {ringData.sleep.goal}h
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center space-y-3">
                    <div className="w-20 h-20 border-4 border-gray-200 rounded-full flex items-center justify-center">
                      <span className="text-gray-400 text-2xl">?</span>
                    </div>
                    <p className="text-sm text-gray-600">No data available</p>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="bg-white/80 backdrop-blur-sm border-none rounded-2xl shadow-lg">
              <CardHeader>
                <CardTitle className="text-gray-700 text-lg flex items-center">
                  <Footprints className="mr-2 h-5 w-5 text-green-500" />
                  Daily Steps
                </CardTitle>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="flex flex-col items-center space-y-3">
                    <div className="w-20 h-20 border-4 border-gray-200 border-t-green-500 rounded-full animate-spin"></div>
                    <p className="text-sm text-gray-600">Loading...</p>
                  </div>
                ) : error ? (
                  <div className="flex flex-col items-center space-y-3">
                    <div className="w-20 h-20 border-4 border-gray-200 rounded-full flex items-center justify-center">
                      <span className="text-gray-400 text-2xl">?</span>
                    </div>
                    <p className="text-sm text-red-600 text-center">{error}</p>
                  </div>
                ) : ringData ? (
                  <div className="flex flex-col items-center space-y-3">
                    <Ring
                      current={
                        ringData.steps?.current || ringData.energy?.current || 0
                      }
                      goal={
                        ringData.steps?.goal || ringData.energy?.goal || 10000
                      }
                      color="#22c55e"
                      size={100}
                      strokeWidth={10}
                    />
                    <div className="text-center">
                      <p className="text-lg font-semibold text-gray-800">
                        {(
                          ringData.steps?.current ||
                          ringData.energy?.current ||
                          0
                        ).toLocaleString()}{" "}
                        steps
                      </p>
                      <p className="text-sm text-gray-600">
                        Goal:{" "}
                        {(
                          ringData.steps?.goal ||
                          ringData.energy?.goal ||
                          10000
                        ).toLocaleString()}{" "}
                        steps
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center space-y-3">
                    <div className="w-20 h-20 border-4 border-gray-200 rounded-full flex items-center justify-center">
                      <span className="text-gray-400 text-2xl">?</span>
                    </div>
                    <p className="text-sm text-gray-600">No data available</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
