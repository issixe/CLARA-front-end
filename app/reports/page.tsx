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
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  ChevronDown,
  User,
  Settings,
  LogOut,
  CalendarIcon,
  Loader2,
  Activity,
  Moon,
  TrendingUp,
  Target,
  Lightbulb,
  CheckCircle,
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
      <span className="text-lg font-semibold text-gray-700 mr-4">{label}</span>
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

interface FitnessData {
  window: { start: string; end: string };
  physical_activity: {
    steps: { daily_data: any[]; summary: any; graph: string };
    exercise_minutes: { daily_data: any[]; summary: any; graph: string };
    calories: { daily_data: any[]; summary: any; graph: string };
    distance: { daily_data: any[]; summary: any; graph: string };
  };
  sleep: {
    duration: { daily_data: any[]; summary: any; graph: string };
    heart_rate: { daily_data: any[]; summary: any };
  };
  health_summary: any;
}

interface VellumReport {
  title: string;
  activity_level?: string;
  sleep_quality?: string;
  sleep_assessment?: string;
  summary: any;
  insights: string[];
  recommendations: string[];
  data_quality: any;
}

export default function ReportPage() {
  const [fromDate, setFromDate] = useState<Date>();
  const [toDate, setToDate] = useState<Date>();
  const [fitnessData, setFitnessData] = useState<FitnessData | null>(null);
  const [vellumReports, setVellumReports] = useState<{
    physical_activity_report: VellumReport;
    sleep_report: VellumReport;
  } | null>(null);
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
      // 1. Fetch comprehensive fitness data
      const res = await fetch(
        `${BACKEND_URL}/api/comprehensive-report?start=${start}&end=${end}`,
        { credentials: "include" }
      );
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(txt || "Failed to fetch comprehensive report");
      }
      const data = await res.json();
      setFitnessData(data);

      // 2. Generate Vellum reports
      const vellumRes = await fetch(
        `${BACKEND_URL}/api/generate-vellum-reports`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify(data),
        }
      );
      if (!vellumRes.ok) {
        const txt = await vellumRes.text();
        throw new Error(txt || "Failed to generate Vellum reports");
      }
      const vellumData = await vellumRes.json();
      setVellumReports(vellumData);
    } catch (err: any) {
      setErrorMsg(err.message || "Unknown error");
      setFitnessData(null);
      setVellumReports(null);
    } finally {
      setLoading(false);
    }
  }

  const getQualityColor = (quality: string) => {
    switch (quality) {
      case "Excellent":
      case "Very Active":
        return "bg-green-100 text-green-800";
      case "Good":
      case "Moderately Active":
        return "bg-blue-100 text-blue-800";
      case "Fair":
      case "Lightly Active":
        return "bg-yellow-100 text-yellow-800";
      case "Poor":
      case "Sedentary":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

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

      {/* ── Main ────────────────────────────────────────────────── */}
      <div className="pt-24">
        <h2 className="text-2xl font-bold text-gray-600 mb-4">
          Generate Comprehensive Fitness Report:
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
            {loading ? (
              <Loader2 className="animate-spin h-5 w-5" />
            ) : (
              "Generate Report"
            )}
          </button>
        </div>

        {errorMsg && (
          <Card className="bg-red-50 border-red-200 mb-6">
            <CardContent className="p-4">
              <p className="text-red-600 font-medium">{errorMsg}</p>
            </CardContent>
          </Card>
        )}

        {/* Vellum Reports */}
        {vellumReports && (
          <div className="space-y-6 mb-8">
            {/* Physical Activity Report */}
            <Card className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <Activity className="h-6 w-6 text-[#F099C1]" />
                    <CardTitle className="text-xl text-gray-700">
                      {vellumReports.physical_activity_report.title}
                    </CardTitle>
                  </div>
                  <Badge
                    className={getQualityColor(
                      vellumReports.physical_activity_report.activity_level ||
                        ""
                    )}
                  >
                    {vellumReports.physical_activity_report.activity_level}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="flex space-x-6">
                {/* Summary Stats (Left Column) */}
                <div className="w-1/3 space-y-4">
                  <div className="bg-blue-50 rounded-lg p-4 text-center">
                    <p className="text-sm text-gray-600">Total Steps</p>
                    <p className="text-xl font-bold text-blue-600">
                      {vellumReports.physical_activity_report.summary.total_steps.toLocaleString()}
                    </p>
                  </div>
                  <div className="bg-green-50 rounded-lg p-4 text-center">
                    <p className="text-sm text-gray-600">Exercise Minutes</p>
                    <p className="text-xl font-bold text-green-600">
                      {
                        vellumReports.physical_activity_report.summary
                          .total_exercise_minutes
                      }
                    </p>
                  </div>
                  <div className="bg-orange-50 rounded-lg p-4 text-center">
                    <p className="text-sm text-gray-600">Calories Burned</p>
                    <p className="text-xl font-bold text-orange-600">
                      {vellumReports.physical_activity_report.summary.total_calories_burned.toLocaleString()}
                    </p>
                  </div>
                  <div className="bg-purple-50 rounded-lg p-4 text-center">
                    <p className="text-sm text-gray-600">Distance (km)</p>
                    <p className="text-xl font-bold text-purple-600">
                      {vellumReports.physical_activity_report.summary.total_distance_km.toFixed(
                        1
                      )}
                    </p>
                  </div>
                </div>

                {/* Insights & Recs (Right Column) */}
                <div className="w-2/3 space-y-6">
                  {/* Insights */}
                  <div>
                    <h4 className="flex items-center text-lg font-semibold text-gray-700 mb-3">
                      <Lightbulb className="h-5 w-5 mr-2 text-yellow-500" />
                      Insights
                    </h4>
                    <div className="space-y-2">
                      {vellumReports.physical_activity_report.insights.map(
                        (insight, index) => (
                          <div
                            key={index}
                            className="flex items-start space-x-2"
                          >
                            <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                            <p className="text-gray-600">{insight}</p>
                          </div>
                        )
                      )}
                    </div>
                  </div>

                  {/* Recommendations */}
                  <div>
                    <h4 className="flex items-center text-lg font-semibold text-gray-700 mb-3">
                      <Target className="h-5 w-5 mr-2 text-red-500" />
                      Recommendations
                    </h4>
                    <div className="space-y-2">
                      {vellumReports.physical_activity_report.recommendations.map(
                        (rec, index) => (
                          <div
                            key={index}
                            className="flex items-start space-x-2"
                          >
                            <TrendingUp className="h-4 w-4 text-blue-500 mt-0.5 flex-shrink-0" />
                            <p className="text-gray-600">{rec}</p>
                          </div>
                        )
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Sleep Report */}
            <Card className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <Moon className="h-6 w-6 text-[#F099C1]" />
                    <CardTitle className="text-xl text-gray-700">
                      {vellumReports.sleep_report.title}
                    </CardTitle>
                  </div>
                  <Badge
                    className={getQualityColor(
                      vellumReports.sleep_report.sleep_quality || ""
                    )}
                  >
                    {vellumReports.sleep_report.sleep_quality}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="flex space-x-6">
                {/* Left Column (Stats) */}
                <div className="w-1/3 space-y-4">
                  {/* Sleep Assessment */}
                  <div className="bg-indigo-50 rounded-lg p-4">
                    <p className="text-center text-gray-700 font-medium">
                      {vellumReports.sleep_report.sleep_assessment}
                    </p>
                  </div>

                  <div className="bg-indigo-50 rounded-lg p-4 text-center">
                    <p className="text-sm text-gray-600">Total Sleep Hours</p>
                    <p className="text-xl font-bold text-indigo-600">
                      {vellumReports.sleep_report.summary.total_sleep_hours}
                    </p>
                  </div>
                  <div className="bg-blue-50 rounded-lg p-4 text-center">
                    <p className="text-sm text-gray-600">Avg Sleep/Night</p>
                    <p className="text-xl font-bold text-blue-600">
                      {
                        vellumReports.sleep_report.summary
                          .average_sleep_hours_per_night
                      }
                      h
                    </p>
                  </div>
                  <div className="bg-red-50 rounded-lg p-4 text-center">
                    <p className="text-sm text-gray-600">Avg Heart Rate</p>
                    <p className="text-xl font-bold text-red-600">
                      {
                        vellumReports.sleep_report.summary
                          .average_resting_heart_rate
                      }{" "}
                      BPM
                    </p>
                  </div>
                  <div className="bg-purple-50 rounded-lg p-4 text-center">
                    <p className="text-sm text-gray-600">Heart Rate Range</p>
                    <p className="text-xl font-bold text-purple-600">
                      {
                        vellumReports.sleep_report.summary
                          .min_resting_heart_rate
                      }
                      -
                      {
                        vellumReports.sleep_report.summary
                          .max_resting_heart_rate
                      }
                    </p>
                  </div>
                </div>

                {/* Right Column (Insights & Recs) */}
                <div className="w-2/3 space-y-6">
                  {/* Insights */}
                  <div>
                    <h4 className="flex items-center text-lg font-semibold text-gray-700 mb-3">
                      <Lightbulb className="h-5 w-5 mr-2 text-yellow-500" />
                      Insights
                    </h4>
                    <div className="space-y-2">
                      {vellumReports.sleep_report.insights.map(
                        (insight, index) => (
                          <div
                            key={index}
                            className="flex items-start space-x-2"
                          >
                            <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                            <p className="text-gray-600">{insight}</p>
                          </div>
                        )
                      )}
                    </div>
                  </div>

                  {/* Recommendations */}
                  <div>
                    <h4 className="flex items-center text-lg font-semibold text-gray-700 mb-3">
                      <Target className="h-5 w-5 mr-2 text-red-500" />
                      Recommendations
                    </h4>
                    <div className="space-y-2">
                      {vellumReports.sleep_report.recommendations.map(
                        (rec, index) => (
                          <div
                            key={index}
                            className="flex items-start space-x-2"
                          >
                            <TrendingUp className="h-4 w-4 text-blue-500 mt-0.5 flex-shrink-0" />
                            <p className="text-gray-600">{rec}</p>
                          </div>
                        )
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Fitness Data Graphs */}
        {fitnessData && (
          <Card className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg">
            <CardHeader>
              <CardTitle className="text-xl text-gray-700">
                Fitness Data Visualizations
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {/* Steps Graph */}
                <div>
                  <h4 className="text-lg font-semibold text-gray-700 mb-3">
                    Daily Steps
                  </h4>
                  <img
                    src={`data:image/png;base64,${fitnessData.physical_activity.steps.graph}`}
                    alt="Steps graph"
                    className="w-full rounded-lg border shadow"
                  />
                </div>

                {/* Sleep Graph */}
                <div>
                  <h4 className="text-lg font-semibold text-gray-700 mb-3">
                    Sleep Duration
                  </h4>
                  <img
                    src={`data:image/png;base64,${fitnessData.sleep.duration.graph}`}
                    alt="Sleep graph"
                    className="w-full rounded-lg border shadow"
                  />
                </div>

                {/* Exercise Minutes Graph */}
                <div>
                  <h4 className="text-lg font-semibold text-gray-700 mb-3">
                    Exercise Minutes
                  </h4>
                  <img
                    src={`data:image/png;base64,${fitnessData.physical_activity.exercise_minutes.graph}`}
                    alt="Exercise minutes graph"
                    className="w-full rounded-lg border shadow"
                  />
                </div>

                {/* Calories Graph */}
                <div>
                  <h4 className="text-lg font-semibold text-gray-700 mb-3">
                    Calories Burned
                  </h4>
                  <img
                    src={`data:image/png;base64,${fitnessData.physical_activity.calories.graph}`}
                    alt="Calories graph"
                    className="w-full rounded-lg border shadow"
                  />
                </div>

                {/* Distance Graph */}
                <div>
                  <h4 className="text-lg font-semibold text-gray-700 mb-3">
                    Distance Traveled
                  </h4>
                  <img
                    src={`data:image/png;base64,${fitnessData.physical_activity.distance.graph}`}
                    alt="Distance graph"
                    className="w-full rounded-lg border shadow"
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {!fitnessData && !vellumReports && !loading && !errorMsg && (
          <Card className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg">
            <CardContent className="p-6">
              <p className="text-center text-gray-500 h-64 flex items-center justify-center">
                Comprehensive fitness report will appear here
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
